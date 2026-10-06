# 築跡 Studio Notes

AI Coding 第 2 章作業 1：以 Next.js 建立「建築學生作品與學習紀錄」網站。

## 技術與功能

- Next.js 16 App Router、React 19、TypeScript、Tailwind CSS 4。
- 響應式首頁、六件示範作品、分類與關鍵字搜尋。
- 原生 dialog 作品介紹、鍵盤 Escape 關閉、Local Storage 收藏。
- 建築學習資源連結、原創本地 SVG 示意圖。
- 無登入、資料庫或後端 API。示範作品不代表作者實際完成的建築設計。

## 開發

需要 Node.js 20.9 以上版本，建議 Node.js 24 LTS。

```bash
npm ci
npm run dev
```

以瀏覽器開啟開發伺服器顯示的位址。正式建置：

```bash
npm run lint
npm run build
npm run start
```

## 瀏覽器測試

先用 `npm run start` 啟動已建置網站，再開另一個終端機。

雲端環境已有 `/usr/bin/chromium`：

```bash
npm run test:e2e
```

其他電腦請先安裝 Playwright 瀏覽器，再指定路徑：

```bash
npx playwright install chromium
```

將 `CHROMIUM_PATH` 設為所安裝的 Chromium 執行檔路徑再執行測試。Windows 可改為本機 Chrome 執行檔；使用 PowerShell 的 `$env:CHROMIUM_PATH` 設定環境變數。

測試輸出及截圖會寫入專案上一層的「驗證資料」。若要測試已部署網站，可設定 `TEST_BASE_URL` 為真正的公開網址。

## 更換成你的作品

1. 在 `src/app/page.tsx` 的 `projects` 陣列替換名稱、年份、介紹、學習過程與工具。
2. 在 `public/images` 放入你有使用權的圖片。若用 JPG/PNG，將圖片路徑改為對應副檔名。
3. 更新品牌、關於本站文字與示範提示。只有換入真實作品後才移除示範標示。
4. 若新增或刪除作品，同步更新既有測試的數量與名稱。

## 部署

GitHub 作業分支：`ai-coding-assignment-1`。

GitHub 倉庫根目錄中的網站路徑：`AI_Coding_作業一/architecture-portfolio`。

可直接在此網站目錄執行：

```bash
npx vercel login
npx vercel --prod
```

登入由你在 Vercel 完成；不要將 Token 提交至 Git 或貼在聊天裡。框架選 Next.js，工作目錄保持目前網站目錄。詳細操作見上一層 `01_一步一步操作說明.md`。

已完成匿名臨時部署，2026-10-06 17:24（台北時間）到期。需使用者認領或正式部署以永久保存。公開匿名瀏覽仍受雲端網路代理阻擋，尚未驗證；請確認無痕可瀏覽後才填寫繳交網址。
