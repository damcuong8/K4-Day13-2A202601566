# Evidence: Dashboard, SLO và Alert Rules (Thành viên C)

## 1. Kết quả kiểm tra Dashboard Contract

Lệnh kiểm tra:
```bash
python scripts/validate_dashboard.py
```

Kết quả:
```text
HỢP LỆ: 6/6 panel có trong dashboard contract.
```

---

## 2. Chi tiết 6 Panel Dashboard theo Contract `config/dashboard.yaml`

| ID Panel | Tên Panel | Event/Field | Phép tổng hợp | Đơn vị | Ngưỡng (Threshold) |
|---|---|---|---|---|---|
| `latency` | Latency percentiles | `response_sent.latency_ms` | P50, P95, P99 | ms | P95 <= 3000ms |
| `traffic` | Request traffic | `request_received` | count, rate_per_minute | requests_per_minute | Rate >= 1 req/min |
| `errors` | Error rate and breakdown | `request_received`, `request_failed` | error_rate_pct, count_by_value | percent (%) | error_rate_pct <= 2% |
| `cost` | Cost over time | `response_sent.cost_usd` | sum_by_minute, total | usd ($) | Total <= $2.5 USD |
| `tokens` | Input and output tokens | `response_sent.tokens_in/tokens_out` | sum_by_field | tokens | Total <= 50,000 tokens |
| `quality` | Quality proxy | `response_sent.quality_score` | mean | score (0..1) | Mean >= 0.75 |

---

## 3. Định nghĩa SLO (Service Level Objectives)

1. **Latency SLO:** 95% request có thời gian phản hồi $ \le 3000\text{ ms} $ trong cửa sổ 60 phút.
   - *Lý do:* Giữ trải nghiệm phản hồi mượt mà cho người dùng khi tương tác với AI chatbot.
2. **Availability / Error Rate SLO:** Tỷ lệ lỗi $ \text{error\_rate\_pct} \le 2\% $ trong cửa sổ 60 phút.
   - *Lý do:* Đảm bảo tính sẵn sàng cao của hệ thống API, tránh việc gián đoạn dịch vụ do lỗi server 500.
3. **Quality SLO:** Điểm chất lượng trung bình $ \text{quality\_score} \ge 0.75 $ trong cửa sổ 60 phút.
   - *Lý do:* Đảm bảo câu trả lời từ AI đáp ứng độ chính xác và hữu ích cho người dùng.

---

## 4. Alert Rules và Runbook

### Alert 1: High Latency Warning
- **Severity:** Warning
- **SLI/SLO liên quan:** Latency SLO (P95 latency <= 3000ms)
- **Điều kiện & Thời gian duy trì:** `p95(latency_ms) > 3000ms` duy trì liên tục trong 3 phút.
- **Ảnh hưởng tới người dùng:** Trải nghiệm phản hồi chậm, thời gian chờ tin nhắn chatbot bị kéo dài.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở Dashboard xem panel **Latency** & **Traffic** để kiểm tra có đợt tăng đột biến lưu lượng (traffic spike) không.
  2. Mở Langfuse tìm các trace có `latency_ms > 3000` để xác định span gây chậm (RAG retrieval, LLM call, hay tool execution).
  3. Lọc log trong `data/logs.jsonl` theo `correlation_id` của các trace bị chậm để tìm nguyên nhân cụ thể.
- **Mitigation tạm thời:**
  - Nếu RAG chậm: Giảm số lượng tài liệu tham khảo (`top_k`) hoặc kích hoạt caching.
  - Nếu LLM API chậm: Chuyển sang fallback model hoặc giảm `max_tokens`.
- **Owner:** Member C / On-call Engineer

### Alert 2: High Error Rate Critical
- **Severity:** Critical
- **SLI/SLO liên quan:** Availability SLO (Error rate <= 2%)
- **Điều kiện & Thời gian duy trì:** `error_rate_pct > 2%` duy trì liên tục trong 2 phút.
- **Ảnh hưởng tới người dùng:** Người dùng bị lỗi HTTP 500, không nhận được câu trả lời từ AI.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở Panel **Errors** trên Dashboard để xem phân bố loại lỗi (`error_type`).
  2. Tìm các log có event `request_failed` trong `data/logs.jsonl` để đọc thông báo exception chi tiết.
  3. Truy vết theo `correlation_id` trên Langfuse để xem span nào bị ngắt/crash.
- **Mitigation tạm thời:**
  - Nếu hết quota / lỗi LLM provider: Bật circuit breaker hoặc chuyển provider dự phòng.
  - Nếu do payload xấu / lỗi code: Áp dụng input validation hoặc rollback code về phiên bản gần nhất.
- **Owner:** Member C / On-call Engineer

### Alert 3: High Cost & Token Consumption Warning
- **Severity:** Warning
- **SLI/SLO liên quan:** Cost & Token SLO (Cost <= $2.5 USD, Tokens <= 50,000 trong 60 phút)
- **Điều kiện & Thời gian duy trì:** `total(cost_usd) > 2.5` hoặc `total(tokens) > 50000` trong cửa sổ 60 phút.
- **Ảnh hưởng tới người dùng:** Chi phí vận hành tăng vọt, nguy cơ cạn ngân sách làm dừng dịch vụ.
- **Ba bước kiểm tra đầu tiên:**
  1. Xem panel **Cost** và **Tokens** trên Dashboard để xác định mốc thời gian tiêu tốn token bất thường.
  2. Kiểm tra log lọc theo `user_id_hash` và `feature` xem có người dùng hoặc tính năng nào lạm dụng API không.
  3. Mở Langfuse kiểm tra prompt/input của các request dùng token lớn.
- **Mitigation tạm thời:**
  - Áp dụng Rate limiting / Quota limit theo `user_id_hash`.
  - Cắt giảm độ dài prompt/context hoặc bật tính năng tóm tắt tự động context.
- **Owner:** Member C / Ops Team
