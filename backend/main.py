from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from collections import defaultdict
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routes import auth
import os


app = FastAPI()
app.include_router(auth.router)

# Load model & encoders
model = joblib.load("fraud_model.pkl")
label_encoders = joblib.load("label_encoders.pkl")

# MongoDB setup (you can set this via .env or secrets for security)
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://bpscrohit:Rohit123@cluster0.rszwkl0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client["fraud_detection"]
collection = db["predictions"]
transactions_collection = db["predictions"]
users_collection = db.users

# Define input schema
class TransactionInput(BaseModel):
    TransactionID: int
    TransactionDate: str
    Amount: float
    MerchantID: int
    TransactionType: str
    Location: str

# 👇 Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["http://localhost:5173"] for more control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to convert MongoDB ObjectId and fields to JSON serializable
def serialize_doc(doc):
    return {
        "TransactionID": doc.get("TransactionID"),
        "Timestamp": doc.get("TransactionDate"),
        "Amount": doc.get("Amount"),
        "Location": doc.get("Location"),
        "MerchantID": doc.get("MerchantID"),
        "TransactionType": doc.get("TransactionType"),
        "isFraud": doc.get("isFraud"),
        "fraudProbability": doc.get("fraudProbability"),
    }

@app.post("/predict")
def predict_fraud(data: TransactionInput):
    # Convert input to DataFrame
    df = pd.DataFrame([{
        "TransactionID": data.TransactionID,
        "TransactionDate": data.TransactionDate,
        "Amount": data.Amount,
        "MerchantID": data.MerchantID,
        "TransactionType": data.TransactionType,
        "Location": data.Location
    }])

    # Datetime features
    df["TransactionDate"] = pd.to_datetime(df["TransactionDate"], errors="coerce")
    df["Hour"] = df["TransactionDate"].dt.hour
    df["Day"] = df["TransactionDate"].dt.day
    df["Month"] = df["TransactionDate"].dt.month
    df["Weekday"] = df["TransactionDate"].dt.weekday
    df.drop("TransactionDate", axis=1, inplace=True)

    # Encode
    for col in ["TransactionType", "Location"]:
        le = label_encoders[col]
        df[col] = df[col].apply(lambda x: le.transform([x])[0] if x in le.classes_ else -1)

    # Ensure correct column order
    expected_columns = ['TransactionID', 'Amount', 'MerchantID', 'TransactionType', 'Location', 'Hour', 'Day', 'Month', 'Weekday']
    df = df[expected_columns]

    # Predict
    prediction = int(model.predict(df)[0])
    probability = float(model.predict_proba(df)[0][1])

    # Store in MongoDB
    record = data.dict()
    record["isFraud"] = prediction
    record["fraudProbability"] = round(probability, 4)
    record["timestamp"] = datetime.utcnow()

    collection.insert_one(record)

    return {
        "isFraud": prediction,
        "fraudProbability": round(probability, 4)
    }

@app.get("/fraud-rate-by-city")
def fraud_rate_by_city():
    transactions = list(transactions_collection.find())

    city_data = defaultdict(lambda: {
        "total": 0,
        "frauds": 0,
        "fraudProbSum": 0.0
    })

    for tx in transactions:
        city = tx.get("Location", "Unknown")
        is_fraud = tx.get("IsFraud", 0)
        fraud_prob = float(tx.get("fraudProbability", 0.0))

        city_data[city]["total"] += 1
        city_data[city]["fraudProbSum"] += fraud_prob
        if is_fraud == 1:
            city_data[city]["frauds"] += 1

    result = []
    for city, stats in city_data.items():
        total = stats["total"]
        frauds = stats["frauds"]
        avg_prob = stats["fraudProbSum"] / total if total > 0 else 0
        fraud_rate = frauds / total if total > 0 else 0

        result.append({
            "city": city,
            "total": total,
            "frauds": frauds,
            "fraudRate": round(fraud_rate, 4),
            "avgFraudProbability": round(avg_prob, 4)
        })

    return JSONResponse(content=result)

# ✅ GET endpoint to fetch all transactions
@app.get("/transactions")
def get_all_transactions():
    transactions = list(collection.find())
    return [serialize_doc(doc) for doc in transactions]