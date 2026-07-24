"""
批次壓縮 Moodhu-Designs 作品集圖片 → WebP
- 最大寬度 1200px
- 品質 80
- 輸出到 images/ 資料夾
- 產生 designs.json
"""
import os, json, hashlib
from pathlib import Path
from PIL import Image

SRC = Path(r"E:\BaiduSyncdisk\Moodhu-Designs")
DST = Path(r"E:\BaiduSyncdisk\Moodhu-Designs-Web")
IMG_OUT = DST / "images"
MAX_W = 1200
QUALITY = 80
ADMIN_PASSWORD = "moodhu2024"  # 管理員密碼，可自行修改

os.makedirs(IMG_OUT, exist_ok=True)

extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
designs = []
seen_hashes = set()
total_in = 0
total_out_size = 0

for fpath in sorted(SRC.rglob("*")):
    if fpath.suffix.lower() not in extensions:
        continue
    # 跳過隱藏檔
    if fpath.name.startswith("."):
        continue

    total_in += 1
    rel = fpath.relative_to(SRC)
    category = str(rel.parent)
    if category == ".":
        category = "Uncategorized"

    # 讀取圖片
    try:
        img = Image.open(fpath).convert("RGB")
    except Exception as e:
        print(f"  ⚠ 略過 {fpath.name}: {e}")
        continue

    # 去重：計算內容 hash
    img_bytes = img.tobytes()
    h = hashlib.md5(img_bytes).hexdigest()
    if h in seen_hashes:
        print(f"  ⚠ 重複跳過: {fpath.name}")
        continue
    seen_hashes.add(h)

    # 縮放 (保持比例)
    w, h_orig = img.size
    if w > MAX_W:
        ratio = MAX_W / w
        img = img.resize((MAX_W, int(h_orig * ratio)), Image.LANCZOS)

    # 存成 WebP
    stem = fpath.stem
    # 清理檔名（避免特殊字元問題）
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in stem)
    out_name = f"{safe_name}.webp"
    out_path = IMG_OUT / out_name

    img.save(out_path, "WEBP", quality=QUALITY, method=6)
    size_kb = round(os.path.getsize(out_path) / 1024, 1)
    total_out_size += os.path.getsize(out_path)

    # 收集 metadata
    designs.append({
        "id": safe_name,
        "filename": out_name,
        "title": stem,
        "category": category,
        "width": img.width,
        "height": img.height,
        "size_kb": size_kb,
        "original": fpath.name,
    })
    print(f"  ✓ {fpath.name} → {out_name} ({w}×{h_orig} → {img.width}×{img.height}, {size_kb}KB)")

# 寫入 designs.json
data = {
    "designs": designs,
    "total": len(designs),
    "admin_password": ADMIN_PASSWORD,
}
json_path = DST / "designs.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

total_in_mb = sum(f.stat().st_size for f in SRC.rglob("*") if f.suffix.lower() in extensions) / 1024 / 1024
total_out_mb = total_out_size / 1024 / 1024
ratio = (1 - total_out_mb / total_in_mb) * 100 if total_in_mb > 0 else 0

print(f"\n{'='*50}")
print(f"✅ 完成！")
print(f"   原始檔案: {total_in} 張 / {total_in_mb:.1f}MB")
print(f"   壓縮輸出: {len(designs)} 張 (去重後) / {total_out_mb:.1f}MB")
print(f"   壓縮率: {ratio:.1f}%")
print(f"   設計稿 JSON: {json_path}")
