from fastapi import FastAPI
from pydantic import BaseModel
app = FastAPI(title="Document Metadata Service")

class DocumentCheck(BaseModel):
    document_ids: list[str] = []

@app.get("/health")
def health():
    return {"status": "ok", "service": "document-service"}

@app.post("/validate")
def validate_documents(payload: DocumentCheck):
    # Demo only: treat any non-empty document list as present.
    # This service does NOT upload/store file bytes or perform KYC.
    return {"valid": len(payload.document_ids) > 0, "count": len(payload.document_ids),
            "note": "metadata-only demo; no KYC verification performed"}
