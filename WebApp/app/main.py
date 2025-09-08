from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pathlib

from WebApp.app.auth.routes import router as auth_router

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
    <meta charset='utf-8'/><style>body{font-family:system-ui;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#f0f6ff;margin:0;} .wrap{text-align:center;} h1{color:#134e9b;margin-bottom:.5rem;} p{color:#475569;font-size:.85rem;} button{margin-top:1rem;padding:.5rem .9rem;border:1px solid #134e9b;background:#fff;color:#134e9b;border-radius:6px;cursor:pointer;} button:hover{background:#134e9b;color:#fff;}</style></head>
    <body><div class='wrap'><h1 id='welcome'>Loading...</h1><p id='info'>Checking session.</p><button id='logout'>Logout</button></div>
    <script>
    async function init(){
        const t = localStorage.getItem('access_token');
        if(!t){ window.location='/'; return; }
        try {
            const res = await fetch('/auth/me',{headers:{'Authorization':'Bearer '+t}});
            if(!res.ok){ throw new Error('unauth'); }
            const user = await res.json();
            document.getElementById('welcome').textContent = 'Welcome, '+user.email;
            document.getElementById('info').textContent = 'User ID '+user.id;
        } catch(e){ localStorage.removeItem('access_token'); window.location='/'; }
    }
    document.getElementById('logout').addEventListener('click', ()=>{ localStorage.clear(); window.location='/'; });
    init();
    </script>
    </body></html>""")

@app.get("/admin", response_class=HTMLResponse, tags=["ui"])
async def admin_portal(request: Request):
    return HTMLResponse("""<!DOCTYPE html><html><head><title>Admin</title><meta charset='utf-8'/>
    <style>body{font-family:system-ui;margin:0;background:#f5f8fb;color:#0f2642;padding:2rem;}h1{margin-top:0;color:#134e9b;}table{border-collapse:collapse;width:100%;margin-top:1rem;}th,td{border:1px solid #d0d9e4;padding:.5rem .6rem;font-size:.8rem;}th{background:#e3eef9;text-align:left;}button{cursor:pointer;border:1px solid #134e9b;background:#fff;color:#134e9b;padding:.35rem .6rem;border-radius:4px;}button:hover{background:#134e9b;color:#fff;}#loginBox{max-width:320px;margin:4rem auto;background:#fff;border:1px solid #d0e2f0;border-radius:8px;padding:1rem 1.25rem;box-shadow:0 4px 20px -6px rgba(0,0,0,.08);}input{width:100%;padding:.5rem .6rem;margin:.4rem 0;border:1px solid #b8c9d9;border-radius:4px;}#notice{font-size:.7rem;color:#475569;margin-top:.5rem;}#err{color:#b91c1c;font-size:.75rem;margin-top:.25rem;}#ok{color:#047857;font-size:.75rem;margin-top:.25rem;} .pill{display:inline-block;padding:.15rem .5rem;border-radius:1rem;font-size:.6rem;background:#134e9b;color:#fff;margin-left:.35rem;} .inactive{background:#b91c1c !important;}</style></head>
    <body><div id='app'></div>
    <script>
    const app = document.getElementById('app');
    const LS_KEY='admin_api_key';
    function loginView(){
        app.innerHTML = `<div id="loginBox"><h1>Admin Login</h1><input id="k" placeholder="Admin API Key"/><button id="go">Enter</button><div id='err'></div><div id='notice'>Use configured admin API key.</div></div>`;
        document.getElementById('go').onclick=()=>{ localStorage.setItem(LS_KEY, document.getElementById('k').value.trim()); load(); };
    }
    async function fetchJSON(url, opts={}){ const key = localStorage.getItem(LS_KEY); opts.headers = Object.assign({'X-Admin-Key': key,'Content-Type':'application/json'}, opts.headers||{}); const r= await fetch(url, opts); if(!r.ok) throw new Error(await r.text()); try{return await r.json();}catch{return {};} }
    function render(users){
        let rows = users.map(u=>`<tr><td>${u.id}</td><td>${u.email}${u.is_admin?'<span class=\"pill\">ADMIN</span>':''}${u.is_active?'':'<span class=\"pill inactive\">INACTIVE</span>'}</td><td><button data-act='reset' data-id='${u.id}'>Reset PW</button> <button data-act='toggle' data-id='${u.id}'>Toggle Active</button></td></tr>`).join('');
        app.innerHTML = `<h1>User Management</h1><button id='logout'>Logout</button><table><thead><tr><th>ID</th><th>Email</th><th>Actions</th></tr></thead><tbody>${rows}</tbody></table><div id='ok'></div><div id='err'></div>`;
        document.getElementById('logout').onclick=()=>{ localStorage.removeItem(LS_KEY); loginView(); };
        app.querySelectorAll('button[data-act]').forEach(btn=>{ btn.onclick=async()=>{ const id=btn.getAttribute('data-id'); const act=btn.getAttribute('data-act'); try{ if(act==='reset'){ const np=prompt('New password for user '+id+':'); if(!np) return; await fetchJSON('/auth/users/'+id+'/password',{method:'POST',body:JSON.stringify({password:np})}); } else if(act==='toggle'){ await fetchJSON('/auth/users/'+id+'/toggle_active',{method:'POST'}); } loadUsers(); }catch(e){ showErr(e.message); } }; });
    }
    function showErr(m){ const e=document.getElementById('err'); if(e){ e.textContent=m; } }
    function showOk(m){ const e=document.getElementById('ok'); if(e){ e.textContent=m; } }
    async function loadUsers(){ try{ const users = await fetchJSON('/auth/users'); render(users); } catch(e){ showErr('Error: '+e.message); if(e.message.includes('Forbidden')){ loginView(); } } }
    function load(){ const key=localStorage.getItem(LS_KEY); if(!key){ loginView(); return; } loadUsers(); }
    load();
    </script></body></html>""")

@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}
