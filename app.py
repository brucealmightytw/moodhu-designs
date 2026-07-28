from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import os
import time
from typing import Dict, Any

app = FastAPI()

# Config
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DESIGNS_FILE = DATA_DIR / "designs.json"
DELETED_FILE = DATA_DIR / "deleted_ids.json"
VOTES_FILE = DATA_DIR / "votes.json"
ADMIN_PASSWORD = "moodhu"

# Initialize data files
if not DELETED_FILE.exists():
    with open(DELETED_FILE, "w") as f:
        json.dump([], f)

if not VOTES_FILE.exists():
    with open(VOTES_FILE, "w") as f:
        json.dump({}, f)

# Load data
def load_designs():
    with open(DESIGNS_FILE, "r") as f:
        data = json.load(f)
    
    # Convert old format (object) to new format (array)
    if isinstance(data, dict) and "designs" not in data:
        designs = []
        for id, design in data.items():
            design["id"] = id
            designs.append(design)
        return {"designs": designs, "total": len(designs)}
    
    return data

def save_designs(data):
    with open(DESIGNS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_deleted():
    with open(DELETED_FILE, "r") as f:
        return json.load(f)

def save_deleted(ids):
    with open(DELETED_FILE, "w") as f:
        json.dump(ids, f, indent=2)

def load_votes():
    with open(VOTES_FILE, "r") as f:
        return json.load(f)

def save_votes(votes):
    with open(VOTES_FILE, "w") as f:
        json.dump(votes, f, indent=2)

# API Endpoints
@app.get("/api/designs")
async def get_designs():
    data = load_designs()
    deleted = load_deleted()
    data["designs"] = [d for d in data["designs"] if d["id"] not in deleted]
    data["total"] = len(data["designs"])
    return data

@app.get("/api/votes")
async def get_votes():
    designs = load_designs()["designs"]
    votes = load_votes()
    
    # Aggregate votes
    result = {}
    for d in designs:
        result[d["id"]] = {"likes": 0, "dislikes": 0}
    
    for vote in votes.values():
        if vote["design_id"] in result:
            if vote["action"] == "like":
                result[vote["design_id"]]["likes"] += 1
            else:
                result[vote["design_id"]]["dislikes"] += 1
    
    return result

@app.get("/api/votes/me")
async def get_my_votes(voter_id: str):
    votes = load_votes()
    return {k: v for k, v in votes.items() if v["voter_id"] == voter_id}

@app.post("/api/vote")
async def cast_vote(request: Request):
    data = await request.json()
    voter_id = request.query_params.get("voter_id")
    design_id = data.get("design_id")
    action = data.get("action")
    
    if not all([voter_id, design_id, action]):
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    if action not in ["like", "dislike"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    votes = load_votes()
    
    # Check if already voted
    for vote_id, vote in votes.items():
        if vote["voter_id"] == voter_id and vote["design_id"] == design_id:
            raise HTTPException(status_code=400, detail="Already voted")
    
    # Record vote
    vote_id = f"{voter_id}_{design_id}_{int(time.time())}"
    votes[vote_id] = {
        "voter_id": voter_id,
        "design_id": design_id,
        "action": action,
        "timestamp": int(time.time())
    }
    
    save_votes(votes)
    return {"ok": True}

@app.post("/api/delete")
async def delete_design(request: Request):
    data = await request.json()
    design_id = data.get("design_id")
    password = data.get("password")
    
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Wrong password")
    
    if not design_id:
        raise HTTPException(status_code=400, detail="Missing design_id")
    
    # Add to deleted list
    deleted = load_deleted()
    if design_id not in deleted:
        deleted.append(design_id)
        save_deleted(deleted)
    
    return {"ok": True}

# Static files
app.mount("/thumbs", StaticFiles(directory="thumbs"), name="thumbs")
app.mount("/images", StaticFiles(directory="images"), name="images")

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)