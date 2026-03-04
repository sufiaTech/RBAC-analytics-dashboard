import json
"""
Interactive Data Dashboard with Role-Based Access (RBAC) - Backend

RUN INSTRUCTIONS:
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

import db, models, schemas, auth, crud

# Initialize DB tables
models.Base.metadata.create_all(bind=db.engine)

app = FastAPI(title="RBAC Dashboard API")

# CORS Setup (Allowing Streamlit default port 8501 and localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Helpers
# -------------------------
def get_admin_user(user: models.User = Depends(auth.get_current_user)) -> models.User:
    auth.require_admin(user)
    return user


class AuditEventIn(BaseModel):
    action: str
    details: Optional[Dict[str, Any]] = None


# -------------------------
# Authentication Endpoints
# -------------------------
@app.post("/auth/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, session: Session = Depends(db.get_db)):
    db_user = crud.get_user_by_username(session, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    created = crud.create_user(session, user)

    # Audit Log
    crud.create_audit_log(
        session,
        user_id=created.id,
        action="REGISTER",
        details={"username": created.username, "role": created.role, "department": created.department},
    )

    return created


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(db.get_db),
):
    user = crud.get_user_by_username(session, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        # Optional audit log for failed login
        crud.create_audit_log(
            session,
            user_id=user.id if user else 0,
            action="LOGIN_FAILED",
            details={"username": form_data.username},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.username})

    # Audit Log
    crud.create_audit_log(
        session,
        user_id=user.id,
        action="LOGIN_SUCCESS",
        details={"username": user.username, "role": user.role, "department": user.department},
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=schemas.UserOut)
def get_me(user: models.User = Depends(auth.get_current_user)):
    return user


# -------------------------
# Dashboard Endpoints
# -------------------------
@app.get("/dashboard/kpis", response_model=List[schemas.KPIOut])
def get_kpis(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    department: Optional[str] = None,
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    # Audit
    crud.create_audit_log(
        session,
        user_id=user.id,
        action="VIEW_KPIS",
        details={"start_date": str(start_date), "end_date": str(end_date), "department": department},
    )
    return crud.get_dashboard_kpis(session, user, department, start_date, end_date)


@app.get("/dashboard/chart", response_model=List[schemas.DataRecordOut])
def get_chart(
    metric: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    department: Optional[str] = None,
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    # Audit
    crud.create_audit_log(
        session,
        user_id=user.id,
        action="VIEW_CHART",
        details={"metric": metric, "start_date": str(start_date), "end_date": str(end_date), "department": department},
    )
    return crud.get_dashboard_chart(session, user, metric, department, start_date, end_date)


@app.get("/dashboard/table", response_model=List[schemas.DataRecordOut])
def get_table(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    department: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    # Audit
    crud.create_audit_log(
        session,
        user_id=user.id,
        action="VIEW_TABLE",
        details={
            "start_date": str(start_date),
            "end_date": str(end_date),
            "department": department,
            "limit": limit,
            "offset": offset,
        },
    )
    return crud.get_dashboard_table(session, user, department, start_date, end_date, limit, offset)


# -------------------------
# Admin Endpoints
# -------------------------
@app.get("/admin/users", response_model=List[schemas.UserOut])
def get_all_users(admin: models.User = Depends(get_admin_user), session: Session = Depends(db.get_db)):
    # Audit
    crud.create_audit_log(session, user_id=admin.id, action="VIEW_USERS", details={})
    return crud.get_users(session)


@app.patch("/admin/users/{user_id}", response_model=schemas.UserOut)
def update_user_role(
    user_id: int,
    user_update: schemas.UserUpdate,
    admin: models.User = Depends(get_admin_user),
    session: Session = Depends(db.get_db),
):
    user = crud.update_user(session, user_id, user_update)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Audit Log
    crud.create_audit_log(
        session,
        user_id=admin.id,
        action="ROLE_CHANGE",
        details={"target_user_id": user_id, "changes": user_update.model_dump()},
    )

    return user


# Step 4 (B1): Admin can read audit logs
@app.get("/admin/audit-logs", response_model=List[schemas.AuditLogOut])
def admin_audit_logs(admin: models.User = Depends(get_admin_user), session: Session = Depends(db.get_db)):
    logs = crud.get_audit_logs(session)

    # Optional: pretty print JSON stored in details
    for log in logs:
        if log.details:
            try:
                log.details = json.dumps(json.loads(log.details), indent=2)
            except Exception:
                pass

    return logs


# Backward compatible route (you had /audit)
@app.get("/audit", response_model=List[schemas.AuditLogOut])
def get_audit(admin: models.User = Depends(get_admin_user), session: Session = Depends(db.get_db)):
    return crud.get_audit_logs(session)


# Generic audit event endpoint (e.g., EXPORT_CSV)
@app.post("/audit/event")
def log_event(
    event: AuditEventIn,
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    # Restrict export log to managers/admins if needed
    if event.action == "EXPORT_CSV" and user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot export data")

    crud.create_audit_log(session, user_id=user.id, action=event.action, details=event.details or {})
    return {"status": "success"}