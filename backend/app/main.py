from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import validate, history, reference, export, reports
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Rhadix Validator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(validate.router,   prefix="/api/validate",   tags=["Validation"])
app.include_router(history.router,    prefix="/api/history",    tags=["History"])
app.include_router(reference.router,  prefix="/api/reference",  tags=["Reference"])
app.include_router(export.router,     prefix="/api/export",     tags=["Export"])
app.include_router(reports.router,    prefix="/api/reports",    tags=["Reports"])

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Rhadix Validator"}
