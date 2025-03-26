from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb+srv://bpscrohit:Rohit123@cluster0.rszwkl0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client.fraud_db  # your DB name
users_collection = db.users
