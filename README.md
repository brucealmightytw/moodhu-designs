# Moodhu Maldives Design Gallery

投票畫庮部署於 Zeabur。

## 本地開發
```bash
npm install
npm run dev
```

## 部署
連接 GitHub repo 到 Zeabur、自動偶掉 Node.js 專案。

## 目錄結構
- `server.js` - Express + SQLite 後端
- `public/` - 前端静態檔案
- `images/` - WebP 圖片 (gitignore、部署時自動生成或預先放置)
- `catalog.json` - 設計目錄資料
