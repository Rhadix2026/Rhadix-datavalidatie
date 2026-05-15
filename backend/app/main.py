from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import validate, history, reference, export, reports, profiles
from app.reconciliation.router import router as recon_router
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rhadix Validator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(validate.router,   prefix="/api/validate",   tags=["Validation"])
app.include_router(history.router,    prefix="/api/history",    tags=["History"])
app.include_router(reference.router,  prefix="/api/reference",  tags=["Reference"])
app.include_router(export.router,     prefix="/api/export",     tags=["Export"])
app.include_router(reports.router,    prefix="/api/reports",    tags=["Reports"])
app.include_router(profiles.router,                        tags=["Profiles"])
app.include_router(recon_router, prefix="/api/reconciliation", tags=["Reconciliation"])

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Rhadix Validator"}
