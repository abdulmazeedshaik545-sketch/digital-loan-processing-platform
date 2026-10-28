import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Loan Customer Portal API")
LOAN_SERVICE_URL = os.getenv("LOAN_SERVICE_URL", "http://localhost:8081")

class LoanRequest(BaseModel):
    customer_id: str
    amount: float = Field(gt=0, le=5000000)
    annual_income: float = Field(gt=0)
    employment_type: str = "salaried"
    document_ids: list[str] = []

@app.get("/health")
def health():
    return {"status": "ok", "service": "frontend"}

@app.post("/apply")
async def apply_for_loan(payload: LoanRequest):
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(f"{LOAN_SERVICE_URL}/loans", json=payload.model_dump())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Loan service unavailable: {exc.__class__.__name__}")
