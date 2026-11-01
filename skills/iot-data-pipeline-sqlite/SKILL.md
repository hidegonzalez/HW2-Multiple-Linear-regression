---
name: iot-data-pipeline-sqlite
description: >-
  Automated ingestion, parsing, transformation, and SQLite persistence for IoT and Open Data feeds.
  Includes Python 3.13+ SSL X509 strict validation adapter workarounds, multi-dataset 404 fallback routing,
  multi-interval aggregation (e.g. 12-hour day/night segments to daily aggregates to regional averages),
  and resilient parameterized SQLite storage with cold-start self-healing pipelines.
  Use this skill when building IoT data ingest pipelines, meteorological or sensor ETL workflows,
  or local embedded databases for desktop and web dashboards.
---

# IoT 與開放資料自動化 ETL 管道與 SQLite 持久化架構 (IoT Data Pipeline & SQLite)

本技能提煉自中央氣象署（CWA）氣象大數據擷取與嵌入式資料庫系統開發實戰，涵蓋從網路憑證問題排查、非同步容錯擷取、複雜階層 JSON 轉換聚合到 SQLite 輕量化持久化的完整架構。

---

## 🏗️ 1. 端到端資料管道架構 (End-to-End Pipeline)

```
[外部 IoT 感測源 / CWA 開放平台 API]
       │ (HTTP GET with Auth Header)
       ▼
1. 擷取層 (fetch_weather.py)
   - 憑證適配器 (CWAAdapter: 排除 Python 3.13+ SSL 阻斷)
   - 404 容錯回退 (Primary Dataset -> Fallback Dataset)
   - 原始資料落盤快照 (weather_raw.json)
       │
       ▼
2. 轉換與彙總層 (parse_weather.py)
   - 時間區段分組 (12小時日夜切分)
   - 極值篩選 (過濾殘缺時段，保留完整 7 天)
   - 區域空間階層聚合 (22 縣市對應六大地理分區取平均)
       │
       ▼
3. 持久化與檢驗層 (database.py)
   - 表格建立與 UNIQUE 複合約束
   - 交易防護 (Transaction Atomic Write)
   - 資料量驗證與完整性測試 (COUNT == 42)
       │
       ▼
[前端應用消費層 (Streamlit / FastAPI / Web)]
   - 冷啟動自愈檢查 (Cold-Start Auto DB Regeneration)
```

---

## 🔒 2. Python 3.13+ 官方憑證嚴格驗證阻斷修復 (SSL Adapter)

### 問題背景：
自 Python 3.13 起，底層 OpenSSL 預設開啟 `VERIFY_X509_STRICT` 旗標。台灣政府開放資料平台（如 CWA、政府資料開放平臺）部分憑證因缺少 X.509 `Subject Key Identifier (SKI)` 延伸欄位，會直接拋出 `SSLError: certificate verify failed`。若盲目使用 `verify=False`，會產生安全漏洞與警報警告。

### 標準解法：自訂 Requests `HTTPAdapter`
僅關閉 `VERIFY_X509_STRICT`，同時完整保留 CA 根憑證驗證與鏈結檢查：

```python
import ssl
import requests
from requests.adapters import HTTPAdapter

class OpenDataSSLAdapter(HTTPAdapter):
    """修復政府開放資料缺少 Subject Key Identifier 之 SSL 檢查問題"""
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        # 僅關閉 X509 嚴格旗標，憑證權威驗證依然完整開啟
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)

def create_secure_session() -> requests.Session:
    session = requests.Session()
    session.mount("https://", OpenDataSSLAdapter())
    return session
```

---

## 🔄 3. 雙資料集容錯回退策略 (Failover Fallback)

外部 API 隨時可能下線、變更端點或遭遇 404。建構高可用資料管道必須包含自動回退邏輯：

```python
import os
import requests

PRIMARY_ENDPOINT = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-A0010-001"
FALLBACK_ENDPOINT = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091"

def fetch_with_fallback(session: requests.Session, api_key: str) -> dict:
    headers = {"Authorization": api_key}
    
    # 嘗試主端點
    try:
        resp = session.get(PRIMARY_ENDPOINT, headers=headers, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        print(f"⚠️ 主端點回傳 HTTP {resp.status_code}，啟動備用資料集回退...")
    except Exception as e:
        print(f"⚠️ 主端點連線異常: {e}，啟動備用端點...")

    # 備用端點
    resp_fallback = session.get(FALLBACK_ENDPOINT, headers=headers, timeout=20)
    resp_fallback.raise_for_status()
    return resp_fallback.json()
```

---

## 📐 4. 時間區段與地理階層聚合演算法 (ETL Transformation)

氣象預報通常每 12 小時一個預報時段（06-18 白天、18-06 夜間）。需要將非對齊的時間序列重整為「日」與「行政分區」：

```python
from collections import defaultdict

# 區域映射表
REGION_MAPPING = {
    "北部地區": ["基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣"],
    "中部地區": ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    "南部地區": ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"],
    "東北部地區": ["宜蘭縣"],
    "東部地區": ["花蓮縣"],
    "東南部地區": ["臺東縣"],
}
COUNTY_TO_REGION = {c: r for r, cs in REGION_MAPPING.items() for c in cs}

def extract_valid_daily_temperatures(location_data: dict) -> dict:
    """提取白晝+夜晚雙時段皆完整之每日 (min_t, max_t)"""
    mint_buckets, maxt_buckets = defaultdict(list), defaultdict(list)
    
    for element in location_data.get("WeatherElement", []):
        elem_name = element.get("ElementName")
        if elem_name not in ("最低溫度", "最高溫度"):
            continue
            
        for period in element.get("Time", []):
            date_str = period["StartTime"][:10]
            val = float(period["ElementValue"][0][list(period["ElementValue"][0].keys())[0]])
            if elem_name == "最低溫度":
                mint_buckets[date_str].append(val)
            else:
                maxt_buckets[date_str].append(val)

    # 僅保留包含 2 個時段以上之完整日期
    valid_daily = {}
    for d in mint_buckets:
        if len(mint_buckets[d]) >= 2 and len(maxt_buckets.get(d, [])) >= 2:
            valid_daily[d] = (min(mint_buckets[d]), max(maxt_buckets[d]))
    return valid_daily
```

---

## 💾 5. SQLite 嵌入式資料庫設計最佳實踐

### 表格架構規範：
1. **複合主鍵約束 (UNIQUE Constraint)**：避免排程抓取時造成重複紀錄。
2. **參數化查詢 (Parameterized Queries)**：杜絕 SQL Injection 風險。
3. **整批交易提交 (Transactional Execution)**：提昇寫入效能十倍以上。

```python
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    mint REAL NOT NULL,
    maxt REAL NOT NULL,
    updatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(regionName, dataDate)
);
CREATE INDEX IF NOT EXISTS idx_region_date ON TemperatureForecasts(regionName, dataDate);
"""

def init_database(db_path: str = "data.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn

def bulk_insert_forecasts(conn: sqlite3.Connection, records: list):
    """
    records: list of tuples -> (regionName, dataDate, mint, maxt)
    使用 INSERT OR REPLACE 達成無痛冪等更新 (Idempotent)
    """
    sql = """
    INSERT OR REPLACE INTO TemperatureForecasts (regionName, dataDate, mint, maxt)
    VALUES (?, ?, ?, ?);
    """
    with conn:
        conn.executemany(sql, records)
```

---

## 🛡️ 6. 應用層冷啟動自愈機制 (Self-Healing Cold Start)

在部署至雲端無狀態容器（如 Render、Streamlit Cloud）或第一次 Git Clone 時，本地 `.db` 通常被 `.gitignore` 排除。在 App 入口加上自動偵測與管道執行邏輯：

```python
import os

DB_FILE = "data.db"

def ensure_database_ready():
    """若資料庫不存在或資料為空，自動召喚 ETL 管道重新生成"""
    need_regenerate = False
    
    if not os.path.exists(DB_FILE):
        need_regenerate = True
    else:
        # 驗證筆數是否充足
        try:
            with sqlite3.connect(DB_FILE) as conn:
                count = conn.execute("SELECT COUNT(*) FROM TemperatureForecasts").fetchone()[0]
                if count == 0:
                    need_regenerate = True
        except Exception:
            need_regenerate = True

    if need_regenerate:
        print("⚡ 偵測到資料庫未就緒，執行自動補償 ETL 管道...")
        # 調用模組生成資料庫
        import fetch_weather
        import parse_weather
        import database
        
        fetch_weather.main()
        parse_weather.parse_weather()
        conn = database.init_db()
        database.populate_db(conn)
        conn.close()
        print("✅ 自愈完成，資料庫已成功初始化！")
```
