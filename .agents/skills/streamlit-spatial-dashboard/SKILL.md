---
name: streamlit-spatial-dashboard
description: >-
  Architecting interactive IoT and geospatial analytics dashboards with Streamlit, Altair charting,
  Folium map rendering, and resilient micro-frontend component embedding.
  Use this skill when building Python-based data applications that combine relational SQL queries,
  interactive time-series line/bar graphs, geographical spatial pinpoints, and hybrid frontend integrations.
---

# Streamlit 地理空間與 IoT 數據視覺化儀表板架構 (Streamlit Spatial Dashboard)

本技能總結自氣象預報系統、IoT 感測網儀表板與複合式 Web 架構開發，提供結合 **Streamlit**、**SQLite 參數化查詢**、**Altair 時間序列互動圖表**、**Folium 地理空間地圖** 以及 **微前端（Micro-Frontend）平滑降級嵌入** 的黃金組合。

---

## 🧭 1. 系統視覺與互動架構 (System Architecture)

```
[使用者操作：下拉選單 / 日期選取 / 區域切換]
                     │
                     ▼
  ┌─────────────────────────────────────────────────────────┐
  │                 Streamlit 響應式中樞                    │
  ├────────────────────────────┬────────────────────────────┤
  │ 1. 關聯式 SQL 查詢層       │ 2. Altair 互動圖表層       │
  │    (SQLite + @st.cache)    │    (Min/Max 氣溫波動走勢)  │
  ├────────────────────────────┼────────────────────────────┤
  │ 3. Folium 地理地圖層       │ 4. 混合微前端 Iframe 嵌入  │
  │    (各區座標點位/熱力 Badge)│    (Windy / React 動態圖層)│
  └────────────────────────────┴────────────────────────────┘
```

---

## ⚡ 2. SQLite 參數化查詢與 Streamlit 智慧快取

避免在 Web 回調中重複建立資料庫連線或讀取全量 CSV，透過 `@st.cache_data` 實現高效快取：

```python
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "data.db"

@st.cache_data(ttl=600)  # 快取 10 分鐘，過期自動刷新
def query_region_forecast(region_name: str) -> pd.DataFrame:
    """使用 SQL 參數化查詢指定區域之一週預報"""
    query = """
    SELECT dataDate, mint, maxt
    FROM TemperatureForecasts
    WHERE regionName = ?
    ORDER BY dataDate ASC
    LIMIT 7;
    """
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn, params=(region_name,))
    
    # 計算平均溫
    df["avg_temp"] = ((df["mint"] + df["maxt"]) / 2).round(1)
    return df
```

---

## 📈 3. Altair 多指標時間序列視覺化 (Time-Series Charting)

使用 Altair 繪製自適應寬度、具備平滑色彩標註與 Tooltip 的雙折線圖：

```python
import altair as alt

def render_temperature_chart(df: pd.DataFrame, region_title: str):
    st.subheader(f"📊 {region_title} — 未來 7 日氣溫走勢")
    
    # 將資料轉為長格式 (Long-format) 供 Altair 繪製雙折線
    chart_df = df.melt(
        id_vars=["dataDate"],
        value_vars=["maxt", "mint"],
        var_name="指標",
        value_name="溫度"
    )
    chart_df["指標"] = chart_df["指標"].map({"maxt": "最高溫 (°C)", "mint": "最低溫 (°C)"})

    line_chart = (
        alt.Chart(chart_df)
        .mark_line(point=True)
        .encode(
            x=alt.X("dataDate:N", title="預報日期"),
            y=alt.Y("溫度:Q", title="氣溫 (°C)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "指標:N",
                scale=alt.Scale(domain=["最高溫 (°C)", "最低溫 (°C)"], range=["#ef4444", "#3b82f6"])
            ),
            tooltip=["dataDate", "指標", "溫度"]
        )
        .properties(height=320)
        .interactive()
    )
    st.altair_chart(line_chart, use_container_width=True)
```

---

## 🗺️ 4. Folium 地理標記與動態 HTML 徽章渲染

利用 Folium 在 Leaflet 底圖上依據氣候指標動態繪製地圖標記（DivIcon 或 Marker）：

```python
import folium
from streamlit_folium import st_folium

# 台灣地理分區中心點座標
REGION_COORDS = {
    "北部地區": (25.03, 121.56),
    "中部地區": (24.15, 120.67),
    "南部地區": (22.99, 120.21),
    "東北部地區": (24.75, 121.75),
    "東部地區": (23.98, 121.60),
    "東南部地區": (22.79, 121.07),
}

def render_taiwan_map(region_avg_temps: dict, selected_region: str):
    # 建立地圖中心點
    center = REGION_COORDS.get(selected_region, (23.7, 121.0))
    m = folium.Map(location=[center[0], center[1]], zoom_start=8, tiles="CartoDB dark_matter")

    for region, (lat, lon) in REGION_COORDS.items():
        avg_t = region_avg_temps.get(region, 25.0)
        
        # 依溫度決定標記顏色
        color = "#ef4444" if avg_t >= 28 else "#3b82f6" if avg_t <= 20 else "#10b981"
        is_selected = (region == selected_region)

        # 建立 HTML 氣溫圓標
        html_marker = f"""
        <div style="
            background: {color};
            color: white;
            font-weight: bold;
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 12px;
            border: {'2px solid #fbbf24' if is_selected else '1px solid rgba(255,255,255,0.4)'};
            box-shadow: 0 2px 8px rgba(0,0,0,0.5);
            white-space: nowrap;
        ">
            {region}: {avg_t}°C
        </div>
        """
        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(html=html_marker),
            popup=f"{region} 均溫 {avg_t}°C"
        ).add_to(m)

    st_folium(m, height=400, use_container_width=True)
```

---

## 🧩 5. 混合微前端平滑降級整合 (Graceful Micro-Frontend Embedding)

當專案需要嵌入外部 React/Vite/Windy 動態儀表板（例如 Port 5173）時，若外部伺服器未啟動，必須**自動偵測並平滑隱藏/降級**，絕對不可產生白色死頁或 Connection Refused 報錯：

```python
import socket
import streamlit.components.v1 as components

def is_service_alive(host: str = "localhost", port: int = 5173, timeout: float = 0.5) -> bool:
    """快速偵測本地或遠端微前端通訊埠是否就緒"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def render_optional_micro_frontend(selected_region: str):
    HOST, PORT = "localhost", 5173
    
    if is_service_alive(HOST, PORT):
        st.caption("🌐 連線正常：正在顯示 Windy 動態風場微前端圖層")
        embed_url = f"http://{HOST}:{PORT}/?region={selected_region}"
        components.iframe(embed_url, height=450, scrolling=False)
    else:
        # 平滑降級：不噴錯，僅收攏或提示
        st.info("💡 提示：進階 Windy 動態圖層（Port 5173）未啟動，目前以標準 Folium 地圖呈現。")
```
