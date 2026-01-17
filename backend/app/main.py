from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, database
from app.routers import projects, sessions, health

app = FastAPI(title="Measured API", version="1.0.0")

# Initialize database connection and tables on startup
@app.on_event("startup")
async def startup_event():
    await database.connect()
    await init_db()

# Disconnect database on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])

