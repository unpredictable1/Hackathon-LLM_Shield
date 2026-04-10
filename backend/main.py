import os
import re
import json
import sys
from typing import Optional, Dict, Any

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================================================
# 1. DYNAMIC PATH INJECTION (Critical for your structure)
# =========================================================
# Move up ONE level to find LLMShield.py
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_PATH)
try:
    from LLMShield import LLMShieldSystem
except ImportError:
    raise ImportError(f"❌ Could not find LLMShield.py at {ROOT_PATH}")

try:
    from groq import Groq
except ImportError:
    Groq = None

# =========================================================
# App setup
# =========================================================
app = FastAPI(title="GuardPay AI: Safety Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# Initialize Your Professional System
# =========================================================
# This automatically loads your l2_model and security_db
system = LLMShieldSystem()

# =========================================================
# Request / Response schemas
# =========================================================
class PromptRequest(BaseModel):
    prompt: str

class PromptResponse(BaseModel):
    original_prompt: str
    action: str
    final_message: str
    unsafe_probability: float
    risk_level: str
    threat_type: str  # Updated to show your L2 categories

# =========================================================
# Routes
# =========================================================
@app.get("/")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "message": "GuardPay AI Safety System is Online",
        "root_path": ROOT_PATH,
        "device": "cuda" if torch.cuda.is_available() else "cpu"
    }

@app.post("/analyze", response_model=PromptResponse)
def analyze_prompt(payload: PromptRequest) -> Dict[str, Any]:
    prompt = payload.prompt.strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    # 1. RUN YOUR FULL LLMSHIELD PIPELINE (Anonymize -> Scan -> KB -> Judge)
    # This calls your Step 1-7 in LLMShield.py
    final_output = system.query(prompt)

    # 2. INTERNAL SCAN FOR METADATA
    # We run a quick scan just to provide the UI with probability/threat info
    meta_check = system.shield.scan(prompt)

    # 3. DETERMINE ACTION FOR WEB UI
    if "❌" in final_output or "⚠️" in final_output:
        action = "BLOCK"
    elif "CONFIDENTIAL_" in final_output:
        action = "ANONYMIZE"
    else:
        action = "ALLOW"

    return {
        "original_prompt": prompt,
        "action": action,
        "final_message": final_output,
        "unsafe_probability": round(float(meta_check["score"]), 4),
        "risk_level": meta_check["tier"],
        "threat_type": meta_check["threat"]
    }