---
name: industrial-iot-telemetry-alerting
description: >-
  Architecting industrial IoT telemetry, distributed edge-to-cloud log ingestion, and closed-loop alerting pipelines.
  Includes lightweight edge log shipping (Promtail/Filebeat), Kafka event streaming, dynamic threshold queries
  from MES PostgreSQL databases based on active Work Orders, closed-loop API automated machine interlocking (HOLD/lock),
  and read-write separated time-series visualization (Grafana/Loki).
  Use this skill when designing industrial automated testing stations, manufacturing execution pipelines, or mission-critical IoT alerting.
---

# 工業物聯網產線遙測與閉環智慧預警系統架構 (Industrial IoT Telemetry & Alerting)

本技能提煉自主機板硬體自動化測試與智慧預警系統（Hardware Testing Architecture）專案，涵蓋從**邊緣端測試機台輕量採集**、**分散式事件串流緩衝（Kafka）**、**動態工單容許規格比對**到**呼叫 MES API 進行硬體自動鎖板（Closed-Loop Interlock）**的工業級架構規範。

---

## 🏭 1. 工業物聯網邊緣—中央解耦架構藍圖

在產線（如 SMT、主機板或光模組自動化測試）中，若測試端機台直接負擔複雜資料庫寫入或預警運算，會導致測試週期（Cycle Time）拉長，甚至影響硬體測量精度。

標準解法為採取**前線機台與中央運算分離**及**讀寫分離**的分散式架構：

```text
【前線測試機台群 (Edge)】       【中央訊息與運算神經中樞】             【製造執行與工廠系統 (MES)】
 (CentOS 7 / Win11)
+-----------------------+
| 測試機 A (Filebeat)   |──(JSON)──+
+-----------------------+          │   +------------------+    +------------------------+    +-------------------+
                                   +──►|  Apache Kafka    |───►|  Python 智慧預警大腦   |───►| MES 外部 API      |
+-----------------------+          │   |  (分散式訊息隊列)|    |  (消費者群組 Worker)   |    | (即時扣留/鎖板)   |
| 測試機 B (Filebeat)   |──(JSON)──+   +------------------+    +------------------------+    +-------------------+
+-----------------------+          │             │                         ▲                          │
                                   │             ▼                         │ (依工單動態查詢上下限)   ▼
+-----------------------+          │   +------------------+                │                 +-------------------+
| 測試機 C (Filebeat)   |──(JSON)──+   | Loki / InfluxDB  |                +─────────────────| MES PostgreSQL    |
+-----------------------+              | (時序巨量資料庫) |                                  | (規格主資料庫)    |
                                       +------------------+
                                                 │
                                                 ▼
                                       +------------------+
                                       | Grafana 監控大屏 | ──► QA主管與工程師 (瀏覽器即時看板)
                                       +------------------+
```

---

## 📤 2. 邊緣端輕量化日誌發送規範 (Edge Shipper)

邊緣測試端**嚴禁**直連遠端資料庫。測試腳本僅需輸出標準化結構之本地日誌，由背景常駐的 Shipper 進行零干擾串流：

```json
{
  "timestamp": "2026-06-02T10:15:30.120Z",
  "stationId": "MB-TEST-03",
  "workOrder": "WO-20260602-008",
  "boardSerialNumber": "SN-A94827104",
  "testItem": "VCORE_VOLTAGE_LOAD",
  "measuredValue": 1.285,
  "unit": "V",
  "status": "MEASURED"
}
```

---

## ⚡ 3. Python 預警大腦：動態工單閥值與即時比對

不同生產批次或機型（工單 Work Order）擁有不同的電氣公差。預警服務必須動態讀取 MES 規格，避免寫死門檻：

```python
import json
import psycopg2
from confluent_kafka import Consumer, KafkaError
import requests

class FactoryAlertEngine:
    def __init__(self, pg_config: dict, kafka_conf: dict):
        self.pg_conn = psycopg2.connect(**pg_config)
        self.consumer = Consumer(kafka_conf)
        self.consumer.subscribe(['factory-telemetry'])
        self.threshold_cache = {} # 工單規格快取

    def get_work_order_spec(self, work_order: str, test_item: str) -> dict:
        """動態自 MES 資料庫查詢當前工單容許上下限"""
        cache_key = f"{work_order}:{test_item}"
        if cache_key in self.threshold_cache:
            return self.threshold_cache[cache_key]

        with self.pg_conn.cursor() as cur:
            cur.execute("""
                SELECT min_limit, max_limit 
                FROM mes_work_order_specs 
                WHERE work_order = %s AND test_item = %s;
            """, (work_order, test_item))
            row = cur.fetchone()
            if row:
                spec = {"min": float(row[0]), "max": float(row[1])}
                self.threshold_cache[cache_key] = spec
                return spec
        return None

    def interlock_mes_hold(self, serial_num: str, reason: str):
        """閉環連動：呼叫 MES API 將不良品鎖板，阻止流入下一站"""
        try:
            payload = {
                "serialNumber": serial_num,
                "action": "HOLD",
                "reasonCode": "AUTO_OOS_VOLTAGE",
                "remark": reason
            }
            resp = requests.post("http://mes.factory.internal/api/v1/board/interlock", 
                                 json=payload, timeout=2.0)
            if resp.status_code == 200:
                print(f"🔒 [MES 閉環鎖板成功] 機板 {serial_num} 已自動設為 HOLD！")
            else:
                print(f"⚠️ MES 鎖板回應異常: {resp.status_code}")
        except Exception as e:
            print(f"❌ MES API 呼叫失敗: {e}")

    def run(self):
        print("🚀 預警大腦啟動，監聽 Kafka 事件串流...")
        while True:
            msg = self.consumer.poll(timeout=1.0)
            if msg is None or msg.error():
                continue
                
            data = json.loads(msg.value().decode('utf-8'))
            sn = data['boardSerialNumber']
            wo = data['workOrder']
            item = data['testItem']
            val = data['measuredValue']

            spec = self.get_work_order_spec(wo, item)
            if spec:
                # 判定超出規格 (Out-of-Spec, OOS)
                if val < spec['min'] or val > spec['max']:
                    alarm_msg = f"項目 {item} 測得 {val} 超出閥值 [{spec['min']} ~ {spec['max']}]"
                    print(f"🚨 異常警告: {alarm_msg}")
                    # 1. 觸發即時閉環鎖板
                    self.interlock_mes_hold(sn, alarm_msg)
                    # 2. 觸發郵件/即時通訊告警
                    # self.send_alert_notification(data, alarm_msg)
```

---

## 📊 4. 讀寫分離與 Grafana 監控大屏集成

1. **儲存層分離**：日誌由 Kafka 直轉寫入高寫入吞吐的時序儲存（如 Loki / TimescaleDB），不佔用業務資料庫資源。
2. **重測防呆過濾**：硬體測試常有因接觸不良重測的情況。在 SQL/LogQL 查詢中使用 `ROW_NUMBER() OVER (PARTITION BY boardSerialNumber ORDER BY timestamp DESC)` 確保報表預設僅統計**最新一筆**結果。
3. **管理員維護 UI**：提供專用的手動審核介面，供 QA 工程師複查被自動鎖板的異常單元。
