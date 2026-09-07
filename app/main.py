from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="ERP Natural-Language Q&A API",
    description="Deterministic Q&A system for ERP data",
    version="0.1.0"
)

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
