from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.club_db
members_collection = db.members

async def startup_db_client():
    await members_collection.create_index([("points", -1)])
    await members_collection.create_index([("email", 1)], unique=True, sparse=True)
    await members_collection.create_index([("name", 1), ("email", 1)], unique=True, sparse=True)
