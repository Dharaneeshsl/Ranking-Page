import os
import logging
import ssl
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import bcrypt
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from datetime import datetime
from .models.user import UserInDB

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseConfigError(Exception):
    """Raised when there's an error in database configuration"""
    pass

# ====================================
# Database Configuration
# ====================================
# Required environment variables with validation
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME")
REQUIRED_ENV_VARS = {
    "MONGODB_URI": MONGODB_URI,
    "DATABASE_NAME": DATABASE_NAME,
    "ADMIN_EMAIL": os.getenv("ADMIN_EMAIL"),
    "ADMIN_PASSWORD": os.getenv("ADMIN_PASSWORD")
}

# Validate all required configurations
missing_vars = [var for var, val in REQUIRED_ENV_VARS.items() if not val]
if missing_vars:
    error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
    logger.critical(error_msg)
    raise DatabaseConfigError(error_msg)

# Admin configuration
ADMIN_CONFIG = {
    "email": os.getenv("ADMIN_EMAIL").strip(),
    "password": os.getenv("ADMIN_PASSWORD").strip(),
    "name": (os.getenv("ADMIN_NAME") or "Admin User").strip(),
}

# SSL Configuration for production
SSL_CA_CERTS = os.getenv("SSL_CA_CERTS")
SSL_CERT_REQS = ssl.CERT_REQUIRED if os.getenv("ENVIRONMENT") == "production" else ssl.CERT_NONE

# Initialize MongoDB client with production-ready settings
client = None
try:
    ssl_context = None
    if os.getenv("ENVIRONMENT") == "production":
        ssl_context = ssl.create_default_context(cafile=SSL_CA_CERTS)
        ssl_context.verify_mode = SSL_CERT_REQS

    client = AsyncIOMotorClient(
        MONGODB_URI,
        ssl=ssl_context is not None,
        ssl_cert_reqs=SSL_CERT_REQS,
        ssl_ca_certs=SSL_CA_CERTS,
        maxPoolSize=int(os.getenv("DB_MAX_POOL_SIZE", "100")),
        minPoolSize=int(os.getenv("DB_MIN_POOL_SIZE", "5")),
        maxIdleTimeMS=30000,
        connectTimeoutMS=10000,
        serverSelectionTimeoutMS=10000,
        socketTimeoutMS=45000,
        retryWrites=True,
        retryReads=True,
        readPreference='secondaryPreferred' if os.getenv("ENVIRONMENT") == "production" else 'primary',
        replicaSet=os.getenv("MONGODB_REPLICA_SET")
    )
    
    logger.info("MongoDB client initialized with production settings")
    
except Exception as e:
    logger.critical(f"Failed to initialize MongoDB client: {str(e)}")
    raise

# Database and collections
db = client.get_database(DATABASE_NAME)
users_collection = db.users
members_collection = db.members

@asynccontextmanager
async def get_db_session():
    """Async context manager for database sessions"""
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        raise

async def init_db():
    """
    Initialize database with indexes and default admin user.
    
    Raises:
        Exception: If database initialization fails
    """
    try:
        # Test database connection
        await client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        
        # Create indexes
        await users_collection.create_index("email", unique=True)
        await members_collection.create_index("email", unique=True)
        logger.info("✅ Database indexes created/verified")
        
        # Create default admin user if credentials are provided
        if all(ADMIN_CONFIG.values()):
            existing_admin = await users_collection.find_one(
                {"email": ADMIN_CONFIG["email"], "role": "admin"}
            )
            
            if not existing_admin:
                hashed_password = bcrypt.hashpw(
                    ADMIN_CONFIG["password"].encode('utf-8'), 
                    bcrypt.gensalt()
                )
                admin_user = {
                    "email": ADMIN_CONFIG["email"],
                    "name": ADMIN_CONFIG["name"],
                    "hashed_password": hashed_password.decode('utf-8'),
                    "role": "admin",
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                await users_collection.insert_one(admin_user)
                logger.info(f"✅ Created default admin user: {ADMIN_CONFIG['email']}")
            else:
                logger.info("ℹ️  Admin user already exists")
        else:
            logger.warning("⚠️  Admin credentials not fully configured in environment variables")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        raise

async def get_user_by_email(email: str) -> Optional[UserInDB]:
    """
    Get a user by email address.
    
    Args:
        email: The email address of the user to find
        
    Returns:
        UserInDB if found, None otherwise
    """
    try:
        user = await users_collection.find_one({"email": email, "is_active": True})
        if user:
            return UserInDB(**user, id=str(user["_id"]))
        return None
    except Exception as e:
        logger.error(f"Error fetching user by email {email}: {str(e)}")
        return None

async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate a user with email and password.
    
    Args:
        email: User's email
        password: Plain text password
        
    Returns:
        UserInDB if authentication successful, None otherwise
    """
    try:
        user = await get_user_by_email(email)
        if not user:
            # Log failed login attempt (without logging password)
            logger.warning(f"Login attempt failed for email: {email} - User not found")
            return None
            
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.hashed_password.encode('utf-8')):
            # Log failed login attempt (without logging password)
            logger.warning(f"Login attempt failed for email: {email} - Invalid password")
            return None
            
        # Update last login time
        await users_collection.update_one(
            {"email": email},
            {"$set": {"last_login": datetime.utcnow().isoformat()}}
        )
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication error for {email}: {str(e)}")
        return None
