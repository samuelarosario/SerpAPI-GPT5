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

@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}
