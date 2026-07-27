import os, json, hashlib, uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# ── 管理員密碼 ──
ADMIN_PASSWORD = "moodhu2024"

# ── 資料庫 (輕量 JSON 檔案，免安裝) ──
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
VOTES_FILE = DATA_DIR / "votes.json"
DESIGNS_FILE = DATA_DIR / "designs.json"
DELETED_IDS_FILE = Path("deleted_ids.json")  # 永久刪除記錄（跨重啟保留）

def load_json(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_deleted_ids():
    """載入永久刪除的 ID 清單"""
    if DELETED_IDS_FILE.exists():
        return set(json.loads(DELETED_IDS_FILE.read_text(encoding="utf-8")))
    return set()

def save_deleted_ids(ids):
    DELETED_IDS_FILE.write_text(
        json.dumps(sorted(list(ids)), ensure_ascii=False), encoding="utf-8"
    )

def init_db():
    """初始化資料庫（僅首次建立，不覆蓋）"""
    deleted_ids = load_deleted_ids()

    # 只有當 data/designs.json 不存在時才從根源目錄建立
    src = Path("designs.json")
    if not DESIGNS_FILE.exists() and src.exists():
        data = json.loads(src.read_text(encoding="utf-8"))
        designs = {}
        for d in data["designs"]:
            # 跳過：參考圖、已永久刪除的
            if d["id"] in deleted_ids:
                continue
            if d.get("category", "").startswith("_reference"):
                continue
            designs[d["id"]] = d
        save_json(DESIGNS_FILE, designs)

    if not VOTES_FILE.exists():
        save_json(VOTES_FILE, {})

def get_designs():
    db = load_json(DESIGNS_FILE)
    return list(db.values())

def get_votes_count():
    """回傳 { design_id: {likes: N, dislikes: N} }"""
    votes_db = load_json(VOTES_FILE)
    counts = {}
    for vid, vlist in votes_db.items():
        for v in vlist:
            did = v["design_id"]
            if did not in counts:
                counts[did] = {"likes": 0, "dislikes": 0}
            key = v["vote_type"] + "s"  # "like" → "likes"
            counts[did][key] += 1
    return counts

def get_voter_votes(voter_id):
    """回傳該投票者的所有投票 { design_id: vote_type }"""
    votes_db = load_json(VOTES_FILE)
    return {v["design_id"]: v["vote_type"] for v in votes_db.get(str(voter_id), [])}

# ── FastAPI App ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI(title="Moodhu Designs API", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── API Models ──
class VoteRequest(BaseModel):
    design_id: str
    vote_type: str  # "like" or "dislike"

class DeleteRequest(BaseModel):
    design_id: str
    password: str

# ── API Routes ──
@app.get("/api/designs")
def api_designs():
    designs = get_designs()
    return {"designs": designs, "total": len(designs)}

@app.get("/api/votes")
def api_votes():
    return get_votes_count()

@app.get("/api/votes/me")
def api_my_votes(voter_id: str = ""):
    if not voter_id:
        return {}
    return get_voter_votes(voter_id)

@app.post("/api/vote")
def api_vote(req: VoteRequest, voter_id: str = ""):
    if not voter_id:
        raise HTTPException(400, "Missing voter_id")
    if req.vote_type not in ("like", "dislike"):
        raise HTTPException(400, "vote_type must be 'like' or 'dislike'")
    
    votes_db = load_json(VOTES_FILE)
    vid = str(voter_id)
    
    if vid not in votes_db:
        votes_db[vid] = []
    
    # 找現有投票
    existing = None
    for v in votes_db[vid]:
        if v["design_id"] == req.design_id:
            existing = v
            break
    
    if existing:
        if existing["vote_type"] == req.vote_type:
            # 取消投票 (toggle off)
            votes_db[vid] = [v for v in votes_db[vid] if v["design_id"] != req.design_id]
            action = "removed"
        else:
            # 改票
            existing["vote_type"] = req.vote_type
            action = "changed"
    else:
        votes_db[vid].append({
            "design_id": req.design_id,
            "vote_type": req.vote_type,
            "created_at": str(uuid.uuid4())
        })
        action = "added"
    
    save_json(VOTES_FILE, votes_db)
    return {"action": action, "votes": get_votes_count(), "my": get_voter_votes(vid)}

@app.post("/api/delete")
def api_delete(req: DeleteRequest):
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(403, "密碼錯誤")
    
    db = load_json(DESIGNS_FILE)
    if req.design_id not in db:
        raise HTTPException(404, "找不到此設計")
    
    # ① 從資料庫完全移除
    del db[req.design_id]
    save_json(DESIGNS_FILE, db)
    
    # ② 記錄到永久刪除清單（跨重啟、跨機器都有效）
    deleted_ids = load_deleted_ids()
    deleted_ids.add(req.design_id)
    save_deleted_ids(deleted_ids)
    
    # ③ 清理該設計的所有投票資料
    votes_db = load_json(VOTES_FILE)
    changed = False
    for vid in list(votes_db.keys()):
        before = len(votes_db[vid])
        votes_db[vid] = [v for v in votes_db[vid] if v["design_id"] != req.design_id]
        if len(votes_db[vid]) != before:
            changed = True
        if not votes_db[vid]:
            del votes_db[vid]
    if changed:
        save_json(VOTES_FILE, votes_db)
    
    return {"ok": True, "message": "已永久刪除"}

@app.get("/api/stats")
def api_stats():
    counts = get_votes_count()
    designs = get_designs()
    
    total_votes = sum(c["likes"] + c["dislikes"] for c in counts.values())
    voter_count = len(load_json(VOTES_FILE))
    
    # 最受歡迎
    best_id = max(counts, key=lambda k: counts[k]["likes"] - counts[k]["dislikes"]) if counts else None
    
    return {
        "total_votes": total_votes,
        "voter_count": voter_count,
        "top_design_id": best_id
    }

# ── 靜態檔案服務 ──
# 掛載 images 資料夾（含快取 headers）
app.mount("/images", StaticFiles(directory="images", check_dir=False), name="images")

# 前端靜態檔 (index.html, designs.json)
@app.get("/")
def serve_index():
    return FileResponse("index.html")

@app.get("/{path:path}")
def serve_static(path: str):
    file = Path(path)
    if file.exists() and file.is_file():
        return FileResponse(str(file))
    return JSONResponse({"error": "Not found"}, status_code=404)

# ── 啟動 ──
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
