import os
import time
import uuid
from datetime import datetime, timezone

import httpx
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Loan Processing Service")

CUSTOMER_URL = os.getenv("CUSTOMER_SERVICE_URL", "http://localhost:8082")
DOCUMENT_URL = os.getenv("DOCUMENT_SERVICE_URL", "http://localhost:8083")
NOTIFICATION_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8084")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://loanapp:local-demo-only@localhost:5432/loans"
)


class LoanRequest(BaseModel):
    customer_id: str
    amount: float = Field(gt=0, le=5000000)
    annual_income: float = Field(gt=0)
    employment_type: str = "salaried"
    document_ids: list[str] = []


def get_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


@app.on_event("startup")
def initialize_database():
    for attempt in range(30):
        try:
            with get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS loans (
                        loan_id VARCHAR(30) PRIMARY KEY,
                        customer_id VARCHAR(100) NOT NULL,
                        amount NUMERIC(14, 2) NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                """)
            print("PostgreSQL database initialized successfully", flush=True)
            return
        except psycopg.OperationalError as exc:
            print(
                f"Waiting for PostgreSQL ({attempt + 1}/30): {exc}",
                flush=True
            )
            time.sleep(2)

    raise RuntimeError("Could not connect to PostgreSQL after 30 attempts")


@app.get("/health")
def health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "service": "loan-service", "database": "connected"}
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/loans")
def list_loans():
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM loans ORDER BY created_at DESC"
            ).fetchall()
        return rows
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Could not retrieve loans")


@app.post("/loans")
async def create_loan(request: LoanRequest):
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            customer = await client.get(
                f"{CUSTOMER_URL}/customers/{request.customer_id}"
            )
            docs = await client.post(
                f"{DOCUMENT_URL}/validate",
                json={"document_ids": request.document_ids}
            )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=502,
                detail="A dependent service is unavailable"
            )

    if customer.status_code == 404:
        raise HTTPException(
            status_code=400,
            detail="Unknown customer_id in demo customer directory"
        )

    if docs.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail="Document validation service failed"
        )

    if not docs.json()["valid"]:
        status = "pending_documents"
    else:
        # Educational demo rule only; not a real credit assessment.
        status = (
            "eligible_for_review"
            if request.annual_income >= request.amount * 2
            else "rejected_demo_rule"
        )

    loan = {
        "loan_id": "LN-" + uuid.uuid4().hex[:10].upper(),
        "customer_id": request.customer_id,
        "amount": request.amount,
        "status": status,
        "created_at": datetime.now(timezone.utc)
    }

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO loans
                    (loan_id, customer_id, amount, status, created_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    loan["loan_id"],
                    loan["customer_id"],
                    loan["amount"],
                    loan["status"],
                    loan["created_at"]
                )
            )
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Could not save loan application"
        )

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{NOTIFICATION_URL}/notify",
                json={
                    "customer_id": request.customer_id,
                    "message": f"Demo loan {loan['loan_id']} status: {status}"
                }
            )
    except httpx.HTTPError:
        print("Notification service unavailable", flush=True)

    return loan
