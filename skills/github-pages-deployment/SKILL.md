---
name: github-pages-deployment
description: >-
  Troubleshooting, configuring, and verifying GitHub Pages deployments for static websites (HTML/CSS/JS, Single-Page Apps).
  Use this skill whenever setting up GitHub Pages, fixing 'HttpError: Resource not accessible by integration' or 'Get Pages site failed',
  resolving 404 Not Found errors on *.github.io, configuring .nojekyll, avoiding conflicting Actions workflows, or choosing between 'Deploy from a branch' vs 'GitHub Actions'.
---

# GitHub Pages 部署除錯與最佳實踐技能 (GitHub Pages Deployment Runbook)

本技能提供靜態網站（HTML、CSS、JS、Single-Page Apps）部署至 GitHub Pages 的標準SOP、除錯決策樹與常見地雷排除指南。

---

## ⚡ 核心原則：兩種部署模式的黃金選擇

GitHub Pages 目前支援兩種構建來源（Source）：

| 構建來源 (Source) | 適用場景 | 是否需要 Actions 腳本 | 設定方式 | 常見地雷 |
| :--- | :--- | :---: | :--- | :--- |
| **A. Deploy from a branch**<br/>**(原生分支直出模式，推薦)** | 純前端靜態網頁 (`index.html` 位於根目錄或 `/docs`) | ❌ **不需要**<br/>(嚴禁放 `pages.yml`) | Settings ➔ Pages ➔ Source 選 `Deploy from a branch` ➔ Branch 選 `main` / `(root)` | 忘記放 `.nojekyll` 導致 Jekyll 忽略特殊檔案，或殘留 Actions 腳本導致衝突報錯。 |
| **B. GitHub Actions**<br/>**(工作流程構建模式)** | 需要預編譯構建的專案 (Vite, React, Vue, Next.js SSG) | ✅ **需要**<br/>(`.github/workflows/pages.yml`) | Settings ➔ Pages ➔ Source 必須先手動切換為 `GitHub Actions` | 倉庫未手動開啟 Pages 權限時，Action 會噴出 `Resource not accessible by integration`。 |

> 💡 **專家法則**：對於一般的 HTML/CSS/JS 網頁專案（如課程作業、Portfolio、Dashboard），**一律優先採用模式 A (Deploy from a branch)**，架構最單純、速度最快、零維護成本！

---

## 🛠️ 故障排查決策樹 (Troubleshooting Decision Tree)

### 故障 1：GitHub Actions 出現 `HttpError: Resource not accessible by integration`
- **症狀**：
  推送代碼後，GitHub Actions 頁面顯示紅叉 ❌，錯誤日誌為：
  `Create Pages site failed. Error: Resource not accessible by integration`
- **根本原因**：
  GitHub 官方安全策略：**禁止預設的 `GITHUB_TOKEN` 在後台自動為尚未啟用 Pages 的倉庫開通網站**。
- **解決方案（二選一）**：
  1. **方案一（切換為分支原生部署，最徹底）**：
     - 刪除倉庫中的 `.github/workflows/pages.yml`（避免每次 push 都觸發失敗的工作流程）。
     - 前往 `Settings -> Pages -> Source` 選擇 **`Deploy from a branch`**，Branch 選 **`main`**，目錄選 **`/ (root)`** ➔ 點擊 **Save**。
  2. **方案二（堅持使用 GitHub Actions）**：
     - 前往 `Settings -> Pages -> Source`，在下拉選單中將 Source 切換為 **`GitHub Actions`**。
     - 回到 Actions 頁面點擊 **`Re-run all jobs`**。

---

### 故障 2：訪問 `https://<username>.github.io/<repo>/` 出現 404 Not Found
- **症狀**：
  倉庫已經推播，且 Settings 顯示正在構建，但開啟網址卻顯示 404。
- **檢查清單**：
  1. **檢查建置延遲**：
     - 第一次啟用 GitHub Pages 通常需要 **60~120 秒** 佇列構建。請勿立刻判定失敗，稍等 1~2 分鐘後重新整理。
  2. **檢查根目錄入口檔案**：
     - 根目錄必須有名為 `index.html`（全小寫）的主入口檔案，大小寫不符（如 `Index.html`）在 Linux 伺服器會引發 404。
  3. **檢查倉庫公開性 (Public vs Private)**：
     - 免費用戶的 GitHub Pages 僅支援 **Public 公開倉庫**；若設為 Private，需要 GitHub Pro / Enterprise。
  4. **檢查 `.nojekyll` 檔案**：
     - 根目錄是否有建立空白的 `.nojekyll` 檔案。

---

### 故障 3：Jekyll 預設過濾導致 CSS、JS 或子目錄檔案遺失
- **症狀**：
  HTML 頁面正常打開，但樣式跑版、圖片不見、或特定下劃線目錄（如 `_data/`, `_static/`）裡的檔案 404。
- **根本原因**：
  GitHub Pages 預設使用 Jekyll 靜態站點生成器，Jekyll 會自動忽略所有以底線 `_` 或點 `.` 開頭的目錄，並將 `{{ ... }}` 視為 Liquid 模板語法。
- **解法**：
  在倉庫根目錄建立一個**完全空白**的 `.nojekyll` 檔案：
  ```bash
  touch .nojekyll
  git add .nojekyll
  git commit -m "feat: add .nojekyll to disable Jekyll processing"
  git push origin main
  ```

---

## 📋 靜態網站 30 秒標準部署 SOP

日後若有任何靜態網站需要部署至 GitHub Pages，請嚴格執行以下 4 步：

1. **確認檔案結構**：
   ```text
   repo_root/
   ├── index.html        # 必須全小寫
   ├── style.css
   ├── app.js
   └── .nojekyll         # 必備：繞過 Jekyll 預編譯
   ```
2. **清除衝突的 Actions 腳本**：
   確保 `.github/workflows/` 下**沒有**未經授權的 `pages.yml`。
3. **推播至 GitHub**：
   ```bash
   git add .
   git commit -m "deploy: update static site"
   git push origin main
   ```
4. **開啟 GitHub Pages 開關**：
   瀏覽器開啟：`https://github.com/<username>/<repo>/settings/pages`
   - **Source**：選 **`Deploy from a branch`**
   - **Branch**：選 **`main`**，資料夾保持 **`/ (root)`**
   - 點擊 **Save**。
5. **驗證上線**：
   等候 30~60 秒，訪問：`https://<username>.github.io/<repo>/`。

---

## 🔍 自動驗證腳本 (Verification Script)

在終端機中可直接執行 Python 測試網站健康度：

```python
import urllib.request
import sys

url = "https://<username>.github.io/<repo>/"
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status == 200:
            print(f"✅ GitHub Pages 成功上線！狀態碼: {resp.status}")
        else:
            print(f"⚠️ 異常狀態碼: {resp.status}")
except Exception as e:
    print(f"❌ 網站尚未就緒或發生錯誤: {e}")
```
