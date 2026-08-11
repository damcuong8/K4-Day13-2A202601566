# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL: https://github.com/damcuong8/K4-Day13-2A202601566
- Commit SHA cuối: a8f907f (Logging & PII — commit local, cần cập nhật lại sau khi cả nhóm hoàn thành và push bản cuối)
- Thành viên và vai trò:
  - Lý Nhật Huy (2A202601450) — Logging & PII: correlation ID, metadata, JSON log, redaction

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (xem [evidence/validate_logs_output.txt](evidence/validate_logs_output.txt))
- Tổng số traces:
- Số PII leak còn lại: 0 (0 records trên tổng 21 log analyzed)
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID: mỗi request sinh `correlation_id` dạng `req-<8-hex>` (mới hoặc lấy từ header `x-request-id` nếu client gửi sẵn), bind vào `structlog` contextvars nên mọi log dòng của cùng request đều mang chung ID; ID cũng được trả về qua response header `x-request-id` + `x-response-time-ms`. Xem [evidence/correlation_id_headers.txt](evidence/correlation_id_headers.txt) và [evidence/sample_logs_correlation_and_pii.jsonl](evidence/sample_logs_correlation_and_pii.jsonl).
- Evidence PII redaction: input test chứa email và số điện thoại VN bị thay bằng `[REDACTED_EMAIL]`/`[REDACTED_PHONE_VN]` trước khi ghi log; bổ sung thêm pattern `passport_vn` và `address_vn`. Kiểm chứng độc lập bằng `scripts/validate_logs.py` cho `Potential PII leaks detected: 0`. Xem [evidence/pii_redaction_before_after.md](evidence/pii_redaction_before_after.md).
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: `HỢP LỆ: 6/6 panel có trong dashboard contract.` (xem [evidence/validate_dashboard_output.txt](evidence/validate_dashboard_output.txt) và [evidence/dashboard_and_alerts.md](evidence/dashboard_and_alerts.md)).
- Evidence dashboard: Đã cấu hình đủ 6 panel theo contract `config/dashboard.yaml` gồm Latency (P50/P95/P99), Request Traffic, Error Rate & Breakdown, Cost over time, Input/Output Tokens và Quality Proxy score.
- SLO đã chọn và lý do:
  1. **Latency SLO (P95 <= 3000ms):** Đảm bảo thời gian phản hồi nhanh cho người dùng khi chat với AI.
  2. **Availability SLO (Error Rate <= 2%):** Đảm bảo tính ổn định và sẵn sàng của hệ thống API.
  3. **Quality SLO (Mean Quality Score >= 0.75):** Đảm bảo độ chính xác và giá trị thực tiễn của câu trả lời do AI tạo ra.
- Alert rules và runbook: Đã thiết lập 3 Alert Rules kèm Runbook chi tiết trong [docs/alerts.md](file:///d:/AI_thuc_chien/K4-Day13-2A202601566/docs/alerts.md) gồm: High Latency Warning, High Error Rate Critical và High Cost & Token Consumption Warning.

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Lý Nhật Huy (2A202601450) | Logging & PII: sinh/propagate correlation ID qua middleware (`app/middleware.py`), enrich log với `user_id_hash`, `session_id`, `feature`, `model`, `env` (`app/main.py`), đăng ký processor scrub PII trước khi ghi log (`app/logging_config.py`), mở rộng `PII_PATTERNS` với `passport_vn`/`address_vn` và test tương ứng (`app/pii.py`, `tests/test_pii.py`) | `a8f907f` — https://github.com/damcuong8/K4-Day13-2A202601566/commit/a8f907f (link hoạt động sau khi `git push`) | Thứ tự processor của `structlog` quyết định dữ liệu có bị lộ hay không (phải scrub trước khi render JSON và ghi file); dùng `contextvars` để một correlation ID theo suốt vòng đời request mà không cần truyền tay qua từng hàm; cách kiểm chứng PII độc lập với chính implementation của mình bằng bộ regex riêng trong `validate_logs.py`. |
| Thành viên C (Metrics & Alerting) | Dashboard, SLO & Alerting: Kiểm tra dashboard contract `config/dashboard.yaml` đạt `6/6 panel` với `validate_dashboard.py`, định nghĩa Latency/Availability/Quality SLOs và soạn thảo 3 Alert Rules kèm Runbook cho hệ thống trong `docs/alerts.md` | PR / Commit local — https://github.com/damcuong8/K4-Day13-2A202601566 | Hiểu cách liên kết từ Dashboard Metrics tới Traces và Logs; cách xác định các chỉ số SLOs (P95 latency, Error rate %, Quality score) thực tế cho hệ thống AI LLM và xây dựng Runbook ứng phó sự cố theo 3 bước điều tra tiêu chuẩn. |

