import asyncio
from database import members_collection, startup_db_client

async def test_connection():
    try:
        await startup_db_client()
        # Test database connection
        await members_collection.find_one()
        print("✅ Successfully connected to MongoDB")
        
        # Test adding a test member if none exists
        test_member = await members_collection.find_one({"name": "Test User"})
        if not test_member:
            result = await members_collection.insert_one({
                "name": "Test User",
                "email": "test@example.com",
                "points": 0,
                "level": "Bronze Member",
                "contributions": [],
                "badges": ["Bronze Member"]
            })
            print(f"✅ Created test member with ID: {result.inserted_id}")
        else:
            print(f"ℹ️ Test member already exists with ID: {test_member['_id']}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        # Close the MongoDB connection
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        client.close()

if __name__ == "__main__":
    print("🚀 Testing database setup...")
    asyncio.run(test_connection())
