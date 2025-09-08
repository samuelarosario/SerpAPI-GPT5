from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.templating import Jinja2Templates
import pathlib

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

templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

app.include_router(auth_router)

@app.get("/", response_class=HTMLResponse, tags=["ui"])
async def root(request: Request):
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

@app.get("/flight-search", response_class=HTMLResponse, tags=["ui"])
async def flight_search_ui(request: Request):  # Simple HTML + JS form
    return HTMLResponse("""<!DOCTYPE html><html><head><title>Flight Search</title><meta charset='utf-8'/><meta http-equiv='Cache-Control' content='no-store' />
    <style>body{font-family:system-ui;margin:0;background:#eef5fb;min-height:100vh;}header{background:#134e9b;color:#fff;padding:.9rem 1.2rem;}h1{margin:0;font-size:1.15rem;}main{max-width:860px;margin:1.2rem auto;background:#fff;padding:1.2rem 1.5rem;border-radius:10px;box-shadow:0 2px 8px -2px rgba(0,40,90,.15);}form{display:flex;flex-wrap:wrap;gap:.75rem;align-items:flex-end;margin-bottom:1rem;}label{font-size:.65rem;text-transform:uppercase;letter-spacing:.5px;font-weight:600;color:#134e9b;display:block;margin-bottom:.25rem;}input{padding:.55rem .6rem;border:1px solid #bcd3ea;border-radius:6px;font-size:.85rem;background:#f5faff;min-width:140px;}button{padding:.6rem 1rem;border:none;background:#2563eb;color:#fff;border-radius:6px;cursor:pointer;font-weight:600;font-size:.8rem;}button:hover{background:#134e9b;}#results{margin-top:1rem;} .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:.9rem;margin-top:.75rem;} .card{border:1px solid #d5e3f2;padding:.65rem .7rem;border-radius:8px;background:#f8fbfe;font-size:.7rem;line-height:1.25rem;} .src{font-weight:600;color:#0f2747;font-size:.75rem;margin-bottom:.25rem;} .price{color:#047857;font-weight:600;} .err{color:#b91c1c;font-size:.7rem;margin-top:.5rem;} .meta{font-size:.6rem;color:#475569;margin-top:.4rem;} a.back{color:#fff;text-decoration:none;margin-left:1rem;font-size:.7rem;} .tags span{display:inline-block;background:#134e9b;color:#fff;font-size:.55rem;padding:.15rem .45rem;border-radius:1rem;margin-right:.3rem;margin-top:.25rem;}</style></head>
        <body><header><h1>Flight Search <a class='back' href='/dashboard'>&larr; Back</a></h1></header><main>
        <form id='fsForm'>
            <div><label for='origin_code'>Origin</label><input id='origin_code' name='origin' placeholder='e.g. JFK' required maxlength='5'/></div>
            <div><label for='destination'>Destination</label><input id='destination' name='destination' placeholder='e.g. LAX' required maxlength='5'/></div>
            <div><label for='date'>Date</label><input id='date' name='date' type='date' required/></div>
            <div><button type='submit'>Search</button></div>
        </form>
        <div id='status' class='meta'>Enter origin, destination and date (YYYY-MM-DD).</div>
        <div id='results'></div>
        <script>
        const f=document.getElementById('fsForm');
        const statusEl=document.getElementById('status');
        const resEl=document.getElementById('results');
    const originInput=document.getElementById('origin_code');
        const destinationInput=document.getElementById('destination');
        const dateInput=document.getElementById('date');
        function authFetch(url){ const t=localStorage.getItem('access_token'); if(!t){window.location='/'; return Promise.reject(new Error('Not authenticated'));} return fetch(url,{headers:{'Authorization':'Bearer '+t}}); }
        f.addEventListener('submit',async(e)=>{ 
            e.preventDefault();
            resEl.innerHTML='';
            const o=(originInput.value||'').trim().toUpperCase();
            const d=(destinationInput.value||'').trim().toUpperCase();
            const dt=dateInput.value;
            if(!o||!d||!dt){ statusEl.textContent='All fields required.'; return; }
            statusEl.textContent='Searching...';
            try { 
                const url=`/api/flight_search?origin=${encodeURIComponent(o)}&destination=${encodeURIComponent(d)}&date=${encodeURIComponent(dt)}`;
                console.debug('Flight search request', url);
                const r=await authFetch(url);
                if(!r.ok){ const txt=await r.text(); statusEl.textContent='Error: '+txt; console.error('Search HTTP error', txt); return; }
                const data=await r.json();
                console.debug('Flight search response', data);
                if(!data.success){ statusEl.textContent='No results: '+(data.error||'unknown'); return; }
                statusEl.textContent=`Source: ${data.source} | Search ID: ${data.search_id||'n/a'}`;
                const flights=(data.data?.best_flights||[]).concat(data.data?.other_flights||[]);
                if(flights.length===0){ resEl.innerHTML='<p class="meta">No flights found.</p>'; return; }
                let html='<div class="grid">';
                flights.slice(0,30).forEach(flt=>{ 
                    html+=`<div class='card'>
                        <div class='src'>${flt.flights?flt.flights.join(' • '):(flt.flight||'Flight')}</div>
                        <div class='price'>${flt.price||'N/A'}</div>
                        <div class='meta'>${flt.departure_airport||''} → ${flt.arrival_airport||''}</div>
                        <div class='meta'>Dur: ${(flt.duration||'').toString().replace('duration:','')}</div>
                        <div class='tags'>${flt.type?`<span>${flt.type}</span>`:''}${flt.airline?`<span>${flt.airline}</span>`:''}</div>
                    </div>`; 
                });
                html+='</div>';
                resEl.innerHTML=html; 
            } catch(err){ 
                console.error('Flight search exception', err);
                statusEl.textContent='Error: '+err.message; 
            }
        });
        </script>
        </main></body></html>""")

@app.get("/api/flight_search", response_class=JSONResponse, tags=["flight"])
async def api_flight_search(origin: str = Query(..., min_length=3, max_length=5, description="Origin IATA"),
                            destination: str = Query(..., min_length=3, max_length=5, description="Destination IATA"),
                            date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$", description="Outbound date YYYY-MM-DD")):
    # Minimal wrapper: only uses origin/destination/date; relies on existing EFS caching logic.
    client = _get_efs_client()
    def run_search():
        return client.search_flights(departure_id=origin.upper(), arrival_id=destination.upper(), outbound_date=date)
    result = await run_in_threadpool(run_search)
    return JSONResponse(result)


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
