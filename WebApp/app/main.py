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

from jose import jwt, JWTError
from WebApp.app.core.config import settings

def get_current_user(token: str | None = None):
    # Token passed via query for simplicity in prototype; later use Authorization header
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = jwt.decode(token, settings.webapp_jwt_secret, algorithms=[settings.algorithm])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.get("/dashboard", response_class=HTMLResponse, tags=["ui"])
async def dashboard(request: Request, user_id: str = Depends(get_current_user)):
    return HTMLResponse(f"""<!DOCTYPE html><html><head><title>Dashboard</title>
    <meta charset='utf-8'/><style>body{{font-family:system-ui;display:flex;min-height:100vh;align-items:center;justify-content:center;background:#f0f6ff;margin:0;}} .wrap{{text-align:center;}} h1{{color:#134e9b;margin-bottom:.5rem;}} p{{color:#475569;font-size:.85rem;}}</style></head>
    <body><div class='wrap'><h1>Welcome, User {user_id}</h1><p>Blank page placeholder.</p></div></body></html>""")

@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}
