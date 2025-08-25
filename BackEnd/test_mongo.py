import pymongo

try:
    print("🔄 Attempting to connect to MongoDB...")
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    
    # Check if connection is successful
    client.server_info()
    print("✅ Successfully connected to MongoDB!")
    
    # List all databases
    print("\n📂 Available databases:")
    for db in client.list_database_names():
        print(f"- {db}")
        
except Exception as e:
    print(f"\n❌ Failed to connect to MongoDB. Error: {e}")
    print("\n🔧 Troubleshooting steps:")
    print("1. Make sure MongoDB is installed")
    print("2. Start MongoDB service:")
    print("   - Open Services (Win + R -> services.msc)")
    print("   - Find 'MongoDB' and start it")
    print("3. Try connecting through MongoDB Compass")
    print("4. Check if MongoDB is running on port 27017")
