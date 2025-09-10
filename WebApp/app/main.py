from fastapi import FastAPI, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
                .pill{display:inline-block;margin-left:.4rem;padding:.05rem .45rem;border-radius:999px;font-size:.65rem;vertical-align:middle;background:#0ea5e9;color:#fff}
                .pill.v2{background:#854d0e}
                .search{flex:1;display:flex;gap:8px}
                .search input{flex:1;border:1px solid #dadce0;border-radius:24px;padding:.55rem .9rem;font-size:.95rem}
                .search button{border:1px solid #dadce0;background:#f8f9fa;border-radius:24px;padding:.55rem .9rem;cursor:pointer}
                .search .util{background:#fff;border-color:#cbd5e1}
                .nav a{color:#5f6368;text-decoration:none;font-size:.9rem;margin-left:12px}
                main{max-width:980px;margin:0 auto;padding:8px 16px}
                .meta{color:var(--muted);font-size:.85rem;margin:.6rem 0}
            .headline{color:var(--accent);font-size:1.35rem;font-weight:700;margin:.8rem 0;text-align:left}
            .filters{display:flex;gap:10px;align-items:center;margin:.5rem 0 1rem 0;border-bottom:1px solid #eceff3;padding-bottom:.6rem}
                .filters select{border:1px solid #dadce0;border-radius:8px;padding:.35rem .5rem}
            .filters .btn{border:1px solid #dadce0;background:#fff;border-radius:6px;padding:.35rem .6rem;cursor:pointer;font-size:.85rem}
            .tabs{display:flex;gap:8px;border-bottom:1px solid #eceff3;margin:.25rem 0 1rem 0}
            .tab{border:1px solid #dadce0;background:#fff;border-radius:6px 6px 0 0;padding:.35rem .7rem;cursor:pointer;font-size:.85rem}
            .tab.active{background:#e8f0fe;border-bottom-color:#e8f0fe;color:#174ea6}
            details.result{padding:10px 0;border-bottom:1px solid #f1f3f4}
            details.result > summary{list-style:none;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;cursor:pointer}
            details.result > summary::-webkit-details-marker{display:none}
            .result .left{flex:1;min-width:0}
            .result .title{font-size:1.1rem;color:var(--accent);margin:0 0 .2rem 0}
            .crumbs{color:#5f6368;font-size:.85rem;margin-bottom:.25rem}
                .chips{margin-top:.35rem}
                .chip{display:inline-block;background:var(--chip);color:#174ea6;border:1px solid #d2e3fc;padding:.1rem .5rem;border-radius:999px;font-size:.7rem;margin-right:.25rem}
            /* Two-column leg route with per-airport times */
            .leg-route.two-col{display:flex;align-items:flex-start;gap:10px;justify-content:space-between}
            .leg-route.two-col .loc{flex:1;min-width:0}
            .leg-route.two-col .name{font-weight:600;color:#111827}
            .leg-route.two-col .sub{color:var(--muted);font-size:.85rem;margin-top:2px}
            .leg-route.two-col .arrow{color:#6b7280;padding:0 4px;align-self:center}
                .right{width:160px;text-align:right}
                .price{color:var(--ok);font-weight:700;font-size:1.2rem}
                .side{color:#5f6368;font-size:.8rem}
            .segments{margin-top:.6rem;border-left:3px solid #e8eaed;padding-left:10px}
            .seg{color:#3c4043;font-size:.9rem;line-height:1.35rem;margin:.2rem 0}
            .detailsHint{color:#5f6368;font-size:.8rem;margin-top:.2rem}
            .rowActions{margin-top:.3rem}
            .toggleLink{border:1px solid #dadce0;background:#fff;border-radius:4px;padding:.2rem .45rem;cursor:pointer;font-size:.8rem;color:#1a73e8}
            .itinerary{display:flex;flex-direction:column;gap:.6rem;margin:.6rem 0}
            .leg{display:flex;gap:10px}
            .leg .dot{width:10px}
            .dot::before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;background:#5f6368;position:relative;top:6px}
            .leg-main{flex:1}
            .leg-times{font-weight:600;color:#202124}
            .leg-route{color:#5f6368;font-size:.9rem}
            .leg-meta{color:#5f6368;font-size:.85rem;margin-top:.2rem}
            .layover{padding:.45rem .6rem;background:#f8f9fa;border:1px dashed #e0e3e7;border-radius:6px;color:#5f6368;font-size:.85rem}
            .layover.warn{border-color:#f59e0b;background:#fff7ed}
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
                        <input id='origin_code' placeholder='Origin: code, city, or name' maxlength='32' list='originList' required />
                        <input id='destination' placeholder='Destination: code, city, or name' maxlength='32' list='destList' required />
                        <input id='date' type='date' required />
                        <input id='return_date' type='date' placeholder='Return (optional)' />
                        <select id='trip_type' title='Trip type'>
                            <option value='round' selected>2-way (Round trip)</option>
                            <option value='oneway'>1-way</option>
                        </select>
                        <select id='travel_class' title='Travel class'>
                            <option value='1' selected>Economy</option>
                            <option value='2'>Premium</option>
                            <option value='3'>Business</option>
                            <option value='4'>First</option>
                        </select>
                        <button type='submit' id='searchBtn'>Search</button>
                    </form>
                    <datalist id='originList'></datalist>
                    <datalist id='destList'></datalist>
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
                <div class='tabs'>
                    <button id='tabOutbound' class='tab active'>Outbound</button>
                    <button id='tabInbound' class='tab'>Inbound</button>
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
                const returnDateInput=document.getElementById('return_date');
                const tripTypeSel=document.getElementById('trip_type');
                const classSelect=document.getElementById('travel_class');
                const sortSel=document.getElementById('sort');
                const searchBtn=document.getElementById('searchBtn');
                const swapBtn=document.getElementById('swapBtn');
                const clearBtn=document.getElementById('clearBtn');
            const countEl=document.getElementById('count');
            const expandAllBtn=document.getElementById('expandAll');
            const collapseAllBtn=document.getElementById('collapseAll');
                const pager=document.getElementById('pager');
                const prevBtn=document.getElementById('prevBtn');
                const nextBtn=document.getElementById('nextBtn');
                const pageInfo=document.getElementById('pageInfo');
                const tabOut=document.getElementById('tabOutbound');
                const tabIn=document.getElementById('tabInbound');

                const PAGE_SIZE=10; let ALL=[], OUT=[], IN=[], META={source:''}; let page=1; let AIRPORTS = Object.create(null); let CURRENT_DT=''; let CURRENT_RET_DT=''; let CURRENT_ORIG=''; let CURRENT_DEST=''; let currentView='outbound';
                function todayPlus(n){ const d=new Date(); d.setDate(d.getDate()+Number(n||0)); const m=('0'+(d.getMonth()+1)).slice(-2); const day=('0'+d.getDate()).slice(-2); return `${d.getFullYear()}-${m}-${day}`; }
                // Default to tomorrow to satisfy validation (min 1 day ahead)
                if(!dateInput.value){ dateInput.value=todayPlus(1); }
                // Enforce return date > outbound: set min to outbound+1 and clear invalid value
                function dateToYmd(d){ const m=('0'+(d.getMonth()+1)).slice(-2); const day=('0'+d.getDate()).slice(-2); return `${d.getFullYear()}-${m}-${day}`; }
                function addDaysYmd(ymd, n){ const d=ymdToDate(ymd); if(!d) return ''; d.setDate(d.getDate()+Number(n||0)); return dateToYmd(d); }
                function syncReturnMin(){
                    const out=dateInput.value;
                    if(out){
                        const min = addDaysYmd(out, 1);
                        if(min){ returnDateInput.min = min; }
                        if(returnDateInput.value && returnDateInput.value <= out){ returnDateInput.value=''; }
                    } else {
                        returnDateInput.removeAttribute('min');
                    }
                }
                syncReturnMin();
                dateInput.addEventListener('change', syncReturnMin);

                function authFetch(url){ const t=localStorage.getItem('access_token'); if(!t){window.location='/'; throw new Error('Not authenticated');} return fetch(url,{headers:{'Authorization':'Bearer '+t}}); }
                function setBusy(b){
                    [originInput,destinationInput,dateInput,returnDateInput,tripTypeSel,classSelect,sortSel,searchBtn,swapBtn,clearBtn].forEach(el=>{ if(el){ el.disabled=!!b; }});
                    if(searchBtn){ searchBtn.textContent = b? 'Searching…' : 'Search'; }
                }
                function updateUrl(o,d,dt,ret,tt,tc){
                    try{
                        const p = new URLSearchParams();
                        if(o) p.set('o', o);
                        if(d) p.set('d', d);
                        if(dt) p.set('dt', dt);
                        if(ret) p.set('ret', ret);
                        if(tt) p.set('tt', tt);
                        if(tc) p.set('tc', String(tc));
                        const q = p.toString();
                        const url = q ? (`${location.pathname}?${q}`) : location.pathname;
                        history.replaceState(null, '', url);
                    }catch{}
                }
                function saveLast(o,d,dt,ret,tt,tc){
                    try{ localStorage.setItem('fsV2_last', JSON.stringify({o,d,dt,ret,tt,tc})); }catch{}
                }
                function loadInitial(){
                    try{
                        const sp = new URLSearchParams(location.search);
                        const gotQ = sp.get('o')||sp.get('d')||sp.get('dt');
                        let data = null;
                        if(gotQ){
                            data = { o: (sp.get('o')||'').toUpperCase(), d:(sp.get('d')||'').toUpperCase(), dt: sp.get('dt')||'', ret: sp.get('ret')||'', tt: sp.get('tt')||'round', tc: Number(sp.get('tc')||'1') };
                        } else {
                            try{ data = JSON.parse(localStorage.getItem('fsV2_last')||'null'); }catch{ data=null }
                        }
                        if(data){
                            originInput.value = data.o||'';
                            destinationInput.value = data.d||'';
                            dateInput.value = data.dt||dateInput.value;
                            returnDateInput.value = data.ret||'';
                            if(tripTypeSel){ tripTypeSel.value = (data.tt==='oneway'?'oneway':'round'); const ev = new Event('change'); tripTypeSel.dispatchEvent(ev); }
                            if(classSelect){ classSelect.value = String(data.tc||'1'); }
                        }
                    }catch{}
                }
                // Trip type behavior: disable/clear return date when 1-way
                if(tripTypeSel){
                    const syncTripUi=()=>{
                        const isOneWay = tripTypeSel.value === 'oneway';
                        returnDateInput.disabled = isOneWay;
                        if(isOneWay){ returnDateInput.value=''; }
                        syncReturnMin();
                    };
                    tripTypeSel.addEventListener('change', syncTripUi);
                    syncTripUi();
                }
                // --- Autosuggest for airports ---
                async function fetchAirports(q){
                    if(!q||q.length<2) return [];
                    try{
                        const r = await authFetch(`/api/airports/suggest?q=${encodeURIComponent(q)}`);
                        if(!r.ok) return [];
                        const data = await r.json();
                        return Array.isArray(data)? data : [];
                    }catch{return []}
                }
                function populateDatalist(listId, items){
                    const dl = document.getElementById(listId);
                    if(!dl) return;
                    dl.innerHTML = items.slice(0,10).map(it=>{
                        const label = `${it.code} — ${it.name}${it.city?` (${it.city})`:''}${it.country?`, ${it.country}`:''}`;
                        const val = it.code;
                        return `<option value="${val}" label="${label}"></option>`;
                    }).join('');
                }
                function attachSuggest(inputEl, listId){
                    let last=''; let timer=null;
                    inputEl.addEventListener('input', ()=>{
                        const v=inputEl.value.trim();
                        if(v===last) return; last=v;
                        clearTimeout(timer);
                        timer=setTimeout(async()=>{
                            const items = await fetchAirports(v);
                            populateDatalist(listId, items);
                        }, 200);
                    });
                }
                attachSuggest(originInput,'originList');
                attachSuggest(destinationInput,'destList');

                function isIata(s){ return /^[A-Z]{3}$/.test(String(s||'').trim().toUpperCase()); }
                function ymdToDate(ymd){ if(!ymd) return null; try{ const d=new Date(String(ymd).trim()+"T00:00:00"); return isNaN(d.getTime())? null : d; }catch{return null} }
                function daysFromToday(ymd){ const d=ymdToDate(ymd); if(!d) return null; const t=new Date(); const td=new Date(t.getFullYear(),t.getMonth(),t.getDate()); const dd=new Date(d.getFullYear(),d.getMonth(),d.getDate()); return Math.round((dd-td)/86400000); }

                function fmtDuration(mins){ if(mins==null||isNaN(mins)) return ''; const h=Math.floor(mins/60), m=mins%60; return `${h} hr ${m} min`; }
        function parseTs(ts){
                    if(!ts) return null;
                    if(typeof ts === 'number') return new Date(ts);
                    if(typeof ts === 'string'){
                        let s = ts.trim();
                        // If ISO-like, trust it
            if(/^[0-9]{4}-[0-9]{2}-[0-9]{2}T/.test(s)){
                            const d = new Date(s); if(!isNaN(d.getTime())) return d;
                        }
                        // Handle "YYYY-MM-DD HH:MM[:SS] [AM|PM]" -> build ISO local
            const m = s.match(/^([0-9]{4}-[0-9]{2}-[0-9]{2})[ T]([0-9]{1,2}):([0-9]{2})(?::([0-9]{2}))? *(AM|PM)?$/i);
                        if(m){
                            const date = m[1]; let hh = parseInt(m[2],10); const mm = m[3]; const ss = m[4]||'00'; const ap=m[5];
                            if(ap){ const isPM=/pm/i.test(ap); if(hh===12){ hh=isPM?12:0; } else { hh = isPM? hh+12 : hh; } }
                            const hh2 = ('0'+hh).slice(-2);
                            const d = new Date(`${date}T${hh2}:${mm}:${ss}`);
                            if(!isNaN(d.getTime())) return d;
                        }
                        // Fallback: try replacing single space between date and time with T
            if(/^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}/.test(s)){
                            const d = new Date(s.replace(' ', 'T'));
                            if(!isNaN(d.getTime())) return d;
                        }
                        const d2 = new Date(s);
                        if(!isNaN(d2.getTime())) return d2;
                    }
                    try { const d=new Date(ts); return isNaN(d.getTime())? null : d; } catch { return null; }
                }
                function toDate(ts){ return parseTs(ts); }
                function fmtTime(ts){ const d=toDate(ts); if(!d) return ''; return d.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'}); }
        function inferHM(ts){ if(!ts) return ''; const s=String(ts); const m=s.match(/([0-9]{1,2}:[0-9]{2}(?:[ ]*[AP]M)?)/i); return m? m[1] : ''; }
                function dateShort(ts){ const d=toDate(ts); if(!d) return ''; return d.toLocaleDateString([], {month:'short', day:'2-digit'}); }
                function dateShortYMD(ymd){ if(!ymd) return ''; try{ const d=new Date(String(ymd).trim()+"T00:00:00"); if(!isNaN(d.getTime())){ return d.toLocaleDateString([], {month:'short', day:'2-digit'}); } }catch{} return ''; }
                function dayDiff(a,b){ const da=toDate(a), db=toDate(b); if(!da||!db) return 0; const ad=new Date(da.getFullYear(),da.getMonth(),da.getDate()); const bd=new Date(db.getFullYear(),db.getMonth(),db.getDate()); return Math.round((bd-ad)/86400000); }
                function minutesBetween(a,b){ const da=toDate(a), db=toDate(b); if(!da||!db) return null; return Math.max(0, Math.round((db-da)/60000)); }
                function timePart(ts){ const d=toDate(ts); if(!d) return ''; return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}); }
                function cityOrName(code){ const a=AIRPORTS && AIRPORTS[code]; return (a?.city || a?.name || code || ''); }
                function nameOf(code){ const a=AIRPORTS && AIRPORTS[code]; return (a?.name || ''); }
                function buildRoute(f){ const segs=f.flights||[]; if(!segs.length) return 'Flight'; const a=(segs[0].departure_airport?.id||'').toUpperCase(); const b=(segs[segs.length-1].arrival_airport?.id||'').toUpperCase(); const la=`${cityOrName(a)} (${a})`; const lb=`${cityOrName(b)} (${b})`; return `${la} → ${lb}`; }
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
                            depTS: first.departure_time||'',
                            arrTS: last.arrival_time||'',
                            layovers: Array.isArray(f.layovers) ? f.layovers : [],
                            firstDep: (first?.departure_airport?.id||'').toUpperCase(),
                            lastArr: (last?.arrival_airport?.id||'').toUpperCase(),
                        };
                    });
                }
                function directionOf(x){
                    const a=(x.firstDep||'').toUpperCase();
                    const b=(x.lastArr||'').toUpperCase();
                    if(a && b){
                        if (a===CURRENT_ORIG && b===CURRENT_DEST) return 'outbound';
                        if (a===CURRENT_DEST && b===CURRENT_ORIG) return 'inbound';
                    }
                    return 'other';
                }
                function recomputeBuckets(){
                    OUT = []; IN = [];
                    for(const x of ALL){
                        const dir = directionOf(x);
                        if(dir==='outbound') OUT.push(x);
                        else if(dir==='inbound') IN.push(x);
                    }
                    if(tabOut) tabOut.textContent = `Outbound (${OUT.length})`;
                    if(tabIn) tabIn.textContent = `Inbound (${IN.length})`;
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
                    const baseList = currentView==='inbound' ? IN : OUT;
                    const sorted=applySort(baseList);
                    const total=sorted.length; const totalPages=Math.max(1, Math.ceil(total/PAGE_SIZE));
                    page=Math.min(Math.max(1,page), totalPages);
                    const start=(page-1)*PAGE_SIZE; const slice=sorted.slice(start, start+PAGE_SIZE);
                                countEl.textContent = total ? `About ${total} ${currentView} results — Source: ${META.source}` : '';
                    pager.style.display = total>PAGE_SIZE ? 'flex' : 'none';
                    prevBtn.disabled = page<=1; nextBtn.disabled = page>=totalPages; pageInfo.textContent = `Page ${page} of ${totalPages}`;
                                resEl.innerHTML = slice.map((x,idx)=>{
                                    const chips = [x.airlines && `<span class='chip'>${x.airlines}</span>`, x.stops===0 && `<span class='chip'>Nonstop</span>`].filter(Boolean).join('');
                                                const legs = (x.raw.flights||[]);
                                                const parts = [];
                                                for(let i=0;i<legs.length;i++){
                                                    const s=legs[i];
                                                    const depA=(s.departure_airport?.id||'').toUpperCase(); const arrA=(s.arrival_airport?.id||'').toUpperCase();
                                                    const dt=fmtTime(s.departure_time||''); const at=fmtTime(s.arrival_time||'');
                                                    const dd=dayDiff(s.departure_time, s.arrival_time); const plusDay = dd>0? ` + ${dd} day${dd>1?'s':''}`:'';
                                                    const durMin = (s.duration? Number(s.duration): null);
                                                    const durStr = durMin? fmtDuration(durMin) : '';
                                                    const al=s.airline||''; const fn=s.flight_number||'';
                                                    const depCity = cityOrName(depA); const arrCity = cityOrName(arrA);
                                                    const depHM = inferHM(s.departure_time)||fmtTime(s.departure_time)||'';
                                                    const arrHM = inferHM(s.arrival_time)||fmtTime(s.arrival_time)||'';
                                                    parts.push(`
                                                        <div class='leg'>
                                                            <div class='dot'></div>
                                                            <div class='leg-main'>
                                                                <div class='leg-route two-col'>
                                                                    <div class='loc'>
                                                                        <div class='name'>${depCity} (${depA})</div>
                                                                        <div class='sub time'>${depHM}</div>
                                                                    </div>
                                                                    <div class='arrow'>→</div>
                                                                    <div class='loc'>
                                                                        <div class='name'>${arrCity} (${arrA})</div>
                                                                        <div class='sub time'>${arrHM}${plusDay}</div>
                                                                    </div>
                                                                </div>
                                                                <div class='leg-meta'>${[al && al, fn && ('• '+fn), durStr && ('• '+durStr)].filter(Boolean).join(' ')}</div>
                                                            </div>
                                                        </div>
                                                    `);
                                                    // Render provided layovers if present at matching index
                                                    if(i < x.layovers.length){
                                                        const lay = x.layovers[i];
                                                        const code = (lay?.id || '').toUpperCase();
                                                        const mins = Number(lay?.duration) || 0;
                                                        const overnight = !!lay?.overnight;
                                                        const label = `${fmtDuration(mins)} layover • ${cityOrName(code)} (${code})`;
                                                        parts.push(`<div class='layover ${overnight?'warn':''}'>${label}${overnight?' • Overnight layover ⚠️':''}</div>`);
                                                    }
                                                }
                                                const segsFull = `<div class='itinerary'>${parts.join('')}</div>`;
                                                const first=legs[0]||{}; const last=legs[legs.length-1]||{};
                                                // Prefer raw strings when provided (avoid relying on parsing)
                                                const depTimeStr = inferHM(first.departure_time) || fmtTime(first.departure_time) || (x.dep||'');
                                                const arrTimeStr = inferHM(last.arrival_time) || fmtTime(last.arrival_time) || (x.arr||'');
                                                const depDateStr = dateShort(first.departure_time) || (CURRENT_DT ? dateShortYMD(CURRENT_DT) : '');
                                                const arrDateStr = dateShort(last.arrival_time) || (CURRENT_DT ? dateShortYMD(CURRENT_DT) : '');
                                                const crumbTimes = `${depTimeStr || ''} (${depDateStr})${(depTimeStr||arrTimeStr)?' → ':''}${arrTimeStr || ''} (${arrDateStr})`;
                                    return `
                                        <details class='result' data-relidx='${start+idx}'>
                                            <summary>
                                                <div class='left'>
                                                    <h3 class='title'>${x.route}</h3>
                                                    <div class='crumbs'>${fmtDuration(x.duration) || '—'} • ${x.stops} stop${x.stops===1?'':'s'} • ${crumbTimes}</div>
                                                    <div class='chips'>${chips}</div>
                                                    <div class='rowActions'>
                                                        <button type='button' class='toggleLink' data-role='toggle'>Show details</button>
                                                    </div>
                                                </div>
                                                <div class='right'>
                                                    <div class='price'>${priceStr(x.price)}</div>
                                                    <div class='side'>${META.source||''}</div>
                                                </div>
                                            </summary>
                                            <div class='segments'>${segsFull || '<div class="seg">No segment details.</div>'}</div>
                                        </details>`;
                                }).join('');
                                // Make summaries keyboard-focusable and sync toggle button text
                                const detailsList = Array.from(resEl.querySelectorAll('details.result'));
                                detailsList.forEach(d=>{
                                    const sum=d.querySelector('summary'); if(sum) sum.tabIndex=0;
                                    const btn=d.querySelector('.toggleLink');
                                    const setText=()=>{ if(btn) btn.textContent = d.open ? 'Hide details' : 'Show details'; };
                                    setText(); d.addEventListener('toggle', setText);
                                });
                }

                prevBtn.onclick=()=>{ page=Math.max(1,page-1); render(); }
                nextBtn.onclick=()=>{ page=page+1; render(); }
                sortSel.onchange=()=>{ page=1; render(); }
                if(tabOut){ tabOut.onclick=()=>{ currentView='outbound'; tabOut.classList.add('active'); if(tabIn) tabIn.classList.remove('active'); page=1; render(); }; }
                if(tabIn){ tabIn.onclick=()=>{ currentView='inbound'; tabIn.classList.add('active'); if(tabOut) tabOut.classList.remove('active'); page=1; render(); }; }

                async function runSearch(o,d,dt,ret,tclass){
                    statusEl.className='meta';
                    statusEl.textContent='Searching...'; resEl.innerHTML=''; countEl.textContent=''; pager.style.display='none';
                    setBusy(true);
                    CURRENT_DT = dt || '';
                    CURRENT_RET_DT = ret || '';
                    CURRENT_ORIG = (o||'').toUpperCase();
                    CURRENT_DEST = (d||'').toUpperCase();
                    const tc = (tclass && Number(tclass)) ? Number(tclass) : (Number(classSelect?.value)||1);
                    let url=`/api/flight_search?origin=${encodeURIComponent(o)}&destination=${encodeURIComponent(d)}&date=${encodeURIComponent(dt)}&travel_class=${tc}`;
                    const isOneWay = (tripTypeSel?.value === 'oneway');
                    if(isOneWay){
                        url += `&one_way=1`;
                    } else if(ret){
                        url += `&return_date=${encodeURIComponent(ret)}`;
                    }
                    updateUrl(CURRENT_ORIG, CURRENT_DEST, CURRENT_DT, CURRENT_RET_DT, (isOneWay?'oneway':'round'), tc);
                    const r=await authFetch(url);
                    if(!r.ok){ const txt=await r.text(); statusEl.innerHTML='<span class="error">Error: '+txt+'</span>'; return; }
                    const data=await r.json();
                    if(!data.success){ statusEl.innerHTML='<span class="error">No results: '+(data.error||'unknown')+'</span>'; return; }
                    const flights=(data.data?.best_flights||[]).concat(data.data?.other_flights||[]);
                    META.source = data.source || '';
                    // Extract search parameters when available to show class and trip mode
                    const SP = (data && data.data && data.data.search_parameters) ? data.data.search_parameters : {};
                    const CLASS_MAP = {1:'Economy', 2:'Premium', 3:'Business', 4:'First'};
                    const classLabel = CLASS_MAP[Number(SP.travel_class || (classSelect?.value||1))] || '';
                    const isRoundTrip = !!SP.return_date || !!CURRENT_RET_DT;
                    const usedReturnDate = SP.return_date || CURRENT_RET_DT || '';
                    if(!flights.length){ statusEl.className='meta'; statusEl.textContent='No results.'; resEl.innerHTML=''; return; }
                    // Build list of unique airport codes and fetch airport details in batch
                    const setCodes = new Set([o.toUpperCase(), d.toUpperCase()]);
                    for(const f of flights){
                        for(const s of (f.flights||[])){
                            const a=(s?.departure_airport?.id||'').toUpperCase();
                            const b=(s?.arrival_airport?.id||'').toUpperCase();
                            if(a) setCodes.add(a); if(b) setCodes.add(b);
                        }
                        // include layover airports so labels render properly
                        for(const lay of (f.layovers||[])){
                            const c=(lay?.id||'').toUpperCase(); if(c) setCodes.add(c);
                        }
                    }
                    try{
                        const list = Array.from(setCodes).join(',');
                        const rr = await authFetch(`/api/airports/by_codes?codes=${encodeURIComponent(list)}`);
                        if(rr.ok){ const arr = await rr.json(); const map = Object.create(null); (arr||[]).forEach(it=>{ if(it && it.code){ map[(it.code||'').toUpperCase()] = it; } }); AIRPORTS = map; }
                    }catch{}
                    // Resolve friendly names for origin/destination for a larger heading
                    async function fetchAirport(code){
                        try{
                            const rr = await authFetch(`/api/airports/by_code?code=${encodeURIComponent(code)}`);
                            if(!rr.ok) return null;
                            return await rr.json();
                        }catch{return null}
                    }
                    const [ao, ad] = await Promise.all([fetchAirport(o), fetchAirport(d)]);
                    const oLabel = `${(ao?.city||ao?.name||o)} (${o})`;
                    const dLabel = `${(ad?.city||ad?.name||d)} (${d})`;
                    statusEl.className='headline';
                    const modeStr = isRoundTrip ? '2-way' : '1-way';
                    const suffix = [classLabel, modeStr].filter(Boolean).join(' • ');
                    // Break into multiple lines: route, dates, details
                    const datesLine = usedReturnDate ? `on ${dt} • return ${usedReturnDate}` : `on ${dt}`;
                    statusEl.innerHTML = `<div>${oLabel} to ${dLabel}</div><div>${datesLine}</div>${suffix?`<div>${suffix}</div>`:''}`;
                    ALL = normalize(flights);
                    recomputeBuckets();
                    // default to outbound tab if it has items; otherwise show inbound
                    if(OUT.length>0){ currentView='outbound'; if(tabOut){ tabOut.classList.add('active'); } if(tabIn){ tabIn.classList.remove('active'); } }
                    else { currentView='inbound'; if(tabIn){ tabIn.classList.add('active'); } if(tabOut){ tabOut.classList.remove('active'); } }
                    saveLast(CURRENT_ORIG, CURRENT_DEST, CURRENT_DT, usedReturnDate, (isOneWay?'oneway':'round'), tc);
                    page=1; render();
                    setBusy(false);
                }

                        f.addEventListener('submit', async (e)=>{
                    e.preventDefault();
                    let o=(originInput.value||'').trim().toUpperCase();
                    let d=(destinationInput.value||'').trim().toUpperCase();
                    const dt=(dateInput.value||'').trim();
                    const ret=(returnDateInput.value||'').trim();
                    const tclass=(classSelect?.value)||'1';
                    if(!o||!d||!dt){ statusEl.innerHTML='<span class="error">All fields are required.</span>'; return; }
                    // Resolve non-IATA inputs via suggest API (pick first match)
                    if(!isIata(o)){
                        const list = await fetchAirports(o);
                        if(list && list.length && isIata(list[0].code)) o = list[0].code.toUpperCase();
                    }
                    if(!isIata(d)){
                        const list = await fetchAirports(d);
                        if(list && list.length && isIata(list[0].code)) d = list[0].code.toUpperCase();
                    }
                    if(!isIata(o) || !isIata(d)){
                        statusEl.innerHTML='<span class="error">Please use a valid 3-letter IATA airport code for origin and destination.</span>';
                        return;
                    }
                    // Date horizon checks: outbound at least +1 day; return (if any) >= outbound
                    const diff = daysFromToday(dt);
                    if(diff===null || diff < 1){ statusEl.innerHTML='<span class="error">Outbound date must be at least 1 day from today.</span>'; return; }
                    if(tripTypeSel?.value !== 'oneway'){
                        if(!ret){ statusEl.innerHTML='<span class="error">Return date is required for 2-way; it will be used for the inbound search.</span>'; return; }
                        const dOut=ymdToDate(dt), dRet=ymdToDate(ret);
                        if(!dRet || dRet < dOut){ statusEl.innerHTML='<span class="error">Return date cannot be earlier than outbound.</span>'; return; }
                    }
                    const isRound = (tripTypeSel?.value !== 'oneway');
                    runSearch(o,d,dt,(isRound? ret : undefined),tclass);
                });

                        if(swapBtn){ swapBtn.addEventListener('click', ()=>{ const o=originInput.value; originInput.value=destinationInput.value; destinationInput.value=o; originInput.focus(); }); }
                        if(clearBtn){ clearBtn.addEventListener('click', ()=>{ originInput.value=''; destinationInput.value=''; dateInput.value=''; returnDateInput.value=''; statusEl.className='meta'; statusEl.textContent='Enter origin, destination and date (YYYY-MM-DD).'; resEl.innerHTML=''; countEl.textContent=''; pager.style.display='none'; updateUrl('', '', '', '', '', ''); }); }

                        // Per-result toggle button (inside each item)
                        resEl.addEventListener('click', (e)=>{
                            const t=e.target;
                            if(t && t.classList && t.classList.contains('toggleLink')){
                                e.preventDefault();
                                const details = t.closest('details.result');
                                if(details){ details.open = !details.open; }
                            }
                        });

                        // Keyboard navigation for results
                        function isTypingTarget(t){ const tag=(t?.tagName||'').toUpperCase(); return tag==='INPUT' || tag==='TEXTAREA' || tag==='SELECT'; }
                        function resultList(){ return Array.from(resEl.querySelectorAll('details.result')); }
                        function focusResultAt(i){ const list=resultList(); if(!list.length) return; const idx=Math.max(0, Math.min(i, list.length-1)); const sum=list[idx].querySelector('summary'); if(sum){ sum.focus(); } }
                        function currentResultIndex(){ const ae=document.activeElement; if(!ae) return -1; const sum=ae.closest ? ae.closest('details.result summary') : null; const det= sum ? sum.parentElement : (ae.closest ? ae.closest('details.result') : null); if(!det) return -1; const list=resultList(); return list.indexOf(det); }
                        document.addEventListener('keydown', (e)=>{
                            if(isTypingTarget(e.target)) return;
                            const list = resultList(); if(!list.length) return;
                            if(e.key==='ArrowDown'){
                                e.preventDefault(); const cur=currentResultIndex(); focusResultAt(cur<0?0:cur+1);
                            } else if(e.key==='ArrowUp'){
                                e.preventDefault(); const cur=currentResultIndex(); focusResultAt(cur<=0?0:cur-1);
                            } else if(e.key==='Enter' || e.key===' '){
                                const cur=currentResultIndex(); if(cur>=0){ e.preventDefault(); const det=resultList()[cur]; det.open = !det.open; }
                            }
                        });

                        loadInitial();
            </script>
        </body></html>""")

# Duplicate page under a new route with identical functionality/content, independent copy.
@app.get("/flight-search-V2", response_class=HTMLResponse, tags=["ui"])
async def flight_search_ui_v2(request: Request):  # Independent HTML copy
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
            .headline{color:var(--accent);font-size:1.35rem;font-weight:700;margin:.8rem 0;text-align:left}
            .filters{display:flex;gap:10px;align-items:center;margin:.5rem 0 1rem 0;border-bottom:1px solid #eceff3;padding-bottom:.6rem}
                .filters select{border:1px solid #dadce0;border-radius:8px;padding:.35rem .5rem}
            .filters .btn{border:1px solid #dadce0;background:#fff;border-radius:6px;padding:.35rem .6rem;cursor:pointer;font-size:.85rem}
            .tabs{display:flex;gap:8px;border-bottom:1px solid #eceff3;margin:.25rem 0 1rem 0}
            .tab{border:1px solid #dadce0;background:#fff;border-radius:6px 6px 0 0;padding:.35rem .7rem;cursor:pointer;font-size:.85rem}
            .tab.active{background:#e8f0fe;border-bottom-color:#e8f0fe;color:#174ea6}
            details.result{padding:10px 0;border-bottom:1px solid #f1f3f4}
            details.result > summary{list-style:none;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;cursor:pointer}
            details.result > summary::-webkit-details-marker{display:none}
            .result .left{flex:1;min-width:0}
            .result .title{font-size:1.1rem;color:var(--accent);margin:0 0 .2rem 0}
            .crumbs{color:#5f6368;font-size:.85rem;margin-bottom:.25rem}
                .chips{margin-top:.35rem}
                .chip{display:inline-block;background:var(--chip);color:#174ea6;border:1px solid #d2e3fc;padding:.1rem .5rem;border-radius:999px;font-size:.7rem;margin-right:.25rem}
            /* Two-column leg route with per-airport times */
            .leg-route.two-col{display:flex;align-items:flex-start;gap:10px;justify-content:space-between}
            .leg-route.two-col .loc{flex:1;min-width:0}
            .leg-route.two-col .name{font-weight:600;color:#111827}
            .leg-route.two-col .sub{color:var(--muted);font-size:.85rem;margin-top:2px}
            .leg-route.two-col .arrow{color:#6b7280;padding:0 4px;align-self:center}
                .right{width:160px;text-align:right}
                .price{color:var(--ok);font-weight:700;font-size:1.2rem}
                .side{color:#5f6368;font-size:.8rem}
            .segments{margin-top:.6rem;border-left:3px solid #e8eaed;padding-left:10px}
            .seg{color:#3c4043;font-size:.9rem;line-height:1.35rem;margin:.2rem 0}
            .detailsHint{color:#5f6368;font-size:.8rem;margin-top:.2rem}
            .rowActions{margin-top:.3rem}
            .toggleLink{border:1px solid #dadce0;background:#fff;border-radius:4px;padding:.2rem .45rem;cursor:pointer;font-size:.8rem;color:#1a73e8}
            .itinerary{display:flex;flex-direction:column;gap:.6rem;margin:.6rem 0}
            .leg{display:flex;gap:10px}
            .leg .dot{width:10px}
            .dot::before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;background:#5f6368;position:relative;top:6px}
            .leg-main{flex:1}
            .leg-times{font-weight:600;color:#202124}
            .leg-route{color:#5f6368;font-size:.9rem}
            .leg-meta{color:#5f6368;font-size:.85rem;margin-top:.2rem}
            .layover{padding:.45rem .6rem;background:#f8f9fa;border:1px dashed #e0e3e7;border-radius:6px;color:#5f6368;font-size:.85rem}
            .layover.warn{border-color:#f59e0b;background:#fff7ed}
                .pagination{display:flex;justify-content:center;gap:10px;margin:18px 0}
                .pagination button{border:1px solid #dadce0;background:#fff;border-radius:6px;padding:.4rem .7rem;cursor:pointer}
                .back{color:#5f6368;text-decoration:none;font-size:.85rem;margin-left:8px}
                .error{color:#b91c1c}
            </style>
        </head>
        <body>
            <header>
                <div class='topbar'>
                    <div class='logo'>SerpFlights <span class='pill v2'>V2</span></div>
                    <form id='fsForm' class='search'>
                        <input id='origin_code' placeholder='Origin: code, city, or name' maxlength='32' list='originList' required />
                        <input id='destination' placeholder='Destination: code, city, or name' maxlength='32' list='destList' required />
                        <input id='date' type='date' required />
                        <input id='return_date' type='date' placeholder='Return (optional)' />
                        <select id='trip_type' title='Trip type'>
                            <option value='round' selected>2-way (Round trip)</option>
                            <option value='oneway'>1-way</option>
                        </select>
                        <select id='travel_class' title='Travel class'>
                            <option value='1' selected>Economy</option>
                            <option value='2'>Premium</option>
                            <option value='3'>Business</option>
                            <option value='4'>First</option>
                        </select>
                        <button type='submit' id='searchBtn'>Search</button>
                        <button type='button' id='swapBtn' class='util' title='Swap origin/destination'>Swap</button>
                        <button type='button' id='clearBtn' class='util' title='Clear form'>Clear</button>
                    </form>
                    <datalist id='originList'></datalist>
                    <datalist id='destList'></datalist>
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
                <div class='tabs'>
                    <button id='tabOutbound' class='tab active'>Outbound</button>
                    <button id='tabInbound' class='tab'>Inbound</button>
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
                const returnDateInput=document.getElementById('return_date');
                const tripTypeSel=document.getElementById('trip_type');
                const classSelect=document.getElementById('travel_class');
                const sortSel=document.getElementById('sort');
                const searchBtn=document.getElementById('searchBtn');
            const countEl=document.getElementById('count');
            const swapBtn=document.getElementById('swapBtn');
            const clearBtn=document.getElementById('clearBtn');
            const expandAllBtn=document.getElementById('expandAll');
            const collapseAllBtn=document.getElementById('collapseAll');
                const pager=document.getElementById('pager');
                const prevBtn=document.getElementById('prevBtn');
                const nextBtn=document.getElementById('nextBtn');
                const pageInfo=document.getElementById('pageInfo');
                const tabOut=document.getElementById('tabOutbound');
                const tabIn=document.getElementById('tabInbound');

                function setBusy(b){
                    [originInput,destinationInput,dateInput,returnDateInput,tripTypeSel,classSelect,sortSel,searchBtn,swapBtn,clearBtn].forEach(el=>{ if(el){ el.disabled=!!b; }});
                    if(searchBtn){ searchBtn.textContent = b? 'Searching…' : 'Search'; }
                }

                const PAGE_SIZE=10; let ALL=[], OUT=[], IN=[], META={source:''}; let page=1; let AIRPORTS = Object.create(null); let CURRENT_DT=''; let CURRENT_RET_DT=''; let CURRENT_ORIG=''; let CURRENT_DEST=''; let currentView='outbound';
                function today(){ const d=new Date(); const m=('0'+(d.getMonth()+1)).slice(-2); const day=('0'+d.getDate()).slice(-2); return `${d.getFullYear()}-${m}-${day}`; }
                dateInput.value=today();
                function ymdToDate(ymd){ if(!ymd) return null; try{ const d=new Date(String(ymd).trim()+"T00:00:00"); return isNaN(d.getTime())? null : d; }catch{return null} }
                function dateToYmd(d){ const m=('0'+(d.getMonth()+1)).slice(-2); const day=('0'+d.getDate()).slice(-2); return `${d.getFullYear()}-${m}-${day}`; }
                function addDaysYmd(ymd, n){ const d=ymdToDate(ymd); if(!d) return ''; d.setDate(d.getDate()+Number(n||0)); return dateToYmd(d); }
                function syncReturnMin(){
                    const out=dateInput.value;
                    if(out){
                        const min = addDaysYmd(out, 1);
                        if(min){ returnDateInput.min = min; }
                        // Clear invalid return if <= outbound
                        if(returnDateInput.value && returnDateInput.value <= out){ returnDateInput.value=''; }
                    } else {
                        returnDateInput.removeAttribute('min');
                    }
                }
                // Initialize and bind
                syncReturnMin();
                dateInput.addEventListener('change', syncReturnMin);

                function authFetch(url){ const t=localStorage.getItem('access_token'); if(!t){window.location='/'; throw new Error('Not authenticated');} return fetch(url,{headers:{'Authorization':'Bearer '+t}}); }
                // Trip type behavior: disable/clear return date when 1-way
                if(tripTypeSel){
                    const syncTripUi=()=>{
                        const isOneWay = tripTypeSel.value === 'oneway';
                        returnDateInput.disabled = isOneWay;
                        if(isOneWay){ returnDateInput.value=''; }
                        syncReturnMin();
                    };
                    tripTypeSel.addEventListener('change', syncTripUi);
                    syncTripUi();
                }
                // --- Autosuggest for airports ---
                async function fetchAirports(q){
                    if(!q||q.length<2) return [];
                    try{
                        const r = await authFetch(`/api/airports/suggest?q=${encodeURIComponent(q)}`);
                        if(!r.ok) return [];
                        const data = await r.json();
                        return Array.isArray(data)? data : [];
                    }catch{return []}
                }
                function populateDatalist(listId, items){
                    const dl = document.getElementById(listId);
                    if(!dl) return;
                    dl.innerHTML = items.slice(0,10).map(it=>{
                        const label = `${it.code} — ${it.name}${it.city?` (${it.city})`:''}${it.country?`, ${it.country}`:''}`;
                        const val = it.code;
                        return `<option value="${val}" label="${label}"></option>`;
                    }).join('');
                }
                function attachSuggest(inputEl, listId){
                    let last=''; let timer=null;
                    inputEl.addEventListener('input', ()=>{
                        const v=inputEl.value.trim();
                        if(v===last) return; last=v;
                        clearTimeout(timer);
                        timer=setTimeout(async()=>{
                            const items = await fetchAirports(v);
                            populateDatalist(listId, items);
                        }, 200);
                    });
                }
                attachSuggest(originInput,'originList');
                attachSuggest(destinationInput,'destList');

                function fmtDuration(mins){ if(mins==null||isNaN(mins)) return ''; const h=Math.floor(mins/60), m=mins%60; return `${h} hr ${m} min`; }
        function parseTs(ts){
                    if(!ts) return null;
                    if(typeof ts === 'number') return new Date(ts);
                    if(typeof ts === 'string'){
                        let s = ts.trim();
                        // If ISO-like, trust it
            if(/^[0-9]{4}-[0-9]{2}-[0-9]{2}T/.test(s)){
                            const d = new Date(s); if(!isNaN(d.getTime())) return d;
                        }
                        // Handle "YYYY-MM-DD HH:MM[:SS] [AM|PM]" -> build ISO local
            const m = s.match(/^([0-9]{4}-[0-9]{2}-[0-9]{2})[ T]([0-9]{1,2}):([0-9]{2})(?::([0-9]{2}))? *(AM|PM)?$/i);
                        if(m){
                            const date = m[1]; let hh = parseInt(m[2],10); const mm = m[3]; const ss = m[4]||'00'; const ap=m[5];
                            if(ap){ const isPM=/pm/i.test(ap); if(hh===12){ hh=isPM?12:0; } else { hh = isPM? hh+12 : hh; } }
                            const hh2 = ('0'+hh).slice(-2);
                            const d = new Date(`${date}T${hh2}:${mm}:${ss}`);
                            if(!isNaN(d.getTime())) return d;
                        }
                        // Fallback: try replacing single space between date and time with T
            if(/^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}/.test(s)){
                            const d = new Date(s.replace(' ', 'T'));
                            if(!isNaN(d.getTime())) return d;
                        }
                        const d2 = new Date(s);
                        if(!isNaN(d2.getTime())) return d2;
                    }
                    try { const d=new Date(ts); return isNaN(d.getTime())? null : d; } catch { return null; }
                }
                function toDate(ts){ return parseTs(ts); }
                function fmtTime(ts){ const d=toDate(ts); if(!d) return ''; return d.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'}); }
        function inferHM(ts){ if(!ts) return ''; const s=String(ts); const m=s.match(/([0-9]{1,2}:[0-9]{2}(?:[ ]*[AP]M)?)/i); return m? m[1] : ''; }
                function dateShort(ts){ const d=toDate(ts); if(!d) return ''; return d.toLocaleDateString([], {month:'short', day:'2-digit'}); }
                function dateShortYMD(ymd){ if(!ymd) return ''; try{ const d=new Date(String(ymd).trim()+"T00:00:00"); if(!isNaN(d.getTime())){ return d.toLocaleDateString([], {month:'short', day:'2-digit'}); } }catch{} return ''; }
                function dayDiff(a,b){ const da=toDate(a), db=toDate(b); if(!da||!db) return 0; const ad=new Date(da.getFullYear(),da.getMonth(),da.getDate()); const bd=new Date(db.getFullYear(),db.getMonth(),db.getDate()); return Math.round((bd-ad)/86400000); }
                function minutesBetween(a,b){ const da=toDate(a), db=toDate(b); if(!da||!db) return null; return Math.max(0, Math.round((db-da)/60000)); }
                function timePart(ts){ const d=toDate(ts); if(!d) return ''; return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}); }
                function cityOrName(code){ const a=AIRPORTS && AIRPORTS[code]; return (a?.city || a?.name || code || ''); }
                function nameOf(code){ const a=AIRPORTS && AIRPORTS[code]; return (a?.name || ''); }
                function buildRoute(f){ const segs=f.flights||[]; if(!segs.length) return 'Flight'; const a=(segs[0].departure_airport?.id||'').toUpperCase(); const b=(segs[segs.length-1].arrival_airport?.id||'').toUpperCase(); const la=`${cityOrName(a)} (${a})`; const lb=`${cityOrName(b)} (${b})`; return `${la} → ${lb}`; }
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
                            depTS: first.departure_time||'',
                            arrTS: last.arrival_time||'',
                            layovers: Array.isArray(f.layovers) ? f.layovers : [],
                            firstDep: (first?.departure_airport?.id||'').toUpperCase(),
                            lastArr: (last?.arrival_airport?.id||'').toUpperCase(),
                        };
                    });
                }
                function directionOf(x){
                    const a=(x.firstDep||'').toUpperCase();
                    const b=(x.lastArr||'').toUpperCase();
                    if(a && b){
                        if (a===CURRENT_ORIG && b===CURRENT_DEST) return 'outbound';
                        if (a===CURRENT_DEST && b===CURRENT_ORIG) return 'inbound';
                    }
                    return 'other';
                }
                function recomputeBuckets(){
                    OUT = []; IN = [];
                    for(const x of ALL){
                        const dir = directionOf(x);
                        if(dir==='outbound') OUT.push(x);
                        else if(dir==='inbound') IN.push(x);
                    }
                    if(tabOut) tabOut.textContent = `Outbound (${OUT.length})`;
                    if(tabIn) tabIn.textContent = `Inbound (${IN.length})`;
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
                    const baseList = currentView==='inbound' ? IN : OUT;
                    const sorted=applySort(baseList);
                    const total=sorted.length; const totalPages=Math.max(1, Math.ceil(total/PAGE_SIZE));
                    page=Math.min(Math.max(1,page), totalPages);
                    const start=(page-1)*PAGE_SIZE; const slice=sorted.slice(start, start+PAGE_SIZE);
                                countEl.textContent = total ? `About ${total} ${currentView} results — Source: ${META.source}` : '';
                    pager.style.display = total>PAGE_SIZE ? 'flex' : 'none';
                    prevBtn.disabled = page<=1; nextBtn.disabled = page>=totalPages; pageInfo.textContent = `Page ${page} of ${totalPages}`;
                                resEl.innerHTML = slice.map((x,idx)=>{
                                    const chips = [x.airlines && `<span class='chip'>${x.airlines}</span>`, x.stops===0 && `<span class='chip'>Nonstop</span>`].filter(Boolean).join('');
                                                const legs = (x.raw.flights||[]);
                                                const parts = [];
                                                for(let i=0;i<legs.length;i++){
                                                    const s=legs[i];
                                                    const depA=(s.departure_airport?.id||'').toUpperCase(); const arrA=(s.arrival_airport?.id||'').toUpperCase();
                                                    const dt=fmtTime(s.departure_time||''); const at=fmtTime(s.arrival_time||'');
                                                    const dd=dayDiff(s.departure_time, s.arrival_time); const plusDay = dd>0? ` + ${dd} day${dd>1?'s':''}`:'';
                                                    const durMin = (s.duration? Number(s.duration): null);
                                                    const durStr = durMin? fmtDuration(durMin) : '';
                                                    const al=s.airline||''; const fn=s.flight_number||'';
                                                    const depCity = cityOrName(depA); const arrCity = cityOrName(arrA);
                                                    const depHM = inferHM(s.departure_time)||fmtTime(s.departure_time)||'';
                                                    const arrHM = inferHM(s.arrival_time)||fmtTime(s.arrival_time)||'';
                                                    parts.push(`
                                                        <div class='leg'>
                                                            <div class='dot'></div>
                                                            <div class='leg-main'>
                                                                <div class='leg-route two-col'>
                                                                    <div class='loc'>
                                                                        <div class='name'>${depCity} (${depA})</div>
                                                                        <div class='sub time'>${depHM}</div>
                                                                    </div>
                                                                    <div class='arrow'>→</div>
                                                                    <div class='loc'>
                                                                        <div class='name'>${arrCity} (${arrA})</div>
                                                                        <div class='sub time'>${arrHM}${plusDay}</div>
                                                                    </div>
                                                                </div>
                                                                <div class='leg-meta'>${[al && al, fn && ('• '+fn), durStr && ('• '+durStr)].filter(Boolean).join(' ')}</div>
                                                            </div>
                                                        </div>
                                                    `);
                                                    // Render provided layovers if present at matching index
                                                    if(i < x.layovers.length){
                                                        const lay = x.layovers[i];
                                                        const code = (lay?.id || '').toUpperCase();
                                                        const mins = Number(lay?.duration) || 0;
                                                        const overnight = !!lay?.overnight;
                                                        const label = `${fmtDuration(mins)} layover • ${cityOrName(code)} (${code})`;
                                                        parts.push(`<div class='layover ${overnight?'warn':''}'>${label}${overnight?' • Overnight layover ⚠️':''}</div>`);
                                                    }
                                                }
                                                const segsFull = `<div class='itinerary'>${parts.join('')}</div>`;
                                                const first=legs[0]||{}; const last=legs[legs.length-1]||{};
                                                // Prefer raw strings when provided (avoid relying on parsing)
                                                const depTimeStr = inferHM(first.departure_time) || fmtTime(first.departure_time) || (x.dep||'');
                                                const arrTimeStr = inferHM(last.arrival_time) || fmtTime(last.arrival_time) || (x.arr||'');
                                                const depDateStr = dateShort(first.departure_time) || (CURRENT_DT ? dateShortYMD(CURRENT_DT) : '');
                                                const arrDateStr = dateShort(last.arrival_time) || (CURRENT_DT ? dateShortYMD(CURRENT_DT) : '');
                                                const crumbTimes = `${depTimeStr || ''} (${depDateStr})${(depTimeStr||arrTimeStr)?' → ':''}${arrTimeStr || ''} (${arrDateStr})`;
                                    return `
                                        <details class='result' data-relidx='${start+idx}'>
                                            <summary>
                                                <div class='left'>
                                                    <h3 class='title'>${x.route}</h3>
                                                    <div class='crumbs'>${fmtDuration(x.duration) || '—'} • ${x.stops} stop${x.stops===1?'':'s'} • ${crumbTimes}</div>
                                                    <div class='chips'>${chips}</div>
                                                    <div class='rowActions'>
                                                        <button type='button' class='toggleLink' data-role='toggle'>Show details</button>
                                                    </div>
                                                </div>
                                                <div class='right'>
                                                    <div class='price'>${priceStr(x.price)}</div>
                                                    <div class='side'>${META.source||''}</div>
                                                </div>
                                            </summary>
                                            <div class='segments'>${segsFull || '<div class="seg">No segment details.</div>'}</div>
                                        </details>`;
                                }).join('');
                                // Make summaries keyboard-focusable and sync toggle button text
                                const detailsList = Array.from(resEl.querySelectorAll('details.result'));
                                detailsList.forEach(d=>{
                                    const sum=d.querySelector('summary'); if(sum) sum.tabIndex=0;
                                    const btn=d.querySelector('.toggleLink');
                                    const setText=()=>{ if(btn) btn.textContent = d.open ? 'Hide details' : 'Show details'; };
                                    setText(); d.addEventListener('toggle', setText);
                                });
                }

                prevBtn.onclick=()=>{ page=Math.max(1,page-1); render(); }
                nextBtn.onclick=()=>{ page=page+1; render(); }
                sortSel.onchange=()=>{ page=1; render(); }
                if(tabOut){ tabOut.onclick=()=>{ currentView='outbound'; tabOut.classList.add('active'); if(tabIn) tabIn.classList.remove('active'); page=1; render(); }; }
                if(tabIn){ tabIn.onclick=()=>{ currentView='inbound'; tabIn.classList.add('active'); if(tabOut) tabOut.classList.remove('active'); page=1; render(); }; }

                async function runSearch(o,d,dt,ret,tclass){
                    statusEl.className='meta';
                    statusEl.textContent='Searching...'; resEl.innerHTML=''; countEl.textContent=''; pager.style.display='none';
                    setBusy(true);
                    CURRENT_DT = dt || '';
                    CURRENT_RET_DT = ret || '';
                    CURRENT_ORIG = (o||'').toUpperCase();
                    CURRENT_DEST = (d||'').toUpperCase();
                    const tc = (tclass && Number(tclass)) ? Number(tclass) : (Number(classSelect?.value)||1);
                    const isRoundUI = (tripTypeSel?.value !== 'oneway');

                    // Always 1-way outbound
                    const urlOut = `/api/flight_search?origin=${encodeURIComponent(o)}&destination=${encodeURIComponent(d)}&date=${encodeURIComponent(dt)}&travel_class=${tc}&one_way=1`;
                    const r=await authFetch(urlOut);
                    if(!r.ok){ const txt=await r.text(); statusEl.innerHTML='<span class="error">Error: '+txt+'</span>'; setBusy(false); return; }
                    const data=await r.json();
                    if(!data.success){ statusEl.innerHTML='<span class="error">No results: '+(data.error||'unknown')+'</span>'; setBusy(false); return; }
                    const flightsOut=(data.data?.best_flights||[]).concat(data.data?.other_flights||[]);
                    META.source = data.source || '';

                    // Optionally run reverse one-way if 2-way selected and return date provided
                    let flightsIn = [];
                    if(isRoundUI){
                        if(!ret){
                            statusEl.innerHTML = '<span class="error">Return date is required for 2-way; it will be used for the inbound search.</span>';
                            setBusy(false);
                            return;
                        }
                        const urlIn = `/api/flight_search?origin=${encodeURIComponent(d)}&destination=${encodeURIComponent(o)}&date=${encodeURIComponent(ret)}&travel_class=${tc}&one_way=1`;
                        try{
                            const r2 = await authFetch(urlIn);
                            if(r2.ok){
                                const data2 = await r2.json();
                                if(data2 && data2.success){
                                    flightsIn = (data2.data?.best_flights||[]).concat(data2.data?.other_flights||[]);
                                } else {
                                    statusEl.innerHTML = 'Inbound search returned no results.';
                                }
                            } else {
                                statusEl.innerHTML = 'Inbound search failed.';
                            }
                        }catch{ statusEl.innerHTML = 'Inbound search failed.'; }
                    }

                    const flightsAll = flightsOut.concat(flightsIn);
                    if(!flightsAll.length){ statusEl.className='meta'; statusEl.textContent='No results.'; resEl.innerHTML=''; setBusy(false); return; }

                    // Build list of unique airport codes and fetch airport details in batch
                    const setCodes = new Set([o.toUpperCase(), d.toUpperCase()]);
                    for(const f of flightsAll){
                        for(const s of (f.flights||[])){
                            const a=(s?.departure_airport?.id||'').toUpperCase();
                            const b=(s?.arrival_airport?.id||'').toUpperCase();
                            if(a) setCodes.add(a); if(b) setCodes.add(b);
                        }
                        for(const lay of (f.layovers||[])){
                            const c=(lay?.id||'').toUpperCase(); if(c) setCodes.add(c);
                        }
                    }
                    try{
                        const list = Array.from(setCodes).join(',');
                        const rr = await authFetch(`/api/airports/by_codes?codes=${encodeURIComponent(list)}`);
                        if(rr.ok){ const arr = await rr.json(); const map = Object.create(null); (arr||[]).forEach(it=>{ if(it && it.code){ map[(it.code||'').toUpperCase()] = it; } }); AIRPORTS = map; }
                    }catch{}

                    // Resolve friendly names for origin/destination for a larger heading
                    async function fetchAirport(code){
                        try{
                            const rr = await authFetch(`/api/airports/by_code?code=${encodeURIComponent(code)}`);
                            if(!rr.ok) return null;
                            return await rr.json();
                        }catch{return null}
                    }
                    const [ao, ad] = await Promise.all([fetchAirport(o), fetchAirport(d)]);
                    const oLabel = `${(ao?.city||ao?.name||o)} (${o})`;
                    const dLabel = `${(ad?.city||ad?.name||d)} (${d})`;
                    statusEl.className='headline';
                    const CLASS_MAP = {1:'Economy', 2:'Premium', 3:'Business', 4:'First'};
                    const classLabel = CLASS_MAP[tc] || '';
                    const datesLine = isRoundUI ? (`on ${dt} • return ${ret}`) : (`on ${dt}`);
                    const modeStr = isRoundUI ? '2-way' : '1-way';
                    const suffix = [classLabel, modeStr].filter(Boolean).join(' • ');
                    statusEl.innerHTML = `<div>${oLabel} to ${dLabel}</div><div>${datesLine}</div>${suffix?`<div>${suffix}</div>`:''}`;
                    ALL = normalize(flightsAll);
                    recomputeBuckets();
                    if(OUT.length>0){ currentView='outbound'; if(tabOut){ tabOut.classList.add('active'); } if(tabIn){ tabIn.classList.remove('active'); } }
                    else { currentView='inbound'; if(tabIn){ tabIn.classList.add('active'); } if(tabOut){ tabOut.classList.remove('active'); } }
                    page=1; render();
                    setBusy(false);
                }

                        f.addEventListener('submit', (e)=>{
                    e.preventDefault();
                    const o=(originInput.value||'').trim().toUpperCase();
                    const d=(destinationInput.value||'').trim().toUpperCase();
                    const dt=dateInput.value;
                    const ret=(returnDateInput.value||'').trim();
                    const tclass=(classSelect?.value)||'1';
                    if(!o||!d||!dt){ statusEl.innerHTML='<span class="error">All fields are required.</span>'; return; }
                    const isRound = (tripTypeSel?.value !== 'oneway');
                    if(isRound && !ret){ statusEl.innerHTML='<span class="error">Return date is required for 2-way; it will be used for the inbound search.</span>'; return; }
                    runSearch(o,d,dt,(isRound? ret : undefined),tclass);
                });
                        if(swapBtn){ swapBtn.addEventListener('click', ()=>{ const o=originInput.value; originInput.value=destinationInput.value; destinationInput.value=o; originInput.focus(); }); }
                        if(clearBtn){ clearBtn.addEventListener('click', ()=>{ originInput.value=''; destinationInput.value=''; dateInput.value=''; returnDateInput.value=''; statusEl.className='meta'; statusEl.textContent='Enter origin, destination and date (YYYY-MM-DD).'; resEl.innerHTML=''; countEl.textContent=''; pager.style.display='none'; }); }

                        // Per-result toggle button (inside each item)
                        resEl.addEventListener('click', (e)=>{
                            const t=e.target;
                            if(t && t.classList && t.classList.contains('toggleLink')){
                                e.preventDefault();
                                const details = t.closest('details.result');
                                if(details){ details.open = !details.open; }
                            }
                        });

                        // Keyboard navigation for results
                        function isTypingTarget(t){ const tag=(t?.tagName||'').toUpperCase(); return tag==='INPUT' || tag==='TEXTAREA' || tag==='SELECT'; }
                        function resultList(){ return Array.from(resEl.querySelectorAll('details.result')); }
                        function focusResultAt(i){ const list=resultList(); if(!list.length) return; const idx=Math.max(0, Math.min(i, list.length-1)); const sum=list[idx].querySelector('summary'); if(sum){ sum.focus(); } }
                        function currentResultIndex(){ const ae=document.activeElement; if(!ae) return -1; const sum=ae.closest ? ae.closest('details.result summary') : null; const det= sum ? sum.parentElement : (ae.closest ? ae.closest('details.result') : null); if(!det) return -1; const list=resultList(); return list.indexOf(det); }
                        document.addEventListener('keydown', (e)=>{
                            if(isTypingTarget(e.target)) return;
                            const list = resultList(); if(!list.length) return;
                            if(e.key==='ArrowDown'){
                                e.preventDefault(); const cur=currentResultIndex(); focusResultAt(cur<0?0:cur+1);
                            } else if(e.key==='ArrowUp'){
                                e.preventDefault(); const cur=currentResultIndex(); focusResultAt(cur<=0?0:cur-1);
                            } else if(e.key==='Enter' || e.key===' '){
                                const cur=currentResultIndex(); if(cur>=0){ e.preventDefault(); const det=resultList()[cur]; det.open = !det.open; }
                            }
                        });
            </script>
        </body></html>""")

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
    sql = text(
        """
        SELECT airport_code AS code, airport_name AS name, country, country_code, city
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
