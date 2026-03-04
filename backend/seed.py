from sqlalchemy.orm import Session
from db import SessionLocal, engine, Base
import models  # IMPORTANT: ensures models are imported so tables register
import schemas
import crud

from datetime import date, timedelta
import random


def main():
    print("=== SEED START ===")
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db: Session = SessionLocal()

    # -------------------------
    # Create / Upsert Users
    # -------------------------
    users = [
        {"username": "admin", "password": "adminpassword", "role": "admin", "department": None},
        {"username": "manager_sales", "password": "managerpassword", "role": "manager", "department": "Sales"},
        {"username": "viewer_sales", "password": "viewerpassword", "role": "viewer", "department": "Sales"},
        {"username": "manager_it", "password": "managerpassword", "role": "manager", "department": "IT"},
    ]

    print("Inserting users...")
    for u in users:
        created = crud.create_user(db, schemas.UserCreate(**u))
        print(f"Upserted user: {created.username} | role={created.role} | dept={created.department}")

    # -------------------------
    # Insert Demo Data Records
    # -------------------------
    print("Inserting demo data records...")

    start_day = date.today() - timedelta(days=30)
    records_to_add = []

    for i in range(31):  # last 31 days
        d = start_day + timedelta(days=i)

        # Sales metrics
        records_to_add.append(
            models.DataRecord(date=d, department="Sales", metric_name="revenue", value=random.randint(5000, 20000))
        )
        records_to_add.append(
            models.DataRecord(date=d, department="Sales", metric_name="orders", value=random.randint(30, 140))
        )

        # IT metrics
        records_to_add.append(
            models.DataRecord(date=d, department="IT", metric_name="tickets", value=random.randint(5, 40))
        )
        records_to_add.append(
            models.DataRecord(date=d, department="IT", metric_name="uptime", value=random.randint(970, 999) / 10)
        )  # 97.0–99.9

    db.add_all(records_to_add)
    db.commit()

    print(f"Inserted {len(records_to_add)} data records.")

    # Confirm counts
    user_count = db.query(models.User).count()
    data_count = db.query(models.DataRecord).count()
    print("User count:", user_count)
    print("DataRecord count:", data_count)

    db.close()
    print("=== SEED DONE ===")


if __name__ == "__main__":
    main()