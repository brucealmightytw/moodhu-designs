from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import os
import time
import uuid
from typing import Dict, Any

app = FastAPI()

# Config
DATA_DIR = Path(os.environ.get("DATA_DIR", "."))
DATA_DIR.mkdir(exist_ok=True)
DESIGNS_FILE = DATA_DIR / "designs.json"
DELETED_FILE = DATA_DIR / "deleted_ids.json"
VOTES_FILE = DATA_DIR / "votes.json"
FLAGGED_FILE = DATA_DIR / "flagged.json"
CORRECTIONS_FILE = DATA_DIR / "corrections.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "moodhu")

# Canonical category list for the correction dropdown — keep in sync with the
# real species/themes used across designs.json. "Uncategorized" and any stray
# filesystem-path values are deliberately excluded; pick the closest real match instead.
CATEGORIES = [
    "Clownfish", "Dolphin", "HammerheadShark", "MandalaMantaWhaleShark",
    "MantaRay", "MantaWhaleShark", "Mixed", "NapoleonWrasse", "ReefShark",
    "SeaTurtle", "TigerShark", "TropicalFish", "WhaleShark",
]

# Initialize data files
if not DELETED_FILE.exists():
    with open(DELETED_FILE, "w") as f:
        json.dump([], f)

if not VOTES_FILE.exists():
    with open(VOTES_FILE, "w") as f:
        json.dump({}, f)

if not FLAGGED_FILE.exists():
    with open(FLAGGED_FILE, "w") as f:
        json.dump({}, f)

if not CORRECTIONS_FILE.exists():
    with open(CORRECTIONS_FILE, "w") as f:
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

def load_flagged():
    with open(FLAGGED_FILE, "r") as f:
        return json.load(f)

def save_flagged(flagged):
    with open(FLAGGED_FILE, "w") as f:
        json.dump(flagged, f, indent=2)

def load_corrections():
    with open(CORRECTIONS_FILE, "r") as f:
        return json.load(f)

def save_corrections(corrections):
    with open(CORRECTIONS_FILE, "w") as f:
        json.dump(corrections, f, indent=2)

# API Endpoints
@app.get("/api/designs")
async def get_designs():
    data = load_designs()
    deleted = load_deleted()
    votes = load_votes()
    corrections = load_corrections()
    flagged = load_flagged()

    # Aggregate votes
    agg = {}
    for vid, vlist in votes.items():
        if isinstance(vlist, list):
            for v in vlist:
                did = v.get("design_id")
                vt = v.get("vote_type", v.get("action"))
                if did not in agg:
                    agg[did] = {"likes": 0, "dislikes": 0}
                if vt == "like":
                    agg[did]["likes"] += 1
                elif vt == "dislike":
                    agg[did]["dislikes"] += 1

    # Filter deleted and add computed votes
    designs = []
    for d in data["designs"]:
        if d["id"] in deleted:
            continue
        v = agg.get(d["id"], {"likes": 0, "dislikes": 0})
        d["votes"] = {
            "likes": v["likes"],
            "dislikes": v["dislikes"],
            "net": v["likes"] - v["dislikes"]
        }
        correction = corrections.get(d["id"])
        if correction and correction.get("confirmed"):
            d["category"] = correction["category"]
        if d["id"] in flagged:
            d["flagged"] = True
        designs.append(d)

    # Sort by net votes descending (default ranking)
    designs.sort(key=lambda x: x["votes"]["net"], reverse=True)
    
    data["designs"] = designs
    data["total"] = len(designs)
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
    
    # Add net to each design's votes
    for did in result:
        result[did]["net"] = result[did]["likes"] - result[did]["dislikes"]
    
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

def _client_ip(request: Request) -> str:
    # Zeabur (like most PaaS) sits behind a proxy — the real client IP is in
    # X-Forwarded-For, not request.client.host (which would be the proxy's IP).
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _ip_already_voted_elsewhere(votes: dict, design_id: str, ip: str, voter_id: str) -> bool:
    """True if some OTHER voter_id from this same IP already has a vote on this
    design. voter_id is client-supplied and trivially forgeable (no login, no
    cookie) — anyone could otherwise cast unlimited votes on one design just by
    sending a fresh random voter_id each time. This closes that gap without
    requiring accounts, at the cost of shared-IP false positives (offices, NAT)."""
    if ip == "unknown":
        return False
    for vid, vlist in votes.items():
        if vid == voter_id or not isinstance(vlist, list):
            continue
        for v in vlist:
            if v.get("design_id") == design_id and v.get("ip") == ip:
                return True
    return False


@app.post("/api/vote")
async def cast_vote(request: Request):
    data = await request.json()
    voter_id = data.get("voter_id") or request.query_params.get("voter_id")
    design_id = data.get("design_id")
    action = data.get("vote_type") or data.get("action")
    ip = _client_ip(request)

    # Handle explicit remove action
    if action == 'remove':
        votes = load_votes()
        if voter_id in votes:
            votes[voter_id] = [v for v in votes[voter_id] if v["design_id"] != design_id]
            if not votes[voter_id]:
                del votes[voter_id]
            save_votes(votes)
        return {"ok": True, "action": "removed"}

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
            votes[voter_id][existing_idx]["ip"] = ip
            save_votes(votes)
            return {"ok": True, "action": "changed"}

    # Brand-new vote for this voter_id — reject if this IP already voted on this
    # design under a different voter_id (see _ip_already_voted_elsewhere).
    if _ip_already_voted_elsewhere(votes, design_id, ip, voter_id):
        raise HTTPException(status_code=429, detail="Already voted for this design")

    # Record new vote in array format
    if voter_id not in votes:
        votes[voter_id] = []
    votes[voter_id].append({
        "design_id": design_id,
        "vote_type": action,
        "created_at": str(uuid.uuid4()),
        "ip": ip,
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

@app.get("/api/categories")
async def get_categories():
    return {"categories": CATEGORIES}

@app.post("/api/admin/verify")
async def verify_admin(request: Request):
    """Checks the password with no side effects, so the frontend can enter
    admin mode once and reuse the password for subsequent actions without
    re-prompting on every delete/flag/correct."""
    data = await request.json()
    password = data.get("password")
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Wrong password")
    return {"ok": True}

@app.post("/api/flag")
async def flag_design(request: Request):
    data = await request.json()
    design_id = data.get("design_id")
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Wrong password")
    if not design_id:
        raise HTTPException(status_code=400, detail="Missing design_id")

    flagged = load_flagged()
    if design_id not in flagged:
        flagged[design_id] = {"flagged_at": time.time()}
        save_flagged(flagged)

    return {"ok": True}

@app.get("/api/flagged")
async def get_flagged():
    flagged = load_flagged()
    corrections = load_corrections()
    designs = {d["id"]: d for d in load_designs()["designs"]}

    result = []
    for design_id, info in flagged.items():
        d = designs.get(design_id)
        if not d:
            continue
        correction = corrections.get(design_id, {})
        result.append({
            "id": design_id,
            "filename": d.get("filename"),
            "title": d.get("title"),
            "current_category": d.get("category"),
            "suggested_category": correction.get("suggested_category"),
            "flagged_at": info.get("flagged_at"),
        })

    return {"flagged": result, "categories": CATEGORIES}

@app.post("/api/suggest")
async def suggest_correction(request: Request):
    """Claude Code writes its suggested category here after visually inspecting
    a flagged design's image. Not applied until Bruce confirms via /api/correct —
    unauthenticated on purpose, low risk, this only pre-fills the review dropdown."""
    data = await request.json()
    design_id = data.get("design_id")
    category = data.get("category")

    if not design_id or category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Missing design_id or invalid category")

    corrections = load_corrections()
    existing = corrections.get(design_id, {})
    existing["suggested_category"] = category
    corrections[design_id] = existing
    save_corrections(corrections)

    return {"ok": True}

@app.post("/api/correct")
async def correct_design(request: Request):
    data = await request.json()
    design_id = data.get("design_id")
    category = data.get("category")
    password = data.get("password")

    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Wrong password")
    if not design_id or category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Missing design_id or invalid category")

    corrections = load_corrections()
    corrections[design_id] = {"category": category, "confirmed": True}
    save_corrections(corrections)

    flagged = load_flagged()
    if design_id in flagged:
        del flagged[design_id]
        save_flagged(flagged)

    return {"ok": True}

# Static files
app.mount("/thumbs", StaticFiles(directory="thumbs"), name="thumbs")
app.mount("/images", StaticFiles(directory="images"), name="images")
# Serve root-level static files (logo.png, favicon, etc.) — must be last
app.mount("/", StaticFiles(directory=".", html=True), name="root")

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)