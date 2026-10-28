from fastapi import FastAPI
app = FastAPI(title="Customer Profile Service")
CUSTOMERS = {
    "C1001": {"customer_id": "C1001", "name": "Sample Customer", "segment": "retail"},
    "C1002": {"customer_id": "C1002", "name": "Demo Customer", "segment": "retail"}
}

@app.get("/health")
def health():
    return {"status": "ok", "service": "customer-service"}

@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    customer = CUSTOMERS.get(customer_id)
    if customer is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Customer not found in demo directory")
    return customer
