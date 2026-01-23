from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="Dexter AI Platform", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Dexter AI Platform API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dexter-backend"}

@app.get("/api/status")
async def api_status():
    return {
        "api": "online",
        "database": "connected",
        "redis": "connected",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
