from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, database
from app.routers import projects, sessions, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database connection and tables
    await database.connect()
    await init_db()
    yield
    # Shutdown: Disconnect database
    await database.disconnect()


app = FastAPI(title="Measured API", version="1.0.0", lifespan=lifespan)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "https://measured-tracker.vercel.app",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])

