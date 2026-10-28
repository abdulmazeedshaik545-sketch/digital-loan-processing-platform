import os, uuid
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Loan Processing Service")
CUSTOMER_URL = os.getenv("CUSTOMER_SERVICE_URL", "http://localhost:8082")
DOCUMENT_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://localhost:8083")
NOTIFICATION_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8084")
LOANS = []

class LoanRequest(BaseModel):
    customer_id: str
    amount: float = Field(gt=0, le=5000000)
    annual_income: float = Field(gt=0)
    employment_type: str = "salaried"
    document_ids: list[str] = []

@app.get("/health")
def health():
    return {"status": "ok", "service": "loan-service"}

@app.get("/loans")
def list_loans():
    return LOANS

@app.post("/loans")
async def create_loan(request: LoanRequest):
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            customer = await client.get(f"{CUSTOMER_URL}/customers/{request.customer_id}")
            docs = await client.post(f"{DOCUMENT_URL}/validate", json={"document_ids": request.document_ids})
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="A dependent service is unavailable")
    if customer.status_code == 404:
        raise HTTPException(status_code=400, detail="Unknown customer_id in demo customer directory")
    if docs.status_code >= 400:
        raise HTTPException(status_code=400, detail="Document validation service failed")
    doc_result = docs.json()
    if not doc_result["valid"]:
        status = "pending_documents"
    else:
        # Educational demo rule only; not a real underwriting/credit model.
        status = "eligible_for_review" if request.annual_income >= request.amount * 2 else "rejected_demo_rule"
    loan = {
        "loan_id": "LN-" + uuid.uuid4().hex[:10].upper(),
        "customer_id": request.customer_id,
        "amount": request.amount,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    LOANS.append(loan)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(f"{NOTIFICATION_URL}/notify", json={
                "customer_id": request.customer_id,
                "message": f"Demo loan {loan['loan_id']} status: {status}"
            })
    except httpx.HTTPError:
        pass
    return loan
