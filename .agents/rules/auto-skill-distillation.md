# 自律型專案技能沉澱準則 (Auto-Skill Distillation Principle)

## 📌 核心指導原則

在任何專案的開發、架構設計或疑難排解過程中，AI 助手必須具備高度的**「架構復用與知識沉澱敏銳度」**，主動將有價值的實踐轉化為可重複調用的常用技能：

1. **主動識別通用模式 (Proactive Recognition)**：
   - 當實作出高價值、跨專案通用的前端視覺系統（如毛玻璃、SVG 三角動畫、Web Audio 原生合成）。
   - 當建立穩健的 IoT / 開放資料 ETL 管道、嵌入式資料庫快取架構。
   - 當設計複雜的機器學習 / 強化學習演算法（如 DQN、PER、推薦系統 MDP）。
   - 當排查並解決了棘手的底層系統或雲端部署問題（如 Python 3.13+ SSL 阻斷、GitHub Pages 權限衝突等）。

2. **標準化技能封裝 (Standardized Packaging)**：
   - 技能檔案一律命名為 `SKILL.md`，且必須包含完整的 YAML Frontmatter：
     - `name`: 具體且符合規範的短橫線命名。
     - `description`: 明確說明何時調用、解決什麼問題與包含的核心技術。
   - 內文必須結構化提供：
     - 系統架構圖 (Mermaid)。
     - 生產級可直接複製執行的程式碼範例與核心公式。
     - 完整除錯排查決策樹與驗證清單。

3. **多層級同步保存與即時引用 (Multi-Tier Sync & Reference)**：
   - 同步存放至：
     - 專案目錄：`skills/<skill-name>/SKILL.md` 與 `.agents/skills/<skill-name>/SKILL.md`。
     - 上層課程目錄：`../skills/<skill-name>/SKILL.md`。
     - 全域使用者設定：`~/.gemini/config/skills/<skill-name>/SKILL.md`。
   - 在後續所有新專案中，當遇到相關需求或技術難點時，**主動調用並引用既有技能庫**，實現工程能力的持續自我進化與加速開發。
