#!/usr/bin/env python3
"""Generate 360px-wide WebP thumbnails for the gallery."""
import os
from PIL import Image

img_dir = 'images'
thumb_dir = 'thumbs'
os.makedirs(thumb_dir, exist_ok=True)

files = [f for f in os.listdir(img_dir) if f.endswith('.webp')]
total = len(files)
print(f"Processing {total} images...")

for i, fname in enumerate(sorted(files)):
    src = os.path.join(img_dir, fname)
    dst = os.path.join(thumb_dir, fname)
    if os.path.exists(dst):
        continue
    try:
        img = Image.open(src)
        w, h = img.size
        if w > 360:
            new_w = 360
            new_h = int(h * 360 / w)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        img.save(dst, 'webp', quality=75)
        src_sz = os.path.getsize(src)
        dst_sz = os.path.getsize(dst)
        pct = (1 - dst_sz/src_sz) * 100
        print(f"  [{i+1}/{total}] {fname}: {src_sz//1024}KB -> {dst_sz//1024}KB ({pct:.0f}% smaller)")
    except Exception as e:
        print(f"  [!] {fname}: {e}")

# Stats
total_src = sum(os.path.getsize(os.path.join(img_dir,f)) for f in files)
total_dst = sum(os.path.getsize(os.path.join(thumb_dir,f)) for f in files if os.path.exists(os.path.join(thumb_dir,f)))
print(f"\n{'='*40}")
print(f"Original total: {total_src/1024/1024:.1f} MB")
print(f"Thumb total:   {total_dst/1024/1024:.1f} MB")
print(f"Reduced by:    {(1-total_dst/total_src)*100:.0f}%")
