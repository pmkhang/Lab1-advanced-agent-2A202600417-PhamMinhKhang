# Tasks — Lab 16: Reflexion Agent

## Core (80 điểm)

### 1. Định nghĩa Schemas (`src/reflexion_lab/schemas.py`)
- [x] Hoàn thiện `JudgeResult`: thêm các trường `score: int`, `reason: str`, và các trường tùy chọn như `missing_evidence`, `spurious_claims`
- [x] Hoàn thiện `ReflectionEntry`: thêm các trường `attempt_id: int`, `failure_reason: str`, `lesson: str`, `next_strategy: str`

### 2. Viết System Prompts (`src/reflexion_lab/prompts.py`)
- [x] `ACTOR_SYSTEM`: hướng dẫn Actor đọc context, thực hiện multi-hop reasoning, trả lời ngắn gọn
- [x] `EVALUATOR_SYSTEM`: yêu cầu trả về JSON `{"score": 0|1, "reason": "..."}`, so sánh với gold answer
- [x] `REFLECTOR_SYSTEM`: phân tích lỗi từ attempt trước, đề xuất chiến thuật mới cho lần sau

### 3. Thay thế Mock bằng LLM thật (`src/reflexion_lab/mock_runtime.py` hoặc file mới)
- [x] Gọi LLM thật (Ollama / vLLM / OpenAI / Gemini) trong `actor_answer`
- [x] Gọi LLM thật trong `evaluator`, parse JSON response thành `JudgeResult`
- [x] Gọi LLM thật trong `reflector`, trả về `ReflectionEntry`
- [x] Tính `token_estimate` từ response thực tế của API (thay thế công thức ước tính trong `agents.py`)
- [x] Đo `latency_ms` thực tế bằng `time.perf_counter()` (thay thế công thức ước tính trong `agents.py`)

### 4. Hoàn thiện Reflexion loop (`src/reflexion_lab/agents.py`)
- [x] Triển khai phần `TODO` trong `BaseAgent.run()`:
  - Nếu `agent_type == "reflexion"` và chưa đúng và còn attempt: gọi `reflector` → append vào `reflection_memory` và `reflections`

### 5. Chạy Benchmark thực tế
- [x] Chuẩn bị dataset HotpotQA ≥ 100 mẫu (thay `data/hotpot_mini.json` hoặc truyền path mới)
- [x] Chạy: `python run_benchmark.py --dataset <path> --out-dir outputs/real_run`
- [x] Kiểm tra output: `outputs/real_run/report.json` và `report.md` đúng format
- [x] Chạy autograder: `python autograde.py --report-path outputs/real_run/report.json`

### 6. Hoàn thiện Report
- [x] `report.json` có đủ 6 keys: `meta`, `summary`, `failure_modes`, `examples`, `extensions`, `discussion`
- [x] `meta.num_records >= 100`
- [x] `examples` có ít nhất 20 mục
- [x] `failure_modes` có ít nhất 3 loại
- [x] `discussion` dài ít nhất 250 ký tự (phân tích so sánh ReAct vs Reflexion)

---

## Bonus (tối đa 20 điểm — mỗi extension 10 điểm, tối đa 2)

Thêm tên extension vào `extensions` trong `report.json` để được tính điểm.

| Extension key | Mô tả |
|---|---|
| `structured_evaluator` | Evaluator trả về JSON có cấu trúc, dùng Pydantic để parse và validate |
| `reflection_memory` | Lưu và truyền toàn bộ lịch sử reflection vào prompt Actor ở các lần sau |
| `adaptive_max_attempts` | Tự động điều chỉnh `max_attempts` dựa trên độ khó của câu hỏi |
| `memory_compression` | Nén/tóm tắt reflection_memory khi quá dài trước khi đưa vào prompt |
| `mini_lats_branching` | Sinh nhiều candidate answer mỗi attempt, chọn cái tốt nhất |
| `plan_then_execute` | Actor sinh plan trước, sau đó execute từng bước |
| `benchmark_report_json` | Xuất thêm file JSONL chi tiết từng attempt cho mỗi câu hỏi |
| `mock_mode_for_autograding` | Giữ lại mock mode, có thể switch bằng flag để autograder chạy offline |
