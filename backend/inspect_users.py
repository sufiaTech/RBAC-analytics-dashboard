from db import SessionLocal
from models import User
from auth import verify_password

db = SessionLocal()
users = db.query(User).all()

print("Users in DB:", len(users))
for u in users:
    print("-", u.username, "| role:", u.role, "| dept:", u.department)
    if u.username == "admin":
        print("  adminpassword matches hash?", verify_password("adminpassword", u.hashed_password))

db.close()