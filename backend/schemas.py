from pydantic import BaseModel
from datetime import datetime

class Transaction(BaseModel):
    TransactionDate: datetime
    Amount: float
    MerchantID: int
    TransactionType: str
    Location: str
