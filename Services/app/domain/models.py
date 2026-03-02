from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional

# 1. THE LEDGER MODEL
class LedgerEntry(BaseModel):
    Date: date
    Type: str = Field(..., pattern="^(Buy Shares|Sell Shares|Deposit|Withdrawal|Dividend|Charges|Payable|Receivable).*")
    Category: str
    Amount: float = Field(..., gt=-1000000000, lt=1000000000)
    Status: str = Field(default="Cleared")
    Due_Date: Optional[date] = None
    Ref_ID: str = ""
    Description: str = ""
    Is_Non_Cash: bool = False
    Dispute_Note: str = ""
    Fiscal_Year: str = Field(..., pattern=r"^\d{4}/\d{4}$")

    @field_validator('Amount')
    @classmethod
    def check_amount(cls, v):
        # You can add custom logic here if needed
        return round(v, 2)

# 2. THE HOLDINGS MODEL
class HoldingEntry(BaseModel):
    Symbol: str = Field(..., min_length=1)
    Total_Qty: float = Field(..., ge=0)
    Pledged_Qty: float = Field(default=0, ge=0)
    LTP: float = Field(default=0, ge=0)
    Haircut: float = Field(default=0, ge=0, le=100)

    @field_validator('Symbol')
    @classmethod
    def uppercase_symbol(cls, v):
        return v.upper()

# 3. THE PRICE CACHE MODEL (For public_Files)
class PriceCache(BaseModel):
    Symbol: str
    LTP: float
    Change: float = 0.0
    High52: float = 0.0
    Low52: float = 0.0
    LastUpdated: str
