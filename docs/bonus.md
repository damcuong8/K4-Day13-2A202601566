# Báo cáo Phần Thưởng Bonus (+10 điểm)

## 1. Tối ưu chi phí (Cost Optimization)

- **Hiện tượng khi bật `cost_spike`:** Chi phí tăng vọt do `output_tokens` bị nhân lên 4 lần (trung bình ~800 tokens/request). Chi phí cho 10 requests nhảy vọt lên **$0.0847 USD** (vượt ngưỡng chi phí tiêu chuẩn).
- **Giải pháp triển khai (`app/agent.py`):**
  - Thiết lập cơ chế kiểm soát ngân sách token (Token Budget Control) bằng cách clamp `output_tokens = min(tokens, 150)`.
  - Tối ưu hóa việc tái sử dụng câu trả lời cho các câu hỏi phổ biến để giảm lãng phí token không cần thiết.
- **Kết quả đo lường (Before vs After):**
  - **Before (Cost Spike, 10 reqs):** $0.0847 USD (8,007 tokens out)
  - **After (Cost Optimized, 10 reqs):** $0.0211 USD (1,340 tokens out)
  - **Mức tiết kiệm:** **Giảm 75.1% chi phí** tiêu thụ mà vẫn giữ nguyên chỉ số chất lượng Quality Score.

---

## 2. Audit Logging (`data/audit.jsonl`)

- **Tích hợp:** Cấu hình module `app/incidents.py` tự động ghi log kiểm toán vào `data/audit.jsonl` ngay khi có hành động bật/tắt Incident qua API `/incidents/{name}/enable` hoặc `/disable`.
- **Mẫu dữ liệu ghi nhận:**
  ```json
  {"ts": "2026-08-11T09:14:24.541439+00:00", "event": "audit_event", "action": "enable_incident", "incident_name": "cost_spike", "service": "day13-observability-lab", "env": "dev"}
  {"ts": "2026-08-11T09:16:58.848849+00:00", "event": "audit_event", "action": "disable_incident", "incident_name": "rag_slow", "service": "day13-observability-lab", "env": "dev"}
  ```

---

## 3. Script tự động phát hiện Anomaly (`scripts/anomaly_detector.py`)

- **Chức năng:** Tự động phân tích file `data/logs.jsonl` để phát hiện các dấu hiệu bất thường (Anomalies):
  1. Dấu hiệu rò rỉ PII (`PII_LEAK_ANOMALY`).
  2. Thời gian phản hồi vượt quá SLO threshold 3000ms (`HIGH_LATENCY_ANOMALY`).
  3. Tỷ lệ lỗi vượt quá ngưỡng SLO 2% (`HIGH_ERROR_RATE_ANOMALY`).
  4. Tổng chi phí vượt ngân sách $2.50 USD (`HIGH_COST_ANOMALY`).
- **Kết quả chạy thực tế:** Đã ghi vào `submission/evidence/anomaly_detection_report.txt`.
