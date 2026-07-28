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
DATA_DIR = Path(".")
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
    
    # Aggregate votes (handle both old array format and new dict format)
    result = {}
    for d in designs:
        result[d["id"]] = {"likes": 0, "dislikes": 0}
    
    for voter_id, voter_votes in votes.items():
        # Handle array format: {"voter_id": [{"design_id":..., "vote_type":...}]}
        if isinstance(voter_votes, list):
            for v in voter_votes:
                did = v.get("design_id")
                vt = v.get("vote_type", v.get("action"))
                if did in result:
                    if vt == "like":
                        result[did]["likes"] += 1
                    elif vt == "dislike":
                        result[did]["dislikes"] += 1
        # Handle dict format: {"vote_id": {"design_id":..., "action":...}}
        elif isinstance(voter_votes, dict):
            did = voter_votes.get("design_id")
            act = voter_votes.get("action", voter_votes.get("vote_type"))
            if did in result:
                if act == "like":
                    result[did]["likes"] += 1
                elif act == "dislike":
                    result[did]["dislikes"] += 1
    
    return result

@app.get("/api/votes/me")
async def get_my_votes(voter_id: str):
    votes = load_votes()
    result = {}
    for vid, voter_votes in votes.items():
        if vid != voter_id:
            continue
        # Handle array format
        if isinstance(voter_votes, list):
            for v in voter_votes:
                result[v["design_id"]] = v.get("vote_type", v.get("action"))
        # Handle dict format
        elif isinstance(voter_votes, dict):
            result[voter_votes.get("design_id")] = voter_votes.get("action", voter_votes.get("vote_type"))
    return result

@app.post("/api/vote")
async def cast_vote(request: Request):
    data = await request.json()
    voter_id = data.get("voter_id") or request.query_params.get("voter_id")
    design_id = data.get("design_id")
    action = data.get("vote_type") or data.get("action")
    
    if not all([voter_id, design_id, action]):
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    if action not in ["like", "dislike"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    votes = load_votes()
    
    # Check if already voted (allow changing vote)
    existing_idx = None
    if voter_id in votes:
        for i, v in enumerate(votes[voter_id]):
            if v["design_id"] == design_id:
                existing_idx = i
                break
    
    if existing_idx is not None:
        if votes[voter_id][existing_idx]["vote_type"] == action:
            # Same vote — remove it (toggle off)
            votes[voter_id].pop(existing_idx)
            if not votes[voter_id]:
                del votes[voter_id]
            save_votes(votes)
            return {"ok": True, "action": "removed"}
        else:
            # Different vote — update it
            votes[voter_id][existing_idx]["vote_type"] = action
            votes[voter_id][existing_idx]["created_at"] = str(uuid.uuid4())
            save_votes(votes)
            return {"ok": True, "action": "changed"}
    
    # Record new vote in array format
    import uuid
    votes[voter_id].append({
        "design_id": design_id,
        "vote_type": action,
        "created_at": str(uuid.uuid4())
    })
    
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