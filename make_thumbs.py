#!/usr/bin/env python3
"""
Generate optimized thumbnails for Moodhu Designs.
- Card thumbnails: 240px wide, WebP, ≤40KB
- Lightbox previews: 1200px wide, WebP, ≤1MB
"""
import os
from PIL import Image

# Config
IMG_DIR = 'images'
THUMB_DIR = 'thumbs'
CARD_WIDTH = 240
LIGHTBOX_WIDTH = 1200
QUALITY = 85

os.makedirs(THUMB_DIR, exist_ok=True)

files = [f for f in os.listdir(IMG_DIR) if os.path.isfile(os.path.join(IMG_DIR, f))]
total = len(files)
print(f"Generating {total} thumbnails...")

for i, filename in enumerate(files):
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        continue
    
    try:
        # Card thumbnail (240px)
        img = Image.open(os.path.join(IMG_DIR, filename))
        ratio = img.height / img.width
        card_height = int(CARD_WIDTH * ratio)
        
        card_thumb = img.resize((CARD_WIDTH, card_height), Image.Resampling.LANCZOS)
        card_thumb.save(
            os.path.join(THUMB_DIR, filename),
            'WEBP',
            quality=QUALITY,
            method=6
        )
        
        # Lightbox preview (1200px)
        lightbox_height = int(LIGHTBOX_WIDTH * ratio)
        lightbox_thumb = img.resize((LIGHTBOX_WIDTH, lightbox_height), Image.Resampling.LANCZOS)
        lightbox_thumb.save(
            os.path.join(IMG_DIR, filename),
            'WEBP',
            quality=QUALITY,
            method=6
        )
        
        if i % 20 == 0:
            print(f"  {i+1}/{total}...", end='\r', flush=True)
            
    except Exception as e:
        print(f"Error processing {filename}: {e}")

print(f"\nDone! Generated {total} thumbnails.")