from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from fastapi.templating import Jinja2Templates
import pathlib
from sqlalchemy import text
from WebApp.app.db.session import engine

from WebApp.app.auth.routes import router as auth_router
# Lazy import helper for EnhancedFlightSearchClient to avoid modifying existing EFS modules
import sys, os, logging
_EFS_SINGLETON = None  # module-level cache
def _get_efs_client():
    global _EFS_SINGLETON
    if _EFS_SINGLETON is not None:
        return _EFS_SINGLETON
    try:
        from Main.enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore
    except ModuleNotFoundError:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        main_dir = os.path.join(project_root, 'Main')
        modified = False
        if project_root not in sys.path:
            sys.path.append(project_root); modified = True
        if main_dir not in sys.path and os.path.isdir(main_dir):
            sys.path.append(main_dir); modified = True
        if modified:
            logging.getLogger(__name__).warning("Adjusted sys.path for EFS import: %s", [p for p in (project_root, main_dir)])
        from Main.enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore
    _EFS_SINGLETON = EnhancedFlightSearchClient()
    logging.getLogger(__name__).info("Initialized EFS singleton using db_path=%s", getattr(_EFS_SINGLETON, 'db_path', None))
    return _EFS_SINGLETON

app = FastAPI(title="SerpAPI Flight WebApp", version="0.1.0")

# --- Optional React (Vite) production build integration (single-port mode) ---
# If a built React frontend exists under react-frontend/dist, serve it directly
# from this FastAPI app so only the backend port (default 8013) is required.
from functools import lru_cache
_react_dist_root = pathlib.Path(__file__).resolve().parent.parent / "react-frontend" / "dist"
_react_index_path = _react_dist_root / "index.html"
_react_assets_dir = _react_dist_root / "assets"
REACT_DIST_ENABLED = _react_index_path.is_file() and _react_assets_dir.is_dir()
if REACT_DIST_ENABLED:
    # Mount hashed static asset bundle (JS/CSS etc.). index.html will be returned via root route below.
    app.mount("/assets", StaticFiles(directory=str(_react_assets_dir)), name="assets")

    @lru_cache(maxsize=1)
    def _load_react_index() -> str:
        try:
            return _react_index_path.read_text(encoding="utf-8")
        except Exception as e:
            logging.getLogger(__name__).error("Failed loading React index.html: %s", e)
            return "<!DOCTYPE html><html><body><h1>Frontend load error</h1></body></html>"

    logging.getLogger(__name__).info("React dist detected; serving SPA index & assets (single-port mode enabled)")
else:
    logging.getLogger(__name__).info("React dist folder not found; falling back to Jinja template UI for root route")

templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

app.include_router(auth_router)

@app.get("/", response_class=HTMLResponse, tags=["ui"])
async def root(request: Request):
    # Prefer built React SPA if available; otherwise fall back to legacy minimal login template.
    if REACT_DIST_ENABLED:
        return HTMLResponse(_load_react_index())
    return templates.TemplateResponse("login.html", {"request": request})



@app.get("/dashboard", response_class=HTMLResponse, tags=["ui"])
async def dashboard(request: Request):
    # Client-side JS will fetch /auth/me with stored bearer token.
    return HTMLResponse("""<!DOCTYPE html><html><head><title>Dashboard</title>
    <meta charset='utf-8'/><style>body{font-family:system-ui;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#f0f6ff;margin:0;} .wrap{text-align:center;max-width:620px;} h1{color:#134e9b;margin-bottom:.5rem;} p{color:#475569;font-size:.85rem;} button, a.action{margin-top:1rem;padding:.5rem .9rem;border:1px solid #134e9b;background:#fff;color:#134e9b;border-radius:6px;cursor:pointer;text-decoration:none;display:inline-block;} button:hover, a.action:hover{background:#134e9b;color:#fff;}</style></head>
    <body><div class='wrap'><h1 id='welcome'>Loading...</h1><p id='info'>Checking session.</p><div style='margin-top:1rem'><a class='action' href='/flight-search'>Flight Search</a></div><div id='adminBox' style='margin-top:.75rem'></div><button id='logout'>Logout</button></div>
    <script>
    async function init(){
        const t = localStorage.getItem('access_token');
        if(!t){ window.location='/'; return; }
        try {
            const res = await fetch('/auth/me',{headers:{'Authorization':'Bearer '+t}});
            if(!res.ok){ throw new Error('unauth'); }
            const user = await res.json();
                document.getElementById('welcome').textContent = 'Welcome, '+user.email;
                document.getElementById('info').textContent = 'User ID '+user.id + (user.is_admin ? ' (admin)' : '');
                if(user.is_admin){
                    const box = document.getElementById('adminBox');
                    box.innerHTML = "<button id='gotoAdmin'>Open Admin Portal</button>";
                    document.getElementById('gotoAdmin').onclick=()=>{ window.location='/admin'; };
                }
        } catch(e){ localStorage.removeItem('access_token'); window.location='/'; }
    }
    document.getElementById('logout').addEventListener('click', async ()=>{ 
        const t = localStorage.getItem('access_token');
        try { if(t){ await fetch('/auth/logout',{method:'POST', headers:{'Authorization':'Bearer '+t}}); } } catch(e){}
        localStorage.clear(); window.location='/'; 
    });
    init();
    </script>
    </body></html>""")

"""Legacy inline flight search UI routes removed. React (built) or minimal templates provide UI."""

@app.get("/api/flight_search", response_class=JSONResponse, tags=["flight"]) 
async def api_flight_search(origin: str = Query(..., min_length=3, max_length=5, description="Origin IATA"),
                            destination: str = Query(..., min_length=3, max_length=5, description="Destination IATA"),
                            date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$", description="Outbound date YYYY-MM-DD"),
                            return_date: str | None = Query(None, regex=r"^\d{4}-\d{2}-\d{2}$", description="Return date YYYY-MM-DD (optional)"),
                            travel_class: int = Query(1, ge=1, le=4, description="Travel class (1=Economy,2=Premium,3=Business,4=First)"),
                            one_way: bool = Query(False, description="Set true for 1-way; suppress auto-generated return date")):
    # Minimal wrapper: only uses origin/destination/date; relies on existing EFS caching logic.
    client = _get_efs_client()
    def run_search():
        kwargs = dict(departure_id=origin.upper(), arrival_id=destination.upper(), outbound_date=date, travel_class=int(travel_class))
        if one_way:
            kwargs['one_way'] = True
        elif return_date:
            kwargs['return_date'] = return_date
        return client.search_flights(**kwargs)
    result = await run_in_threadpool(run_search)
    return JSONResponse(result)


@app.get("/api/airports/suggest", response_class=JSONResponse, tags=["airports"])
async def airports_suggest(q: str = Query(..., min_length=1, max_length=64), limit: int = Query(10, ge=1, le=50)):
    q = q.strip()
    if not q:
        return JSONResponse([])
    like = f"%{q}%"
    # Return only code, city, country (omit airport_name & country_code from payload as requested)
    # Still search across name to preserve discoverability.
    sql = text(
        """
        SELECT airport_code AS code, city, country
        FROM airports
        WHERE airport_code LIKE :like COLLATE NOCASE
           OR airport_name LIKE :like COLLATE NOCASE
           OR city LIKE :like COLLATE NOCASE
           OR country LIKE :like COLLATE NOCASE
        ORDER BY airport_code ASC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"like": like, "limit": limit}).mappings().fetchall()
        out = [dict(r) for r in rows]
    return JSONResponse(out)


@app.get("/api/airports/by_code", response_class=JSONResponse, tags=["airports"])
async def airport_by_code(code: str = Query(..., min_length=3, max_length=5)):
    code = code.strip().upper()
    if not code:
        raise HTTPException(status_code=400, detail="code required")
    sql = text(
        """
        SELECT airport_code AS code, airport_name AS name, country, country_code, city
        FROM airports
        WHERE airport_code = :code
        LIMIT 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, {"code": code}).mappings().fetchone()
        if not row:
            return JSONResponse({}, status_code=200)
        return JSONResponse(dict(row))

@app.get("/api/airports/by_codes", response_class=JSONResponse, tags=["airports"])
async def airports_by_codes(codes: str = Query(..., description="Comma-separated IATA codes")):
    # Normalize codes to upper and unique
    codes_list = [c.strip().upper() for c in codes.split(',') if c.strip()]
    if not codes_list:
        return JSONResponse([])
    # SQLite doesn't support array params natively; build placeholders safely
    # Cap to a reasonable number to avoid too-large queries
    codes_list = codes_list[:200]
    placeholders = ','.join([f":c{i}" for i in range(len(codes_list))])
    params = {f"c{i}": code for i, code in enumerate(codes_list)}
    sql = text(
        f"""
        SELECT airport_code AS code, airport_name AS name, country, country_code, city
        FROM airports
        WHERE airport_code IN ({placeholders})
        ORDER BY airport_code ASC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().fetchall()
        out = [dict(r) for r in rows]
    return JSONResponse(out)


@app.get("/api/airports/all", response_class=JSONResponse, tags=["airports"])
async def airports_all():
    """Return a minimal list of all airports for client-side caching/filtering.

    Columns: code, name, country, country_code, city
    """
    sql = text(
        """
        SELECT airport_code AS code, airport_name AS name, country, country_code, city
        FROM airports
        ORDER BY airport_code ASC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().fetchall()
        out = [dict(r) for r in rows]
    # Note: This endpoint is intentionally unauthenticated and can be cached client-side per session.
    return JSONResponse(out)


@app.get("/api/airlines/by_codes", response_class=JSONResponse, tags=["airlines"])
async def airlines_by_codes(codes: str = Query(..., description="Comma-separated airline IATA/ICAO codes (2-3 chars)")):
    # Normalize codes to upper and unique
    codes_list = [c.strip().upper() for c in codes.split(',') if c.strip()]
    if not codes_list:
        return JSONResponse([])
    codes_list = codes_list[:200]
    placeholders = ','.join([f":c{i}" for i in range(len(codes_list))])
    params = {f"c{i}": code for i, code in enumerate(codes_list)}
    sql = text(
        f"""
        SELECT airline_code AS code, airline_name AS name
        FROM airlines
        WHERE airline_code IN ({placeholders})
        ORDER BY airline_code ASC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().fetchall()
        out = [dict(r) for r in rows]
    return JSONResponse(out)


@app.get("/admin", response_class=HTMLResponse, tags=["ui"])
async def admin_portal(request: Request):
    return HTMLResponse("""<!DOCTYPE html><html><head><title>Admin</title><meta charset='utf-8'/>
    <style>body{font-family:system-ui;margin:0;background:#f5f8fb;color:#0f2642;padding:2rem;}h1{margin-top:0;color:#134e9b;}table{border-collapse:collapse;width:100%;margin-top:1rem;}th,td{border:1px solid #d0d9e4;padding:.5rem .6rem;font-size:.8rem;}th{background:#e3eef9;text-align:left;}button{cursor:pointer;border:1px solid #134e9b;background:#fff;color:#134e9b;padding:.35rem .6rem;border-radius:4px;}button:hover{background:#134e9b;color:#fff;}#err{color:#b91c1c;font-size:.75rem;margin-top:.5rem;}#ok{color:#047857;font-size:.75rem;margin-top:.5rem;} .pill{display:inline-block;padding:.15rem .5rem;border-radius:1rem;font-size:.6rem;background:#134e9b;color:#fff;margin-left:.35rem;} .inactive{background:#b91c1c !important;}</style></head>
    <body><h1>Admin Portal</h1><div id='notice'>Loading...</div><div id='wrap'></div><div id='ok'></div><div id='err'></div><button id='back' style='margin-top:1rem'>Back</button>
    <script>
    const wrap=document.getElementById('wrap');
    const err=document.getElementById('err');
    const ok=document.getElementById('ok');
    document.getElementById('back').onclick=()=>{window.location='/dashboard'};
    function showErr(m){err.textContent=m;}
    function showOk(m){ok.textContent=m;}
    async function fetchJSON(url,opts={}){ const t=localStorage.getItem('access_token'); if(!t){ window.location='/'; return;} opts.headers=Object.assign({'Authorization':'Bearer '+t,'Content-Type':'application/json'},opts.headers||{}); const r=await fetch(url,opts); if(!r.ok) throw new Error(await r.text()); try{return await r.json();}catch{return {};} }
    function render(users){ let rows=users.map(u=>`<tr><td>${u.id}</td><td>${u.email}${u.is_admin?'<span class=\"pill\">ADMIN</span>':''}${u.is_active?'':'<span class=\"pill inactive\">INACTIVE</span>'}</td><td><button data-act='reset' data-id='${u.id}'>Reset PW</button> <button data-act='toggle' data-id='${u.id}'>Toggle Active</button></td></tr>`).join(''); wrap.innerHTML=`<table><thead><tr><th>ID</th><th>Email</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table>`; wrap.querySelectorAll('button[data-act]').forEach(btn=>{ btn.onclick=async()=>{ const id=btn.getAttribute('data-id'); const act=btn.getAttribute('data-act'); try{ if(act==='reset'){ const np=prompt('New password for user '+id+':'); if(!np) return; await fetchJSON('/auth/users/'+id+'/password',{method:'POST',body:JSON.stringify({password:np})}); showOk('Password reset'); } else if(act==='toggle'){ await fetchJSON('/auth/users/'+id+'/toggle_active',{method:'POST'}); showOk('Toggled active'); } loadUsers(); }catch(e){ showErr(e.message); } }; }); }
    async function ensureAdmin(){ try{ const me=await fetchJSON('/auth/me'); if(!me.is_admin){ showErr('Not an admin'); return false;} return true;} catch(e){ showErr('Auth required'); return false; } }
    async function loadUsers(){ try{ const users=await fetchJSON('/auth/users'); render(users); } catch(e){ showErr('Error '+e.message);} }
    (async()=>{ if(await ensureAdmin()){ loadUsers(); }})();
    </script></body></html>""")

@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}

# Final SPA fallback (must be last) so explicit routes (/health, /api, etc.) work.
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def spa_fallback(full_path: str, request: Request):
    if not REACT_DIST_ENABLED:
        raise HTTPException(status_code=404, detail="Not Found")
    if not full_path or full_path.startswith(("api/", "auth/", "health", "assets/", "admin", "docs")) or '.' in full_path:
        raise HTTPException(status_code=404, detail="Not Found")
    return HTMLResponse(_load_react_index())
