---
name: vanilla-web-design-system
description: >-
  Architecting zero-dependency, ultra-lightweight Vanilla Web applications with modern CSS theming,
  glassmorphism effects, SVG trigonometric progress indicators, requestAnimationFrame clock engines,
  Web Audio API sound synthesizers, and resilient localStorage single-state trees.
  Use this skill when building high-performance frontend dashboards, portals, interactive visualizers,
  or browser-based utilities without Node.js, React/Vue, bundlers, or third-party CSS frameworks.
---

# 零依賴原生 Web 設計系統與動態互動架構 (Vanilla Web Design System)

本技能總結自現代高階 Web 原生開發實踐（如 AIoT 個人入口儀表板與動態時鐘專案），提供一套**零框架、零建構依賴（Zero-Dependency Vanilla Stack）**的現代前端架構準則與核心模組。

---

## ⚡ 核心哲學：為什麼選擇原生 Vanilla Stack？

在許多 AIoT 儀表板、邊緣設備管理介面、個人入口或展示型專案中，引入 React/Vue/Vite/Webpack 往往帶來過度的打包複雜度、肥大的 `node_modules` 與跨版本構建損壞風險。

**Vanilla Stack 的核心優勢**：
1. **即開即用**：無需 `npm install`、`npm run build`，任何靜態伺服器（甚至雙擊 `index.html` 或 GitHub Pages）皆能 100% 執行。
2. **極致效能**：首次載入無任何框架 Overhead（體積通常 < 50KB），首屏繪製 (FCP) 幾乎等於網路傳輸時間。
3. **底層透明性**：直接操作 DOM、CSSOM、SVG 與 Web Audio API，對瀏覽器渲染管線擁有絕對控制權。

---

## 🎨 1. CSS Custom Properties 宣告式多主題系統

使用原生 CSS 變數在 `:root` 與 `body[data-theme="..."]` 上進行樣式映射，達成**零 JavaScript 樣式計算**的主題切換。

```css
/* ==========================================================================
   主題變數定義 (CSS Custom Properties)
   ========================================================================== */
:root {
  --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --bg-base: #080b13;
  --bg-card: rgba(18, 24, 42, 0.72);
  --border-card: rgba(255, 255, 255, 0.12);
  --accent-cyan: #06b6d4;
  --orb-1: #4f46e5;
  --orb-2: #06b6d4;
  --orb-3: #8b5cf6;
}

/* 簡約白/黑主題 (Minimal) */
body[data-theme="minimal"] {
  --bg-base: #0f1117;
  --bg-card: rgba(26, 31, 44, 0.82);
  --border-card: rgba(255, 255, 255, 0.08);
  --accent-cyan: #e2e8f0;
  --orb-1: #2a313d;
  --orb-2: #1e293b;
  --orb-3: #334155;
}

/* 暮光暖色主題 (Sunset) */
body[data-theme="sunset"] {
  --bg-base: #120914;
  --bg-card: rgba(38, 18, 42, 0.75);
  --border-card: rgba(244, 63, 94, 0.2);
  --accent-cyan: #fb7185;
  --orb-1: #be123c;
  --orb-2: #fb923c;
  --orb-3: #a21caf;
}
```

**JavaScript 切換機制**（僅需變更屬性，GPU 自動重繪）：
```javascript
function applyTheme(themeName) {
  document.body.setAttribute('data-theme', themeName);
}
```

---

## 🔮 2. 現代科技感 Glassmorphism（三層層疊架構）

實現頂級深邃毛玻璃質感的黃金三層結構：

```
Layer 3 (頂層): .glass-card       → backdrop-filter: blur(24px) saturate(160%)
Layer 2 (中層): .grid-overlay     → 40×40px 半透明網格線，提供空間座標感
Layer 1 (底層): .ambient-glow     → 3 個彩色光球，filter: blur(120px) 緩慢流動
```

```css
/* 1. 底層光球漫射 */
.ambient-glow {
  position: fixed;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.45;
  animation: float 20s ease-in-out infinite alternate;
}
.orb-1 { width: 500px; height: 500px; background: var(--orb-1); top: -10%; left: -10%; }
.orb-2 { width: 450px; height: 450px; background: var(--orb-2); bottom: -10%; right: -5%; }

/* 2. 中層幾何網格 */
.grid-overlay {
  position: fixed;
  inset: 0;
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 1;
}

/* 3. 前景毛玻璃卡片 */
.glass-card {
  position: relative;
  z-index: 2;
  background: var(--bg-card);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid var(--border-card);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border-radius: 20px;
}
```

---

## ⏱️ 3. SVG 同心圓向量進度環（三角幾何數學）

在不使用 Chart.js 或 D3 的前提下，利用 SVG `<circle>` 達成無極平滑圓環進度：

$$C = 2 \pi r \approx 2 \times 3.14159265 \times 162 \approx 1017.88$$

```html
<svg class="progress-ring" viewBox="0 0 360 360">
  <!-- 底層軌道 -->
  <circle class="ring-track" cx="180" cy="180" r="162" />
  <!-- 動態前景進度環 -->
  <circle class="ring-indicator" id="progressIndicator" cx="180" cy="180" r="162" />
</svg>
```

```css
.ring-track {
  fill: none;
  stroke: rgba(255, 255, 255, 0.05);
  stroke-width: 4;
}
.ring-indicator {
  fill: none;
  stroke: var(--accent-cyan);
  stroke-width: 4;
  stroke-linecap: round;
  stroke-dasharray: 1017.88;
  stroke-dashoffset: 1017.88;
  transform: rotate(-90deg); /* 從正上方 12 點鐘方向起始 */
  transform-origin: 50% 50%;
  transition: stroke-dashoffset 0.08s linear;
}
```

**更新偏移量公式**：
```javascript
const RADIUS = 162;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS; // ≈ 1017.876

function updateProgressRing(fraction) {
  // fraction 介於 0.0 到 1.0
  const offset = CIRCUMFERENCE - (fraction * CIRCUMFERENCE);
  const ring = document.getElementById('progressIndicator');
  if (ring) {
    ring.style.strokeDashoffset = offset;
  }
}
```

---

## 🚀 4. requestAnimationFrame 高精度時鐘引擎

相較於 `setInterval` 會因為 JavaScript 事件迴圈阻塞而產生時間漂移（Drift），`requestAnimationFrame` 與螢幕硬體垂直同步刷新（VSync, 60~144Hz），並在瀏覽器切換分頁時**自動暫停**，節省 CPU/電池資源。

```javascript
let animId = null;

function clockEngine() {
  const now = new Date();
  
  // 取得毫秒級平滑秒數
  const ms = now.getMilliseconds();
  const sec = now.getSeconds();
  const smoothSeconds = sec + (ms / 1000);
  
  // 更新 60 秒進度環
  updateProgressRing(smoothSeconds / 60);

  // 更新數位時間顯示
  const timeStr = now.toTimeString().substring(0, 8);
  const timeElem = document.getElementById('digitalClock');
  if (timeElem && timeElem.textContent !== timeStr) {
    timeElem.textContent = timeStr;
  }

  // 遞迴請求下一幀
  animId = requestAnimationFrame(clockEngine);
}

// 啟動引擎
requestAnimationFrame(clockEngine);
```

---

## 🔊 5. Web Audio API 原生音訊合成器（零外部 MP3 音效）

透過瀏覽器原生的 `AudioContext`、`OscillatorNode` 與 `GainNode` 指數衰減包絡線，合成清脆細緻的機械點擊或提示音：

```javascript
class SyntheticAudioEngine {
  constructor() {
    this.ctx = null;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    // 現代瀏覽器需要使用者互動後 resume 音訊上下文
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  // 合成清脆機械短音 (Mechanical Transient Click)
  playMechanicalTick() {
    if (!this.ctx || this.ctx.state !== 'running') return;

    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      // 頻率瞬態：從 1400Hz 快速跌落至 300Hz (0.025 秒)
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1400, now);
      osc.frequency.exponentialRampToValueAtTime(300, now + 0.025);

      // 音量包絡：極短的衰減 (Exponential Decay)
      gain.gain.setValueAtTime(0.05, now);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.025);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 0.025);
    } catch (e) {
      console.warn('Audio tick synthesis skipped:', e);
    }
  }
}

const audio = new SyntheticAudioEngine();
// 在任一按鈕點擊事件中初始化：
document.addEventListener('click', () => audio.init(), { once: true });
```

---

## 💾 6. 單一狀態樹 (Single State Tree) 與 localStorage 彈性合併

避免散落各處的 `localStorage.getItem`，採用統一的 State 管理並運用物件展開運算子保證向下相容：

```javascript
const STORAGE_KEY = 'portal_state_v1';

const defaultState = {
  theme: 'aurora',
  format24h: true,
  soundEnabled: false,
  zenMode: false,
  userName: 'JasonChen'
};

// 讀取：預設值與持久化儲存物件合併 (Merge)
function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...defaultState, ...JSON.parse(raw) } : { ...defaultState };
  } catch (e) {
    console.error('State load error, fallback to default:', e);
    return { ...defaultState };
  }
}

let appState = loadState();

// 寫入：集中序列化
function saveState(newState) {
  appState = { ...appState, ...newState };
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(appState));
  } catch (e) {
    console.error('State save error:', e);
  }
}
```

---

## 🗂️ 7. 非同步資料與視圖解耦 (Data-View Separation)

不要在 HTML 內寫死專案列表或感測節點。將資料收斂為靜態 JSON，使用現代 Template Literals 動態插入 DOM：

```javascript
async function loadAndRenderCards(jsonUrl = './projects.json') {
  const container = document.getElementById('cardGrid');
  try {
    const resp = await fetch(jsonUrl);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    container.innerHTML = data.map(item => `
      <div class="glass-card card-item">
        <div class="card-header">
          <span class="status-indicator active"></span>
          <h3 class="card-title">${item.title}</h3>
        </div>
        <p class="card-desc">${item.description}</p>
        <div class="tag-row">
          ${item.tags.map(t => `<span class="badge">${t}</span>`).join('')}
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="error-msg">⚠️ 資料載入失敗: ${err.message}</div>`;
  }
}
```

---

## 📋 總結：適用此技能的專案特徵
- 需要打造高質感、深色科技風格、具儀表板屬性的入口網站或監控網頁。
- 不希望背負龐大的 Node 環境、React/Vue 依賴與 npm 漏洞審查。
- 專案需要長久穩定維護、隨處靜態分發（如 GitHub Pages、嵌入式裝置 HTTP 伺服器）。
