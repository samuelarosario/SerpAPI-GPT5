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
        return HTMLResponse("""<!DOCTYPE html><html lang='en'>
        <head>
            <meta charset='utf-8'/>
            <meta name='viewport' content='width=device-width, initial-scale=1'/>
            <meta http-equiv='Cache-Control' content='no-store'/>
            <title>Flights – Search</title>
            <style>
                :root{--link:#1a0dab;--text:#202124;--muted:#4d5156;--accent:#1a73e8;--ok:#188038;--chip:#e8f0fe}
                *{box-sizing:border-box}
                body{font-family:Arial,Helvetica,sans-serif;color:var(--text);margin:0;background:#fff}
                header{border-bottom:1px solid #eceff3}
                .topbar{max-width:980px;margin:0 auto;display:flex;gap:12px;align-items:center;padding:10px 16px}
                .logo{font-weight:700;color:#4285f4;letter-spacing:.5px}
                .search{flex:1;display:flex;gap:8px}
                .search input{flex:1;border:1px solid #dadce0;border-radius:24px;padding:.55rem .9rem;font-size:.95rem}
                .search button{border:1px solid #dadce0;background:#f8f9fa;border-radius:24px;padding:.55rem .9rem;cursor:pointer}
                .nav a{color:#5f6368;text-decoration:none;font-size:.9rem;margin-left:12px}
                main{max-width:980px;margin:0 auto;padding:8px 16px}
                .meta{color:var(--muted);font-size:.85rem;margin:.6rem 0}
                .filters{display:flex;gap:10px;align-items:center;margin:.5rem 0 1rem 0;border-bottom:1px solid #eceff3;padding-bottom:.6rem}
                .filters select{border:1px solid #dadce0;border-radius:8px;padding:.35rem .5rem}
            details.result{padding:10px 0;border-bottom:1px solid #f1f3f4}
            details.result > summary{list-style:none;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;cursor:pointer}
            details.result > summary::-webkit-details-marker{display:none}
            .result .left{flex:1;min-width:0}
            .result .title{font-size:1.1rem;color:var(--link);margin:0 0 .2rem 0}
            .crumbs{color:#5f6368;font-size:.85rem;margin-bottom:.25rem}
                .chips{margin-top:.35rem}
                .chip{display:inline-block;background:var(--chip);color:#174ea6;border:1px solid #d2e3fc;padding:.1rem .5rem;border-radius:999px;font-size:.7rem;margin-right:.25rem}
                .right{width:160px;text-align:right}
                .price{color:var(--ok);font-weight:700;font-size:1.2rem}
                .side{color:#5f6368;font-size:.8rem}
            .segments{margin-top:.6rem;border-left:3px solid #e8eaed;padding-left:10px}
            .seg{color:#3c4043;font-size:.9rem;line-height:1.35rem;margin:.2rem 0}
            .detailsHint{color:#5f6368;font-size:.8rem;margin-top:.2rem}
                .pagination{display:flex;justify-content:center;gap:10px;margin:18px 0}
                .pagination button{border:1px solid #dadce0;background:#fff;border-radius:6px;padding:.4rem .7rem;cursor:pointer}
                .back{color:#5f6368;text-decoration:none;font-size:.85rem;margin-left:8px}
                .error{color:#b91c1c}
            </style>
        </head>
        <body>
            <header>
                <div class='topbar'>
                    <div class='logo'>SerpFlights</div>
                    <form id='fsForm' class='search'>
                        <input id='origin_code' placeholder='Origin (e.g. JFK)' maxlength='5' required />
                        <input id='destination' placeholder='Destination (e.g. LAX)' maxlength='5' required />
                        <input id='date' type='date' required />
                        <button type='submit'>Search</button>
                    </form>
                    <nav class='nav'>
                        <a class='back' href='/dashboard'>&larr; Dashboard</a>
                    </nav>
                </div>
            </header>
            <main>
                <div id='status' class='meta'>Enter origin, destination and date (YYYY-MM-DD).</div>
                <div class='filters'>
                    <div>Sort</div>
                    <select id='sort'>
                        <option value='relevance'>Relevance</option>
                        <option value='price-asc'>Price: Low to high</option>
                        <option value='duration-asc'>Duration: Shortest first</option>
                        <option value='stops-asc'>Stops: Nonstop first</option>
                    </select>
                    <div style='flex:1'></div>
                    <div id='count' class='meta'></div>
                </div>
                <div id='results'></div>
                <div class='pagination' id='pager' style='display:none'>
                    <button id='prevBtn' disabled>Previous</button>
                    <div id='pageInfo' class='meta'></div>
                    <button id='nextBtn' disabled>Next</button>
                </div>
            </main>

            <script>
                const f=document.getElementById('fsForm');
                const statusEl=document.getElementById('status');
                const resEl=document.getElementById('results');
                const originInput=document.getElementById('origin_code');
                const destinationInput=document.getElementById('destination');
                const dateInput=document.getElementById('date');
                const sortSel=document.getElementById('sort');
                const countEl=document.getElementById('count');
                const pager=document.getElementById('pager');
                const prevBtn=document.getElementById('prevBtn');
                const nextBtn=document.getElementById('nextBtn');
                const pageInfo=document.getElementById('pageInfo');

                const PAGE_SIZE=10; let ALL=[], META={source:''}; let page=1;
                function today(){ const d=new Date(); const m=('0'+(d.getMonth()+1)).slice(-2); const day=('0'+d.getDate()).slice(-2); return `${d.getFullYear()}-${m}-${day}`; }
                dateInput.value=today();

                function authFetch(url){ const t=localStorage.getItem('access_token'); if(!t){window.location='/'; throw new Error('Not authenticated');} return fetch(url,{headers:{'Authorization':'Bearer '+t}}); }
                function fmtDuration(mins){ if(!mins||isNaN(mins)) return ''; const h=Math.floor(mins/60), m=mins%60; return `${h} hr ${m} min`; }
                function timePart(ts){ if(!ts) return ''; const t=(ts.split('T')[1]||ts).substring(0,5); return t; }
                function buildRoute(f){ const segs=f.flights||[]; if(!segs.length) return 'Flight'; const a=segs[0].departure_airport?.id||'?'; const b=segs[segs.length-1].arrival_airport?.id||'?'; return `${a} → ${b}`; }
                function buildStops(f){ const n=(f.flights||[]).length-1; return Math.max(0,n); }
                function priceStr(p){ if(!p) return 'N/A'; return (p+"").includes('USD')?p:`${p} USD`; }
                function airlinesStr(f){ const set=new Set((f.flights||[]).map(s=>s.airline).filter(Boolean)); return Array.from(set).join(', '); }
                function normalize(list){
                    return list.map(f=>{
                        const segs=f.flights||[];
                        const first=segs[0]||{}; const last=segs[segs.length-1]||{};
                        return {
                            raw:f,
                            route: buildRoute(f),
                            price: f.price,
                            priceNum: parseFloat((f.price+"").replace(/[^0-9.]/g,'')) || Number.POSITIVE_INFINITY,
                            duration: f.total_duration || f.duration || 0,
                            stops: buildStops(f),
                            airlines: airlinesStr(f),
                            dep: timePart(first.departure_time||''),
                            arr: timePart(last.arrival_time||''),
                        };
                    });
                }
                function applySort(list){
                    const mode=sortSel.value;
                    const arr=[...list];
                    if(mode==='price-asc') arr.sort((a,b)=>a.priceNum-b.priceNum);
                    else if(mode==='duration-asc') arr.sort((a,b)=>a.duration-b.duration);
                    else if(mode==='stops-asc') arr.sort((a,b)=>a.stops-b.stops);
                    return arr;
                }
                function render(){
                    const sorted=applySort(ALL);
                    const total=sorted.length; const totalPages=Math.max(1, Math.ceil(total/PAGE_SIZE));
                    page=Math.min(Math.max(1,page), totalPages);
                    const start=(page-1)*PAGE_SIZE; const slice=sorted.slice(start, start+PAGE_SIZE);
                    countEl.textContent = total ? `About ${total} results — Source: ${META.source}` : '';
                    pager.style.display = total>PAGE_SIZE ? 'flex' : 'none';
                    prevBtn.disabled = page<=1; nextBtn.disabled = page>=totalPages; pageInfo.textContent = `Page ${page} of ${totalPages}`;
                                resEl.innerHTML = slice.map(x=>{
                                    const chips = [x.airlines && `<span class='chip'>${x.airlines}</span>`, x.stops===0 && `<span class='chip'>Nonstop</span>`].filter(Boolean).join('');
                                    const segsFull=(x.raw.flights||[]).map(s=>{
                                        const al=s.airline||''; const fn=s.flight_number||''; const dep=s.departure_airport?.id||''; const arr=s.arrival_airport?.id||''; const dt=timePart(s.departure_time||''); const at=timePart(s.arrival_time||'');
                                        const dur=(s.duration?`${s.duration}m`:"");
                                        return `<div class='seg'>${dep} ${dt} → ${arr} ${at}${dur?` • ${dur}`:''}${al||fn?` — ${al}${fn?' '+fn:''}`:''}</div>`;
                                    }).join('');
                                    return `
                                        <details class='result'>
                                            <summary>
                                                <div class='left'>
                                                    <h3 class='title'>${x.route}</h3>
                                                    <div class='crumbs'>${fmtDuration(x.duration) || '—'} • ${x.stops} stop${x.stops===1?'':'s'} • ${x.dep || ''}${x.dep||x.arr?' → ':''}${x.arr||''}</div>
                                                    <div class='chips'>${chips}</div>
                                                    <div class='detailsHint'>Click to view segments</div>
                                                </div>
                                                <div class='right'>
                                                    <div class='price'>${priceStr(x.price)}</div>
                                                    <div class='side'>${META.source||''}</div>
                                                </div>
                                            </summary>
                                            <div class='segments'>${segsFull || '<div class="seg">No segment details.</div>'}</div>
                                        </details>`;
                                }).join('');
                }

                prevBtn.onclick=()=>{ page=Math.max(1,page-1); render(); }
                nextBtn.onclick=()=>{ page=page+1; render(); }
                sortSel.onchange=()=>{ page=1; render(); }

                async function runSearch(o,d,dt){
                    statusEl.textContent='Searching...'; resEl.innerHTML=''; countEl.textContent=''; pager.style.display='none';
                    const url=`/api/flight_search?origin=${encodeURIComponent(o)}&destination=${encodeURIComponent(d)}&date=${encodeURIComponent(dt)}`;
                    const r=await authFetch(url);
                    if(!r.ok){ const txt=await r.text(); statusEl.innerHTML='<span class="error">Error: '+txt+'</span>'; return; }
                    const data=await r.json();
                    if(!data.success){ statusEl.innerHTML='<span class="error">No results: '+(data.error||'unknown')+'</span>'; return; }
                    const flights=(data.data?.best_flights||[]).concat(data.data?.other_flights||[]);
                    META.source = data.source || '';
                    if(!flights.length){ statusEl.textContent='No results.'; resEl.innerHTML=''; return; }
                    statusEl.textContent = `Showing results for ${o} → ${d} on ${dt}`;
                    ALL = normalize(flights);
                    page=1; render();
                }

                f.addEventListener('submit', (e)=>{
                    e.preventDefault();
                    const o=(originInput.value||'').trim().toUpperCase();
                    const d=(destinationInput.value||'').trim().toUpperCase();
                    const dt=dateInput.value;
                    if(!o||!d||!dt){ statusEl.innerHTML='<span class="error">All fields are required.</span>'; return; }
                    runSearch(o,d,dt);
                });
            </script>
        </body></html>""")

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
