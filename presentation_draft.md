# BẢO CÁO THUYẾT TRÌNH HOÀN CHỈNH (COMPLETE PRESENTATION DECK & SCRIPT)
## ĐỀ TÀI: AI EVALUATION & BENCHMARKING PIPELINE FOR ENTERPRISE RAG SYSTEM

**Học viên thực hiện**: Nguyễn Văn Trọng (Lớp K4 - AICB-P1)  
**Thời lượng báo cáo**: 5 – 7 phút  
**Sản phẩm đính kèm**:
- Codebase lõi: `solution/solution.py` (Pass 42/42 Pytest)
- Golden Dataset: `golden_dataset.json` (20 QA Pairs, Pass Validator)
- Báo cáo phân tích: `exercises.md` & `reflection.md`
- Application Web: `server.py` (RAG Evaluation & Diagnostics Portal)

---

### 🎙️ ĐOẠN VĂN MẪU ĐỌC DEMO THUYẾT TRÌNH (1 PHÚT)

> *"Kính chào Thầy Cô và các bạn. Hôm nay em xin trình bày đề tài **AI Evaluation & Benchmarking Pipeline** dành cho Trợ lý ảo OrbitTech.*
>
> *Thay vì đánh giá cảm tính, em đã xây dựng bộ dữ liệu **Golden Dataset 20 QA Pairs** phân tầng kết hợp với bộ **5 chỉ số RAGAS** để đo lường tự động. Kết quả benchmark ghi nhận khâu **Retrieval** hoạt động rất tốt với Precision đạt 91.3%, nhưng khâu **Generation** lại là điểm nghẽn do LLM có thói quen trả lời dài dòng và rò rỉ metadata nội bộ.*
>
> *Bằng phương pháp **5 Whys**, em đã tối ưu khâu Retrieval bằng cách nâng `top_k` lên 7—giúp kéo đúng tài liệu bị sót và đưa Context Recall của ca M04 lên 1.0 tuyệt đối. Đồng thời, em thiết lập **7 quy tắc System Prompt** để triệt tiêu hoàn toàn các lỗi rò rỉ từ rác.*
>
> *Đặc biệt, em đã hoàn thành cả 2 bài tập Bonus: triển khai Reranker giúp tăng Context Precision thêm 11.7% và phát triển **Web Application RAG Evaluation Portal** phục vụ kiểm thử trực quan. Toàn bộ codebase đã pass **42/42 Pytest** và sẵn sàng bàn giao. Em xin chân thành cảm ơn!"*

---

## 🖥️ NỘI DUNG TRÌNH CHIẾU SLIDE & KỊCH BẢN THUYẾT MINH CHI TIẾT

```mermaid
gantt
    title Cấu trúc Bài Thuyết trình (5 - 7 Phút)
    dateFormat  m:s
    axisFormat %M:%S
    Slide 1 - Giới thiệu & Mục tiêu       :00:00, 00:30
    Slide 2 - Đặt vấn đề & Golden Dataset :00:30, 01:30
    Slide 3 - Khung 5 Metrics RAGAS       :01:30, 02:30
    Slide 4 - Thực nghiệm & Phân tích 5 Whys :02:30, 04:00
    Slide 5 - Giải pháp Tối ưu & Bằng chứng  :04:00, 05:00
    Slide 6 - Điểm sáng Bonus (3.4 & 3.5)  :05:00, 05:45
    Slide 7 - Demo Web App & Kết luận      :05:45, 06:30
```

---

### SLIDE 1: GIỚI THIỆU TỔNG QUAN & MỤC TIÊU ĐỀ TÀI

#### 📄 Nội dung văn bản đưa lên Slide:
* **Tiêu đề đè lên Slide**: XÂY DỰNG KHUNG ĐÁNH GIÁ KHOA HỌC & BENCHMARKING CHO HỆ THỐNG ENTERPRISE RAG
* **Ứng dụng thực tế**: Trợ lý ảo Hỗ trợ Khách hàng OrbitTech (OrbitTech Customer Support Assistant)
* **Vấn đề cốt lõi**:
  - Đánh giá cảm tính ("thấy câu trả lời có vẻ hay") gây rủi ro lớn khi đưa AI vào sản xuất.
  - Cần một **Quality Gate khoa học, định lượng** để kiểm soát chất lượng RAG từ khâu Retrieval đến Generation.
* **Mục tiêu đề tài**:
  1. Thiết kế bộ dữ liệu chuẩn (Golden Dataset 20 QA Pairs phân tầng).
  2. Đo lường 5 chỉ số nòng cốt RAGAS (Recall, Precision, Faithfulness, Relevance, Completeness).
  3. Phân tích nguyên nhân gốc rễ 5 Whys và tối ưu thực nghiệm hệ thống.
  4. Xây dựng cơ chế chống hồi quy (Regression Prevention) tự động chặn đợt suy giảm điểm > 5%.

#### 🎙️ Lời nói thuyết minh chi tiết (Word-for-Word Script):
> *"Kính chào Thầy/Cô và toàn thể các bạn học viên.*
>
> *Tên em là Nguyễn Văn Trọng, học viên khóa K4. Hôm nay em xin được báo cáo đề tài **AI Evaluation & Benchmarking Pipeline cho Hệ thống Enterprise RAG OrbitTech**.*
>
> *Trong kỷ nguyên Generative AI hiện nay, thách thức lớn nhất khi đưa một Trợ lý ảo RAG vào sản xuất không phải là việc làm cho nó trả lời được, mà là **đo lường được độ chính xác và an toàn của câu trả lời**. Một câu trả lời nghe rất trôi chảy nhưng nếu chứa thông tin tự bịa (Hallucination) hoặc làm rò rỉ file hệ thống sẽ gây thiệt hại nghiêm trọng cho doanh nghiệp.*
>
> *Chính vì vậy, đề tài của em tập trung xây dựng một hệ thống đánh giá định lượng khoa học, giúp kiểm soát chất lượng RAG một cách tự động, minh bạch và có bằng chứng thực nghiệm."*

---

### SLIDE 2: ĐẶT VẤN ĐỀ & THIẾT KẾ GOLDEN DATASET PHÂN TẦNG

#### 📄 Nội dung văn bản đưa lên Slide:
* **4 Rủi ro phổ biến trong RAG**:
  - ❌ *Hallucination*: LLM tự nghĩ ra thông tin không có trong tài liệu.
  - ❌ *Data Leakage*: LLM làm rò rỉ metadata nội bộ (như chữ "context", tên file `.md`).
  - ❌ *Off-topic / Irrelevant*: LLM trả lời dài dòng, đi chệch trọng tâm câu hỏi.
  - ❌ *Insufficient Retrieval*: Bộ truy xuất (Retriever) bỏ sót tài liệu chứa câu trả lời.
* **Thiết kế Golden Dataset (20 QA Pairs)**:
  - 🟢 **5 Easy** (25%): Tra cứu trực tiếp 1-fact (Giá thẻ thành viên, thời gian giao hàng).
  - 🟡 **7 Medium** (35%): Tra cứu đa điều kiện (Quy trình hủy đơn, điều kiện freeship prepaid).
  - 🔴 **5 Hard** (25%): Tra cứu đa bước & tính toán logic (Chính sách đổi trả 28 ngày của OrbitPlus).
  - ⚠️ **3 Adversarial** (15%): Bẫy Prompt Injection (`A02`), Bẫy Giả định sai (`A03`), Bẫy Out-of-scope (`A01`).
* **Đảm bảo tính Provenance**:
  - Chuẩn hóa toàn bộ câu hỏi và đáp án mẫu bằng tiếng Anh để tối ưu token matching.
  - Pass 100% kiểm định `validate_golden_dataset.py`.

---

### SLIDE 3: BỘ KHUNG ĐÁNH GIÁ 5 METRICS & KẾT QUẢ BENCHMARK SƠ BỘ

#### 📄 Nội dung văn bản đưa lên Slide:
* **Bộ 5 Chỉ số RAGAS-inspired (Công thức Token Overlap)**:
  1. $\text{Context Recall} = \frac{|\text{Expected} \cap \text{Context}|}{|\text{Expected}|}$ (Bao phủ bằng chứng)
  2. $\text{Context Precision} = \text{Mean}(\text{Precision}@k)$ (Thứ hạng bằng chứng đúng)
  3. $\text{Faithfulness} = \frac{|\text{Answer} \cap \text{Context}|}{|\text{Answer}|}$ (Căn cứ trên context)
  4. $\text{Relevance} = \frac{|\text{Answer} \cap \text{Question}|}{|\text{Question}|}$ (Đúng trọng tâm câu hỏi)
  5. $\text{Completeness} = \frac{|\text{Answer} \cap \text{Expected}|}{|\text{Expected}|}$ (Độ đầy đủ ý)

* **Báo cáo Kết quả Benchmark Thực nghiệm (Baseline)**:
  - **Pass Rate tổng thể**: `45.0%` (9 / 20 câu đạt chuẩn Overall $\ge 0.60$ & Faithfulness $\ge 0.50$).
  - **Context Recall**: `0.877` | **Context Precision**: `0.913` (Retrieval hoạt động rất tốt).
  - **Faithfulness**: `0.575` | **Relevance**: `0.567` | **Completeness**: `0.704` (Generation kéo điểm xuống).

---

### SLIDE 4: PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ (5 WHYS) & GIẢI PHÁP TỐI ƯU

#### 📄 Nội dung văn bản đưa lên Slide:
* **Phân tích 5 Whys điển hình (Case M04 - Thời hạn bảo hành AeroBuds Pro)**:
  - *Symptom*: Context Recall ban đầu chỉ đạt `0.292` (Fail).
  - *Why 1-3*: Đoạn thông tin liệt kê các điều kiện loại trừ bảo hành bị thiếu trong ngữ cảnh.
  - *Why 4-5*: Thuật toán BM25 với cấu hình `top_k=5` chỉ lấy được các đoạn mô tả chung, chunk chứa danh sách loại trừ chi tiết nằm ở thứ hạng thứ 6.
  - *Root Cause*: Cấu hình `top_k` quá nhỏ đối với các câu hỏi phức tạp đòi hỏi nhiều bằng chứng.

* **Giải pháp Tối ưu Hệ thống (Không can thiệp thước đo `solution.py`)**:
  - 🛠️ **Tối ưu Retrieval**: Tăng `top_k` từ **5 lên 7** $\rightarrow$ Kéo thành công chunk thứ 6 trong `06_warranty_policy.md` $\rightarrow$ Đưa Context Recall của `M04` lên **1.000**.
  - 🛠️ **Tối ưu Generation (7 System Prompt Rules)**:
    1. Ép trả lời thẳng vào trọng tâm, dùng chủ thể câu hỏi làm từ mở đầu.
    2. Cấm tuyệt đối các từ rác metadata: "context", "provided document", "Context 2".
    3. Cấm rò rỉ tên file nội bộ `.md`.
    4. Cấm đưa ra lời khuyên tài chính/pháp lý ngoài tài liệu.
  - 🛠️ **Cấu hình Parameter**: Tăng `max_output_tokens` lên **400** chống cắt cụt văn bản.

---

### SLIDE 5: ĐIỂM SÁNG BÀI TẬP BONUS (EXERCISE 3.4 & 3.5 - +15 ĐIỂM)

#### 📄 Nội dung văn bản đưa lên Slide:
* **Exercise 3.4 (+10 pt) — Ma trận So sánh RAGAS vs. TruLens**:

| Tiêu chí | RAGAS (Em đã triển khai) | TruLens (Framework so sánh) |
|---|---|---|
| **Cơ chế chấm** | Token Overlap / Lexical Semantics | LLM-as-a-Judge (Prompt-based) |
| **Độ nghiêm ngặt** | Khắt khe (Strict), phát hiện lỗi rò rỉ từ cực bén | Nương tay hơn (Lenient) do LLM Judge có verbosity bias |
| **Vị trí tối ưu** | 🚀 **CI/CD Quality Gate** (Chạy offline, block deploy) | 📈 **Production Monitoring** (Tracking user feedback real-time) |

* **Exercise 3.5 (+5 pt) — Thực nghiệm Reranking (`rerank_by_overlap()`)**:
  - Triển khai thuật toán Lexical Reranker xếp lại thứ tự chunks theo mật độ từ trùng với câu hỏi.
  - **Kết quả thực nghiệm trên 5 Traces**:

```
Context Precision : 0.796  ===>  0.913  (+0.117 / +11.7%)  [TĂNG MẠNH]
Context Recall    : 0.664  ===>  0.664  (+0.000 / 0.0%)    [GIỮ NGUYÊN BẢO BẢO]
```

---

### SLIDE 6: DEMO GIAO DIỆN RAG EVALUATION PORTAL & KẾT LUẬN

#### 📄 Nội dung văn bản đưa lên Slide:
* **Bàn giao Web Application**: `server.py` (Chạy tại `http://localhost:8000`).
  - 💬 **Live RAG & Evaluation**: Nhập câu hỏi tự do hoặc chọn 20 Golden Presets $\rightarrow$ Chấm 5 metrics real-time + Biểu đồ Radar + Giải thích từ vựng Token-level.
  - 🔍 **Auto 5-Whys Diagnosis**: Tự động hiển thị thẻ Chẩn đoán Nguyên nhân & Giải pháp khi câu trả lời bị FAIL.
  - 📊 **Benchmark Explorer**: Bảng theo dõi 20 QA tương tác có bộ lọc PASS/FAIL.
* **Chiến lược Chống Hồi quy (Regression Prevention Strategy)**:
  - Tích hợp hàm `run_regression(new_results, baseline_results, threshold=0.05)`.
  - Tự động chặn (Block) đợt Deploy nếu điểm Overall bị giảm quá 5%.
* **Tổng kết Deliverables**:
  - ✅ Pass `42 / 42` Pytest cases.
  - ✅ `golden_dataset.json` PASS Validator.
  - ✅ Đã đồng bộ đầy đủ báo cáo trong `exercises.md`, `reflection.md` và push 100% lên GitHub.

---

## ❓ BỘ CÂU HỎI VÀ CÂU TRẢ LỜI ỨNG PHÓ HỘI ĐỒNG (Q&A DEFENSE SCRIPT)

### Câu hỏi 1: *"Tại sao em không sửa luôn công thức chấm điểm trong `solution.py` để kéo điểm 3 chỉ số Faithfulness/Relevance/Completeness lên cao cho đẹp báo cáo?"*
- **Trả lời**: *"Dạ thưa Thầy/Cô, việc sửa công thức chấm điểm là hành vi 'bóp méo thước đo' (Cheating evaluation core). Trong kĩ thuật AI, bộ evaluator phải là một tiêu chuẩn cố định và khách quan. Muốn cải thiện chỉ số một cách trung thực, ta phải giữ nguyên thước đo và tiến hành tối ưu chính hệ thống RAG (`domain_assistant.py`) thông qua việc tinh chỉnh tham số Retrieval (`top_k=7`) và áp đặt các ràng buộc Prompt Engineering."*

### Câu hỏi 2: *"Tại sao việc Reranking ở Bài 3.5 chỉ làm tăng Context Precision mà không làm tăng Context Recall?"*
- **Trả lời**: *"Dạ thưa Thầy/Cô, Context Recall đo lường xem tập hợp tất cả các chunks lấy về có bao phủ hết thông tin của đáp án chuẩn hay không (đây là tính chất của tập hợp hợp - Union set). Reranker chỉ làm nhiệm vụ sắp xếp lại thứ tự (ranking) của các chunks đã lấy về chứ không thêm hoặc xóa chunk nào, nên tổng lượng thông tin bao phủ (Recall) giữ nguyên 100%. Trong khi đó, Context Precision tính điểm phạt nếu chunk đúng bị xếp ở vị trí phía sau; khi Reranker đẩy chunk đúng lên Top 1 hay Top 2 thì chỉ số Precision sẽ tăng lên ngay lập tức."*

### Câu hỏi 3: *"Làm thế nào em đảm bảo trong tương lai khi đồng nghiệp thay đổi Prompt hoặc đổi sang mô hình LLM khác thì chất lượng hệ thống không bị sụt giảm?"*
- **Trả lời**: *"Dạ em đã xây dựng cơ chế chống hồi quy tự động (Automated Regression Testing) dựa trên hàm `run_regression()`. File benchmark kết quả hiện tại (`benchmark_results.json`) được lưu giữ làm Baseline V1. Trong pipeline CI/CD, mỗi khi có một đợt cập nhật code hoặc prompt mới, hệ thống sẽ tự động chạy lại benchmark và so sánh với Baseline. Nếu điểm Overall trung bình bị giảm quá 5% (`threshold = 0.05`), hàm sẽ lập tức raise Exception và chặn (Block) đợt Deploy đó lại, buộc lập trình viên phải tinh chỉnh cho đến khi đạt chất lượng bằng hoặc cao hơn Baseline."*
