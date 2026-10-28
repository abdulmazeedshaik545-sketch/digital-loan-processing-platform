from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI(title="Notification Service")
OUTBOX = []

class Notification(BaseModel):
    customer_id: str
    message: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}

@app.post("/notify")
def notify(payload: Notification):
    record = {"customer_id": payload.customer_id, "message": payload.message, "delivery": "simulated"}
    OUTBOX.append(record)
    print({"event": "notification_simulated", **record}, flush=True)
    return record

@app.get("/notifications")
def list_notifications():
    return OUTBOX
