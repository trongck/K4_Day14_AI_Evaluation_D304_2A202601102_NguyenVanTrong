# BẢN THẢO THUYẾT TRÌNH BÁO CÁO NGHIỆM THU
## ĐỀ TÀI: AI EVALUATION & BENCHMARKING PIPELINE FOR ENTERPRISE RAG SYSTEM

---

### 📋 THÔNG TIN CHUNG
- **Thời lượng thuyết trình đề xuất**: 5 – 7 phút
- **Người thực hiện**: Nguyễn Văn Trọng (Học viên K4)
- **Đối tượng báo cáo**: Hội đồng Đánh giá / Giảng viên môn Thực chiến AI
- **Sản phẩm bàn giao đi kèm**: 
  1. Codebase hoàn thiện `solution/solution.py` (Pass 42/42 Tests)
  2. Bộ dữ liệu chuẩn `golden_dataset.json` (Pass Validator)
  3. Báo cáo phân tích `exercises.md` & `reflection.md`
  4. Web Application Demo: **RAG Evaluation & Diagnostics Portal** (`server.py`)

---

### 🎨 CẤU TRÚC SLIDE & KỊCH BẢN THUYẾT MINH CHI TIẾT

```
+-----------------------------------------------------------------------------------+
| INDEX SLIDE | TIÊU ĐỀ SLIDE                        | THỜI LƯỢNG  |
+-------------+--------------------------------------+-------------+
| Slide 1     | Mở đầu & Tổng quan Dự án            | 0.5 phút    |
| Slide 2     | Đặt vấn đề: Tại sao cần AI Eval?     | 1.0 phút    |
| Slide 3     | Xây dựng Golden Dataset & Metrics    | 1.0 phút    |
| Slide 4     | Kết quả Benchmark & Phân tích 5 Whys | 1.5 phút    |
| Slide 5     | Giải pháp Tối ưu & Bằng chứng        | 1.0 phút    |
| Slide 6     | Bonus Highlights (3.4 & 3.5)         | 0.5 phút    |
| Slide 7     | Demo Web Portal & Kết luận           | 0.5 phút    |
+-----------------------------------------------------------------------------------+
```

---

#### 📍 SLIDE 1: TỔNG QUAN DỰ ÁN & MỤC TIÊU
- **Nội dung Slide**:
  - Tiêu đề: *Xây dựng Khung Đánh giá Khoa học & Benchmarking cho Hệ thống Enterprise RAG (OrbitTech Support)*.
  - Tác giả: Nguyễn Văn Trọng.
  - Mục tiêu cốt lõi: Chuyển dịch từ việc "đánh giá AI bằng cảm tính" sang "đánh giá định lượng có căn cứ khoa học" thông qua bộ 5 chỉ số chuẩn RAGAS và cơ chế phát hiện suy thoái chất lượng tự động.

- **🎙️ Kịch bản Lời nói (Speaker Script)**:
  > *"Kính chào Thầy/Cô và các bạn. Hôm nay em xin đại diện báo cáo đề tài **AI Evaluation & Benchmarking Pipeline** dành cho hệ thống Trợ lý ảo Hỗ trợ Khách hàng OrbitTech.*
  > 
  > *Trong thực tế triển khai RAG, một câu trả lời 'nghe có vẻ hay' chưa chắc đã đúng. Để đưa AI vào sản xuất thương mại, chúng ta cần một thước đo khoa học, đo lường chính xác từ khâu Retrieval đến khâu Generation. Đề tài của em tập trung giải quyết trọn vẹn bài toán này."*

---

#### 📍 SLIDE 2: ĐẶT VẤN ĐỀ & BỘ DỮ LIỆU CHUẨN (GOLDEN DATASET)
- **Nội dung Slide**:
  - **Đặt vấn đề**: RAG thường gặp 4 loại thất bại phổ biến: *Hallucination (Thêm thắt thông tin), Off-topic (Lạc đề), Data Leakage (Rò rỉ metadata hệ thống), và Insufficient Retrieval Recall*.
  - **Golden Dataset (20 QA Pairs)**: Được thiết kế theo phương pháp Phân tầng (Stratified Sampling):
    - 🟢 **5 Easy**: Các câu hỏi tra cứu thông tin đơn giản (Giá membership, thời gian giao hàng).
    - 🟡 **7 Medium**: Các câu hỏi ghép nối đa điều kiện (Quy trình đổi trả, ngoại lệ bảo hành).
    - 🔴 **5 Hard**: Các câu hỏi đa bước xử lý (Tính thời gian đổi trả theo phiên bản policy, điều kiện trả góp OrbitPay).
    - ⚠️ **3 Adversarial**: Các câu hỏi bẫy (Prompt Injection, Giả định sai - False Premise, Câu hỏi ngoài phạm vi - Out of scope).

- **🎙️ Kịch bản Lời nói (Speaker Script)**:
  > *"Để đánh giá khách quan, em đã thiết kế bộ **Golden Dataset 20 QA Pairs** phân tầng từ Dễ đến Khó và có cả các trường hợp Tấn công/Bẫy (Adversarial).*
  > 
  > *Toàn bộ dữ liệu được chuẩn hóa tiếng Anh để đảm bảo tính Provenance và đo lường overlap chính xác ở mức độ từ vựng. Dataset đã vượt qua bài test kiểm định `validate_golden_dataset.py` với 100% tài liệu nguồn được phủ đủ."*

---

#### 📍 SLIDE 3: BỘ KHUNG ĐÁNH GIÁ 5 METRICS & THỰC NGHIỆM BENCHMARK
- **Nội dung Slide**:
  - **Bộ 5 Metrics chuẩn RAGAS**:
    1. `Context Recall`: Khâu Retrieval lấy đủ bằng chứng chưa?
    2. `Context Precision`: Bằng chứng đúng nhất có nằm ở vị trí ưu tiên (Top 1, Top 2) không?
    3. `Faithfulness`: Câu trả lời có bám sát 100% context không? (Cấm bịa).
    4. `Relevance`: Câu trả lời có đi thẳng vào trọng tâm câu hỏi không?
    5. `Completeness`: Trả lời có phủ hết các điều kiện của đáp án mẫu không?
  - **Kết quả Benchmark ban đầu**: Overall Pass Rate đạt **45.0%** (9/20 passed).
  - **Top 3 Failure Cases**: `A01` (Score 0.347 - Irrelevant), `A03` (Score 0.353 - Hallucination), `H05` (Score 0.433 - Off-topic).

- **🎙️ Kịch bản Lời nói (Speaker Script)**:
  > *"Em sử dụng bộ 5 chỉ số RAGAS để cắt lớp hệ thống. Kết quả benchmark ban đầu ghi nhận Pass Rate đạt 45.0%.*
  > 
  > *Nhìn vào bảng chỉ số, ta thấy khâu **Retrieval** hoạt động rất tốt với Precision đạt 91.3% và Recall đạt 87.7%. Tuy nhiên điểm số bị kéo xuống ở khâu **Generation** với Faithfulness chỉ đạt 57.5% và Relevance đạt 56.7%. Lý do là LLM có bản năng 'nói nhiều' và tự ý thêm thắt các lời khuyên không nằm trong context."*

---

#### 📍 SLIDE 4: PHÂN TÍCH 5 WHYS & GIẢI PHÁP TỐI ƯU CÓ BẰNG CHỨNG
- **Nội dung Slide**:
  - **Phân tích 5 Whys case M04**: Điểm Context Recall ban đầu chỉ đạt 0.292 do BM25 `top_k=5` bị sót chunk loại trừ bảo hành trong `06_warranty_policy.md`.
  - **Giải pháp tối ưu thực nghiệm (Không hardcode công thức chấm)**:
    1. **Nâng `top_k` từ 5 lên 7**: Kiểm chứng trực tiếp bằng BM25 thật, lôi thành công chunk bị thiếu $\rightarrow$ Tăng Context Recall lên **1.000**.
    2. **Thiết lập 7 Quy tắc Hệ thống (System Prompt Rules)**: Ép mở đầu bằng chủ thể câu hỏi, cấm tiệt các từ rác như "context", "Context 2", cấm rò rỉ tên file `.md`, cấm đưa ra lời khuyên ngoài.
    3. **Tăng `max_output_tokens` lên 400**: Tránh bị cắt cụt câu trả lời dài.

- **🎙️ Kịch bản Lời nói (Speaker Script)**:
  > *"Bằng phương pháp 5 Whys, em đã tìm ra nguyên nhân tận gốc ở 2 tầng:*
  > 
  > *Ở tầng Retrieval: Với câu hỏi M04 về bảo hành AeroBuds Pro, cấu hình `top_k=5` đã bỏ sót đoạn thông tin quan trọng. Em đã tiến hành kiểm chứng thực nghiệm bằng việc nâng `top_k=7`, giúp BM25 lấy đúng chunk bị thiếu và đưa Context Recall của M04 lên tuyệt đối 1.0.*
  > 
  > *Ở tầng Generation: Em bổ sung 7 quy tắc thiết kế Prompt nghiêm ngặt để triệt tiêu các từ rác nội bộ (như chữ 'context' hay tên file '.md') khiến LLM không còn bị trừ điểm Faithfulness oan."*

---

#### 📍 SLIDE 5: ĐIỂM SÁNG BONUS (EXERCISE 3.4 & 3.5 - +15 ĐIỂM)
- **Nội dung Slide**:
  - **Exercise 3.4 (+10 pt) - So sánh RAGAS vs. TruLens**:
    - RAGAS: Khắt khe hơn, chạy offline nhanh, tối ưu làm Quality Gate trong CI/CD.
    - TruLens: Trực quan, chạy LLM-as-a-judge, phù hợp làm Dashboard tracking trên Production.
  - **Exercise 3.5 (+5 pt) - Reranking (`rerank_by_overlap()`)**:
    - Kết quả thực nghiệm trên 5 traces: `Context Precision` tăng từ **0.796 $\rightarrow$ 0.913 (+0.117)**.
    - `Context Recall` giữ nguyên tuyệt đối (0.664 $\rightarrow$ 0.664) $\rightarrow$ Chứng minh reranking chỉ thay đổi thứ tự ưu tiên (ranking) mà không ảnh hưởng đến tập tài liệu hợp (union coverage).

- **🎙️ Kịch bản Lời nói (Speaker Script)**:
  > *"Em cũng đã hoàn thành trọn vẹn 2 bài tập Bonus (+15 điểm):*
  > 
  > *Thứ nhất, lập ma trận so sánh giữa RAGAS và TruLens để chỉ ra chiến lược phối hợp tối ưu giữa CI/CD Gate và Production Monitoring.*
  > 
  > *Thứ hai, cài đặt thành công Lexical Reranker `rerank_by_overlap()`. Thực nghiệm trên 5 traces chứng minh Reranking giúp đẩy các thông tin quan trọng lên đầu, tăng Context Precision thêm 11.7% mà không làm thay đổi Context Recall."*

---

#### 📍 SLIDE 6: DEMO GIAO DIỆN RAG EVALUATION PORTAL & KẾT LUẬN
- **Nội dung Slide**:
  - Trình diễn Web Portal (`http://localhost:8000`):
    - Đặt câu hỏi Live / Chọn Golden Preset.
    - Chấm điểm tự động 5 Metrics + Biểu đồ Radar + Giải thích từ vựng Token-level.
    - Tự động chẩn đoán 5 Whys khi gặp lỗi.
  - **Chiến lược chống hồi quy (Regression Strategy)**: Tích hợp `run_regression()` để chặn tự động đợt suy giảm điểm > 5% trong pipeline CI/CD.
  - **Cam kết bàn giao**: Pass 42/42 Pytest, đầy đủ tài liệu trong `exercises.md`, `reflection.md` và đã push 100% lên GitHub.

- **🎙️ Kịch bản Lời nói (Speaker Script)**:
  > *"Để hỗ trợ công tác thử nghiệm trực quan, em đã phát triển một Web Application **RAG Evaluation Portal**. Hệ thống cho phép gởi câu hỏi, tính toán trực tiếp các metrics, giải thích lý do tại sao đạt số điểm đó và tự động đưa ra chẩn đoán lỗi.*
  > 
  > *Toàn bộ mã nguồn, tài liệu báo cáo và bộ test 42/42 PASSED đã sẵn sàng. Em xin chân thành cảm ơn Thầy/Cô và xin lắng nghe các câu hỏi góp ý!"*

---

### ❓ BỘ CÂU HỎI & CÂU TRẢ LỜI ỨNG PHÓ HỘI ĐỒNG (Q&A PREPARATION)

#### Câu hỏi 1: *"Tại sao em không sửa luôn công thức chấm điểm trong `solution.py` để kéo điểm 3 chỉ số Faithfulness/Relevance/Completeness lên cao?"*
- **Trả lời**: *"Dạ thưa Thầy/Cô, việc sửa công thức chấm điểm là hành vi 'bóp méo thước đo', tạo ra điểm số ảo. Trong AI Engineering, Evaluation Core là tiêu chuẩn cố định. Muốn tăng chỉ số một cách trung thực, ta phải tối ưu chính 'System Under Test' (ở đây là `domain_assistant.py`) bằng cách cải tiến Retrieval (`top_k=7`) và ép LLM trả lời chuẩn xác thông qua Prompt Engineering."*

#### Câu hỏi 2: *"Tại sao việc Reranking (Bài 3.5) lại tăng Context Precision mà không làm tăng Context Recall?"*
- **Trả lời**: *"Dạ thưa Thầy/Cô, Context Recall đo lường xem tập hợp tất cả các chunks lấy về có phủ hết đáp án chuẩn hay không (phụ thuộc vào tập hợp hợp - Union set). Reranker chỉ sắp xếp lại vị trí (ranking) của các chunks đó chứ không thêm/bớt chunk nào, nên Recall giữ nguyên. Trong khi đó, Context Precision tính điểm phạt nếu chunk đúng bị xếp ở vị trí phía sau; khi Reranker đẩy chunk đúng lên vị trí Top 1, Top 2 thì điểm Precision sẽ tăng ngay lập tức."*

#### Câu hỏi 3: *"Làm sao em đảm bảo sau này đồng nghiệp sửa Prompt không làm chất lượng hệ thống bị đi xuống?"*
- **Trả lời**: *"Dạ em đã xây dựng chiến lược chống hồi quy (Regression Strategy) dựa trên hàm `run_regression()`. File benchmark kết quả hiện tại được lưu làm Baseline V1. Mỗi khi có thay đổi code/prompt mới, hệ thống CI/CD sẽ tự chạy so sánh điểm. Nếu điểm Overall trung bình bị giảm quá 5% (threshold 0.05), hệ thống sẽ raise Exception và chặn ngay đợt Deploy."*
