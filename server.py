from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from core.sheets_handler import SheetsHandler

load_dotenv()

app = FastAPI()

# CORS Setup
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Config
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "password")

class LoginRequest(BaseModel):
    username: str
    password: str

class UpdateRequest(BaseModel):
    row_id: int
    data: Dict[str, Any]

@app.post("/api/login")
def login(creds: LoginRequest):
    if creds.username == ADMIN_USER and creds.password == ADMIN_PASS:
        return {"status": "success", "token": "fake-jwt-token-for-demo"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/content")
def get_content():
    handler = SheetsHandler()
    data = handler.get_all_content()
    return data

@app.put("/api/content/{row_id}")
def update_content(row_id: int, update: UpdateRequest):
    handler = SheetsHandler()
    success = handler.update_content(row_id, update.data)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update content")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
