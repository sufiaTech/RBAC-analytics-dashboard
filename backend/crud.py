from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json

import models, schemas, auth


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    """
    Create a new user with a bcrypt-hashed password.

    bcrypt has a 72-byte limit for the *raw* password.
    If password is longer than that, passlib/bcrypt raises:
    ValueError: password cannot be longer than 72 bytes
    """
    # 1) Ensure password is a plain string
    raw_password = user.password
    if not isinstance(raw_password, str):
        # fail fast and loud (prevents hashing huge objects)
        raise ValueError(f"Password must be a string, got: {type(raw_password)}")

    raw_password = raw_password.strip()
    if not raw_password:
        raise ValueError("Password cannot be empty.")

    # 2) Enforce bcrypt's 72-byte rule (UTF-8 bytes)
    if len(raw_password.encode("utf-8")) > 72:
        raise ValueError(
            "Password is too long for bcrypt (max 72 bytes). "
            "Use a shorter password."
        )

    # 3) Prevent duplicates
    existing = get_user_by_username(db, user.username)
    if existing:
        return existing

    hashed_password = auth.get_password_hash(raw_password)

    db_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        role=user.role,
        department=user.department
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        if user_update.role is not None:
            db_user.role = user_update.role
        if user_update.department is not None:
            db_user.department = user_update.department
        db.commit()
        db.refresh(db_user)
    return db_user


def get_users(db: Session):
    return db.query(models.User).all()


def create_audit_log(db: Session, user_id: int, action: str, details: dict = None):
    """
    Store audit log details safely. If your models.AuditLog.details is a Text field,
    store JSON as a string.
    """
    if details is None:
        details = {}

    # ensure details is JSON-serializable
    try:
        details_json = json.dumps(details)
    except Exception:
        details_json = json.dumps({"note": "details not serializable"})

    db_log = models.AuditLog(
        user_id=user_id,
        action=action,
        details=details_json
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_audit_logs(db: Session):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).all()


def get_dashboard_kpis(
    db: Session,
    user: models.User,
    department: str = None,
    start_date: datetime = None,
    end_date: datetime = None
):
    query = db.query(
        models.DataRecord.metric_name,
        func.sum(models.DataRecord.value).label("total_value"),
        func.avg(models.DataRecord.value).label("average_value"),
        func.count(models.DataRecord.id).label("count")
    )

    # RBAC filtering
    if user.role != "admin":
        query = query.filter(models.DataRecord.department == user.department)
    elif department:
        query = query.filter(models.DataRecord.department == department)

    if start_date:
        query = query.filter(models.DataRecord.date >= start_date)
    if end_date:
        query = query.filter(models.DataRecord.date <= end_date)

    return query.group_by(models.DataRecord.metric_name).all()


def get_dashboard_table(
    db: Session,
    user: models.User,
    department: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 100,
    offset: int = 0
):
    query = db.query(models.DataRecord)

    # RBAC filtering
    if user.role != "admin":
        query = query.filter(models.DataRecord.department == user.department)
    elif department:
        query = query.filter(models.DataRecord.department == department)

    if start_date:
        query = query.filter(models.DataRecord.date >= start_date)
    if end_date:
        query = query.filter(models.DataRecord.date <= end_date)

    return (
        query.order_by(models.DataRecord.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_dashboard_chart(
    db: Session,
    user: models.User,
    metric: str,
    department: str = None,
    start_date: datetime = None,
    end_date: datetime = None
):
    query = db.query(models.DataRecord).filter(models.DataRecord.metric_name == metric)

    # RBAC filtering
    if user.role != "admin":
        query = query.filter(models.DataRecord.department == user.department)
    elif department:
        query = query.filter(models.DataRecord.department == department)

    if start_date:
        query = query.filter(models.DataRecord.date >= start_date)
    if end_date:
        query = query.filter(models.DataRecord.date <= end_date)

    return query.order_by(models.DataRecord.date.asc()).all()