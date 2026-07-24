# 🦈 Moodhu Designs 投票網站

你的海洋設計作品集投票網站！朋友可以上線看作品、按 👍/👎 投票，還有即時統計排名。

## ✨ 功能

- 🖼️ **完整作品集** — 143 張壓縮 WebP 圖，載入超快
- 👍/👎 **喜歡 / 不喜歡** — 每人每件作品可投一次，可改票
- 📊 **即時統計** — 總票數、投票人數、最受歡迎作品
- 🏷️ **分類過濾** — 按魚種分類瀏覽
- 🗑️ **管理刪除** — 密碼保護的刪除功能，移除錯誤作品
- 📱 **手機友善** — RWD 響應式設計

## 🚀 部署方式（二選一）

### 選項 A：Zeabur（推薦，已訂閱）

1. **將整個資料夾推送到 GitHub**

```bash
cd /e/BaiduSyncdisk/Moodhu-Designs-Web
git init
git add .
git commit -m "🎨 Moodhu Designs voting site"
# 在 GitHub 建立一個新 repo 後：
git remote add origin https://github.com/你的帳號/moodhu-designs.git
git push -u origin main
```

2. **在 Zeabur 部署**
   - 登入 [Zeabur](https://zeabur.com)
   - 點 **New Project** → **Deploy from GitHub**
   - 選擇剛推送的 repo
   - Zeabur 會自動偵測 Python，安裝依賴並啟動
   - 部署完成後會給你一個 `https://xxx.zeabur.app` 網址

3. **自訂網域**（選擇性）
   - 在 Zeabur 專案設定中綁定你自己的網域

### 選項 B：本機測試

```bash
cd /e/BaiduSyncdisk/Moodhu-Designs-Web
pip install -r requirements.txt
python app.py
```

打開瀏覽器前往 `http://localhost:8000`

## 🔑 管理員密碼

- 預設密碼：`moodhu2024`
- 若要修改，請編輯 `app.py` 中的 `ADMIN_PASSWORD` 變數

## 🗂️ 專案結構

```
Moodhu-Designs-Web/
├── index.html        # 投票頁面（前端）
├── app.py            # FastAPI 後端（API + 靜態檔服務）
├── designs.json      # 作品 metadata
├── requirements.txt  # Python 依賴
├── zeabur.json       # Zeabur 部署設定
├── .gitignore
├── images/           # 壓縮後的 WebP 圖片（143 張）
│   ├── Clownfish-AfremovOil.webp
│   ├── MantaRay-KlimtArtNouveau.webp
│   └── ...
└── README.md         # 本文件
```

## 📊 資料儲存

後端使用 JSON 檔案儲存在 `data/` 資料夾：
- `data/votes.json` — 所有投票記錄（依投票者 ID 分組）
- `data/designs.json` — 作品資料（含刪除標記）

Zeabur 部署時這些檔案會存在伺服器磁碟中。
