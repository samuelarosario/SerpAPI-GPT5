from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from WebApp.app.db.session import get_db, engine, Base, SessionLocal
import os
from WebApp.app.auth import models, schemas
from WebApp.app.auth.hash import hash_password, verify_password
from WebApp.app.core.config import settings
from WebApp.app.auth.jwt import create_access_token, create_refresh_token
from WebApp.app.core.auth_logging import log_auth, tail_auth_log

router = APIRouter(prefix="/auth", tags=["auth"])

# Ensure tables exist (simple approach for bootstrap). For in-memory tests, recreate each import.
from sqlalchemy import inspect, text

insp = inspect(engine)
with engine.begin() as conn:
    # If legacy table exists and new table does not, rename/migrate
    if "auth_users" in insp.get_table_names() and "User" not in insp.get_table_names():
        # Attempt rename (SQLite supports simple rename)
        conn.execute(text("ALTER TABLE auth_users RENAME TO User"))
    # Ensure new schema present
Base.metadata.create_all(bind=engine)

# Ensure a default demo user (user@local / password: user) exists for quick manual testing.
def _ensure_default_user():
    try:
        db = SessionLocal()
        from WebApp.app.auth.hash import hash_password
        from WebApp.app.auth import models
        for demo_email, pwd in [("user@local", "user"), ("user@example.com", "StrongPassw0rd!")]:
            exists = db.query(models.User).filter(models.User.email == demo_email).first()
            if not exists:
                demo = models.User(email=demo_email, password_hash=hash_password(pwd))
                db.add(demo)
        db.commit()
    except Exception:
        # Silent fail to avoid impacting startup
        pass
    finally:
        try:
            db.close()
        except Exception:
            pass

_ensure_default_user()

@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(data: schemas.UserCreate, db: Session = Depends(get_db)):
    log_auth("register_attempt", email=data.email)
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        log_auth("register_failure", email=data.email, success=False, detail="email_exists")
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(email=data.email, password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    log_auth("register_success", email=data.email, success=True)
    return user

@router.post("/login", response_model=schemas.TokenPair)
def login(data: schemas.UserLogin, db: Session = Depends(get_db)):
    log_auth("login_attempt", email=data.email)
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        log_auth("login_failure", email=data.email, success=False, detail="no_such_user")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(data.password, user.password_hash):
        log_auth("login_failure", email=data.email, success=False, detail="bad_password")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(str(user.id))
    refresh = create_refresh_token(str(user.id))
    log_auth("login_success", email=data.email, success=True)
    return schemas.TokenPair(access_token=access, refresh_token=refresh)

@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(token: str):
    try:
        payload = jwt.decode(token, settings.webapp_jwt_secret, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        sub = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return schemas.TokenPair(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub)
    )


@router.get("/me", response_model=schemas.UserRead)
def me(request: Request, db: Session = Depends(get_db)):
    # Expect Authorization: Bearer <token>
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(None,1)[1]
    try:
        payload = jwt.decode(token, settings.webapp_jwt_secret, algorithms=[settings.algorithm])
        sub = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == int(sub)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/logs")
def auth_logs(request: Request, lines: int = 50):
    api_key = request.headers.get("X-Admin-Key")
    if not api_key or api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    return tail_auth_log(lines)
