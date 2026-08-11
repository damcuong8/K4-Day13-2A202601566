# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: High Latency Warning (P95 Latency > 3000ms)
- Severity: Warning
- SLI/SLO liên quan: Latency SLO (P95 latency <= 3000ms trong 60 phút)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` duy trì liên tục trong 3 phút.
- Ảnh hưởng tới người dùng: Trải nghiệm phản hồi chậm, thời gian chờ tin nhắn chatbot bị kéo dài.
- Ba bước kiểm tra đầu tiên:
  1. Mở Dashboard xem panel Latency & Traffic để kiểm tra có đợt tăng đột biến lưu lượng (traffic spike) không.
  2. Mở Langfuse tìm các trace có `latency_ms > 3000` để xác định span gây chậm (RAG retrieval, LLM call, hay tool execution).
  3. Lọc log trong `data/logs.jsonl` theo `correlation_id` của các trace bị chậm để tìm nguyên nhân cụ thể.
- Mitigation tạm thời:
  - Nếu RAG chậm: Giảm số lượng tài liệu tham khảo (`top_k`) hoặc kích hoạt caching.
  - Nếu LLM API chậm: Chuyển sang fallback model hoặc giảm `max_tokens`.
- Owner: Thành viên C / On-call Engineer

## Alert 2

- Tên: High Error Rate Critical (Error Rate > 2%)
- Severity: Critical
- SLI/SLO liên quan: Availability SLO (Error rate <= 2% trong 60 phút)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` duy trì liên tục trong 2 phút.
- Ảnh hưởng tới người dùng: Người dùng bị lỗi HTTP 500, không nhận được câu trả lời từ AI.
- Ba bước kiểm tra đầu tiên:
  1. Mở Panel Errors trên Dashboard để xem phân bố loại lỗi (`error_type`).
  2. Tìm các log có event `request_failed` trong `data/logs.jsonl` để đọc thông báo exception chi tiết.
  3. Truy vết theo `correlation_id` trên Langfuse để xem span nào bị ngắt/crash.
- Mitigation tạm thời:
  - Nếu hết quota / lỗi LLM provider: Bật circuit breaker hoặc chuyển provider dự phòng.
  - Nếu do payload xấu / lỗi code: Áp dụng input validation hoặc rollback code về phiên bản gần nhất.
- Owner: Thành viên C / On-call Engineer

## Alert 3

- Tên: High Cost & Token Consumption Warning
- Severity: Warning
- SLI/SLO liên quan: Cost & Token SLO (Cost <= $2.5 USD, Tokens <= 50,000 trong 60 phút)
- Điều kiện và thời gian duy trì: `total(cost_usd) > 2.5` hoặc `total(tokens) > 50000` trong cửa sổ 60 phút.
- Ảnh hưởng tới người dùng: Chi phí vận hành tăng vọt, nguy cơ cạn ngân sách làm dừng dịch vụ.
- Ba bước kiểm tra đầu tiên:
  1. Xem panel Cost và Tokens trên Dashboard để xác định mốc thời gian tiêu tốn token bất thường.
  2. Kiểm tra log lọc theo `user_id_hash` và `feature` xem có người dùng hoặc tính năng nào lạm dụng API không.
  3. Mở Langfuse kiểm tra prompt/input của các request dùng token lớn.
- Mitigation tạm thời:
  - Áp dụng Rate limiting / Quota limit theo `user_id_hash`.
  - Cắt giảm độ dài prompt/context hoặc bật tính năng tóm tắt tự động context.
- Owner: Thành viên C / Ops Team

