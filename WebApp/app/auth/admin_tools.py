from sqlalchemy.orm import Session
from WebApp.app.db.session import SessionLocal
from WebApp.app.auth import models
from WebApp.app.auth.hash import hash_password


def list_users() -> list[tuple[int,str,bool]]:
    db: Session = SessionLocal()
    try:
        rows = db.query(models.User.id, models.User.email, models.User.is_active).all()
        return [(r.id, r.email, r.is_active) for r in rows]
    finally:
        db.close()


def set_password(email: str, new_password: str) -> bool:
    db: Session = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            return False
        user.password_hash = hash_password(new_password)
        db.add(user)
        db.commit()
        return True
    finally:
        db.close()
