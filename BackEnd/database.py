from motor.motor_asyncio import AsyncIOMotorClient
from ..models.user import UserInDB, UserCreate
import bcrypt
from typing import Optional

# Database connection
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.ranking_db
users_collection = db.users

# Initialize database with default admin user if not exists
async def init_db():
    # Create indexes
    await users_collection.create_index("email", unique=True)
    
    # Create default admin user if not exists
    admin_email = "admin@example.com"
    admin_password = "admin123"
    
    existing_admin = await users_collection.find_one({"email": admin_email})
    if not existing_admin:
        hashed_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
        admin_user = {
            "email": admin_email,
            "name": "Admin User",
            "hashed_password": hashed_password.decode('utf-8'),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        await users_collection.insert_one(admin_user)
        print("Default admin user created")

# Get user by email
async def get_user_by_email(email: str) -> Optional[UserInDB]:
    user = await users_collection.find_one({"email": email})
    if user:
        return UserInDB(**user, id=str(user["_id"]))
    return None

# Verify user credentials
async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    user = await get_user_by_email(email)
    if not user:
        return None
    if not bcrypt.checkpw(password.encode('utf-8'), user.hashed_password.encode('utf-8')):
        return None
    return user
