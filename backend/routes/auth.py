from fastapi import APIRouter, HTTPException
from models.userModel import UserCreate, UserLogin
from db import users_collection
from utils.hash import hash_password, verify_password

router = APIRouter()

@router.post("/signup")
async def signup(user: UserCreate):
    # Check if user exists
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed = hash_password(user.password)

    # Insert user
    await users_collection.insert_one({
        "name": user.name,
        "email": user.email,
        "password": hashed
    })

    return {"message": "User created successfully"}

@router.post("/login")
async def login(user: UserLogin):
    db_user = await users_collection.find_one({"email": user.email})
    if not db_user:
        raise HTTPException(status_code=404, detail="Invalid credentials")

    if not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "user": db_user["email"]}
    