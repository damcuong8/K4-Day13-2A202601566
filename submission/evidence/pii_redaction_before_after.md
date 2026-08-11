# PII redaction — before / after

Nguồn input (`data/sample_queries.jsonl`) chứa PII thử nghiệm; log ghi xuống `data/logs.jsonl`
sau khi qua `scrub_event` (app/logging_config.py) và `scrub_text` (app/pii.py) không còn PII thô.

## Case 1 — Email

- Input gốc: `What is your refund policy? My email is student@vinuni.edu.vn`
- Log ghi xuống (`request_received`, correlation_id `req-0e762d6b`):
  `"message_preview": "What is your refund policy? My email is [REDACTED_EMAIL]"`

## Case 2 — Số điện thoại Việt Nam

- Input gốc: `Here is my phone 0987654321, what should be logged?`
- Log ghi xuống (`request_received`, correlation_id `req-edabaa25`):
  `"message_preview": "Here is my phone [REDACTED_PHONE_VN], what should be logged?"`

## Kiểm chứng độc lập

`scripts/validate_logs.py` dò PII bằng bộ regex độc lập với `app/pii.py` (không phụ thuộc
implementation của học viên) trên toàn bộ `data/logs.jsonl`:

```
Potential PII leaks detected: 0
+ [PASSED] PII scrubbing
```

Xem chi tiết đầy đủ trong [`validate_logs_output.txt`](validate_logs_output.txt) và log gốc trong
[`sample_logs_correlation_and_pii.jsonl`](sample_logs_correlation_and_pii.jsonl).

## Ghi chú kỹ thuật

- `app/pii.py`: `PII_PATTERNS` gồm `email`, `phone_vn`, `cccd`, `credit_card`, và bổ sung
  `passport_vn`, `address_vn`.
- `app/logging_config.py`: processor `scrub_event` chạy trước `JsonlFileProcessor`, đảm bảo dữ
  liệu được scrub trước khi ghi xuống file (đúng thứ tự processor).
- Unit test: `tests/test_pii.py` (email, số điện thoại, passport, địa chỉ),
  `tests/test_validate_logs.py` (validator phát hiện PII độc lập).
