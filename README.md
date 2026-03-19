---
title: Chatbot Lich Su Viet Nam
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Chatbot Tra Cứu Lịch Sử Việt Nam

Dự án xây dựng chatbot hỏi đáp về lịch sử Việt Nam theo hướng `RAG (Retrieval-Augmented Generation)`. Hệ thống hiện đã có thể đọc PDF, tạo embedding, truy vấn ChromaDB, gọi LLM để trả lời, lưu lịch sử hỏi đáp, và cung cấp giao diện Streamlit cho người dùng.

README này được cập nhật theo **trạng thái code hiện tại** trong repo, không mô tả theo kế hoạch cũ.

---

## Tổng quan

| Thành phần | Trạng thái hiện tại |
|---|---|
| Bài toán | Chatbot tra cứu lịch sử Việt Nam |
| Giao diện | `Streamlit` (`frontend/app.py`) |
| Backend chat | `backend/rag_chain_pg.py` |
| API bổ trợ | `FastAPI` (`backend/api.py`) |
| Vector DB | `ChromaDB` persistent tại `data/csdl_vector/` |
| Embedding | `intfloat/multilingual-e5-base` |
| LLM chính | Groq `llama-3.3-70b-versatile` |
| LLM dự phòng | Gemini `2.5-flash -> 2.0-flash -> 2.0-flash-lite` |
| CSDL quan hệ | `SQLite` tại `data/chatbot.db` |
| Nguồn dữ liệu | PDF lịch sử + Wikipedia tiếng Việt fallback |

---

## Hình ảnh và sơ đồ

Các hình dưới đây được nhúng bằng **đường dẫn tương đối** từ `README.md` tới thư mục `docs/`, nên khi push repo lên GitHub, người khác có thể xem trực tiếp ngay trên trang dự án nếu các file ảnh cũng được commit đầy đủ.

### Sơ đồ kiến trúc RAG

![Sơ đồ kiến trúc RAG](docs/rag-diagram.drawio.png)

### Activity Diagram

![Activity Diagram](docs/Activity.png)

### Use Case tổng quát

![Use Case tổng quát](docs/UseCase_tong_quat.png)

### Use Case người dùng

![Use Case người dùng](docs/Usecase_User.png)

### Use Case admin

![Use Case admin](docs/Usecase_Admin.png)

### Database Diagram

![Database Diagram](docs/DatabaseDiagram.png)

### ERD

![ERD](docs/ERD.png)

---

## Tính năng đã có

### 1. Hỏi đáp RAG

- Nhận câu hỏi từ giao diện hoặc API.
- Phát hiện câu hỏi tiếp nối để giữ context theo `session_id`.
- Tìm ngữ cảnh liên quan trong ChromaDB bằng embedding E5.
- Gọi Groq làm provider chính, tự động fallback sang Gemini khi cần.
- Nếu LLM lỗi hoặc không đủ điều kiện, hệ thống có `extractive fallback`.
- Khi kho PDF chưa đủ thông tin, hệ thống có thể bổ sung ngữ cảnh từ Wikipedia.

### 2. Quản lý tài liệu PDF

- Nhận file PDF từ thư mục `data/pdf/` để index offline.
- Hỗ trợ upload PDF trực tiếp trên Streamlit.
- Lưu metadata tài liệu vào SQLite.
- Cho phép tóm tắt nhanh nội dung file vừa tải lên.
- Admin có thể thêm/xóa tài liệu hệ thống và thực hiện tái lập chỉ mục.

### 3. Quản lý người dùng

- Đăng ký, đăng nhập, đăng xuất.
- Quên mật khẩu bằng OTP.
- Gửi OTP qua Gmail SMTP nếu đã cấu hình.
- Nếu gửi mail thất bại, hệ thống có fallback hiện OTP để demo.
- Có phân quyền `user` / `admin`.
- Admin có thể đổi vai trò và khóa/mở khóa tài khoản.

### 4. Quản lý hội thoại và phản hồi

- Tạo nhiều cuộc trò chuyện.
- Lưu lịch sử hỏi đáp theo người dùng.
- Tự động đặt tiêu đề cuộc trò chuyện từ câu hỏi đầu tiên.
- Lưu nguồn tham khảo cho từng câu trả lời.
- Người dùng có thể đánh giá `thích/không thích` và gửi phản hồi.
- Admin xem được lịch sử hỏi đáp toàn hệ thống và danh sách phản hồi.

### 5. API cơ bản

`backend/api.py` hiện đang cung cấp các endpoint:

- `GET /`: kiểm tra trạng thái server.
- `POST /chat`: gửi câu hỏi và nhận câu trả lời.
- `POST /clear`: xóa context chat theo `session_id`.

API đang ở mức cơ bản, phù hợp để test hoặc tích hợp nhẹ; luồng sử dụng chính hiện tại vẫn là giao diện Streamlit.

---

## Kiến trúc hiện tại

```text
Người dùng
   |
   v
Streamlit UI (frontend/app.py)
   |
   +-- Auth / lịch sử / feedback / upload PDF / admin
   |
   v
RAG Engine (backend/rag_chain_pg.py)
   |
   +-- Embedding search trong ChromaDB
   +-- Follow-up detection theo session
   +-- Groq -> Gemini -> extractive fallback
   +-- Wikipedia fallback khi cần
   |
   +--> SQLite (backend/db.py)
   |      - nguoi_dung
   |      - cuoc_tro_chuyen
   |      - tin_nhan
   |      - tai_lieu
   |      - phan_hoi_nguoi_dung
   |
   +--> ChromaDB (data/csdl_vector/)
   |
   +--> PDF pipeline (data_processing/)
```

---

## Cấu trúc thư mục

```text
DoAn2-ChatbotLichSu/
├── backend/
│   ├── admin_services.py      # Dịch vụ admin: user, feedback, tài liệu, reindex
│   ├── api.py                 # FastAPI endpoint cơ bản
│   ├── auth.py                # Đăng ký, đăng nhập, OTP, reset mật khẩu
│   ├── config.py              # Cấu hình backend
│   ├── db.py                  # SQLite schema và truy vấn
│   ├── email_service.py       # Gửi OTP qua Gmail SMTP
│   ├── rag_chain_pg.py        # RAG engine chính
│   └── wiki_crawler.py        # Bổ sung dữ liệu từ Wikipedia
├── data/
│   ├── chatbot.db             # SQLite database
│   ├── csdl_vector/           # ChromaDB persistent storage
│   ├── pdf/                   # File PDF nguồn
│   └── processed/             # Dữ liệu xử lý trung gian
├── data_processing/
│   ├── chunking.py            # Chia đoạn văn bản
│   ├── dynamic_indexing.py    # Hỗ trợ cập nhật chỉ mục
│   ├── indexing.py            # Tạo/search vector database
│   ├── loader.py              # Đọc PDF
│   └── run_pipeline.py        # Chạy pipeline index offline
├── docs/                      # Ảnh sơ đồ, use case, ERD, activity
├── evaluation/                # Thử nghiệm / đánh giá
├── frontend/
│   └── app.py                 # Giao diện Streamlit
├── requirements.txt
└── README.md
```

---

## Cơ sở dữ liệu

### SQLite

Hệ thống hiện đang dùng `SQLite` để lưu các thành phần chính:

- `nguoi_dung`: thông tin tài khoản, vai trò, trạng thái khóa.
- `khoi_phuc_mat_khau`: OTP đặt lại mật khẩu.
- `cuoc_tro_chuyen`: metadata mỗi cuộc trò chuyện.
- `tin_nhan`: nội dung hỏi đáp.
- `tai_lieu`: tài liệu người dùng và tài liệu hệ thống.
- `phan_hoi_nguoi_dung`: đánh giá và nhận xét của người dùng.
- `tin_nhan_tham_khao`: nguồn tham khảo gắn với từng tin nhắn.

### ChromaDB

| Thuộc tính | Giá trị hiện tại |
|---|---|
| Đường dẫn | `data/csdl_vector/` |
| Collection | `lich_su_viet_nam` |
| Embedding | `intfloat/multilingual-e5-base` |
| Metric | cosine similarity |

---

## Luồng xử lý chính

### 1. Index tài liệu

```text
PDF -> loader.py -> chunking.py -> indexing.py -> ChromaDB
```

### 2. Hỏi đáp

```text
Câu hỏi -> ask_pg()
        -> embedding search
        -> tạo prompt
        -> Groq / Gemini
        -> lưu lịch sử + nguồn tham khảo
```

### 3. Fallback

```text
Không đủ thông tin từ PDF
-> tìm/crawl Wikipedia
-> thêm vào ngữ cảnh truy vấn
-> sinh câu trả lời mới
```

---

## Tiến độ dự án

### Đã hoàn thành ở mức sử dụng được

- RAG core với ChromaDB + embedding E5.
- Hỏi đáp theo ngữ cảnh và giữ context hội thoại.
- Fallback Groq -> Gemini -> extractive.
- Upload PDF và index trực tiếp từ giao diện.
- Tóm tắt tài liệu đã upload.
- Đăng ký, đăng nhập, quên mật khẩu bằng OTP.
- Lưu lịch sử chat, lưu nguồn tham khảo, lưu feedback.
- Trang quản trị cơ bản cho admin.
- FastAPI endpoint cơ bản để test chat.

### Đang tiếp tục hoàn thiện

- Tối ưu chất lượng truy hồi và chất lượng câu trả lời.


---

## Cài đặt và chạy

### 1. Cài thư viện

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Tạo file `.env`

```env
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash

SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

Ghi chú:

- `GEMINI_API_KEY` nên có để làm fallback cho Groq.
- `SMTP_EMAIL` và `SMTP_PASSWORD` là tùy chọn, chỉ cần khi muốn gửi OTP qua email.

### 3. Chuẩn bị dữ liệu

- Đặt file PDF lịch sử vào `data/pdf/`.
- Chạy index offline nếu muốn nạp toàn bộ dữ liệu ngay từ đầu:

```bash
python data_processing/run_pipeline.py
```

### 4. Chạy giao diện Streamlit

```bash
streamlit run frontend/app.py --server.port 8502
```

Mở trình duyệt tại `http://localhost:8502`.

### 5. Chạy API (tùy chọn)

```bash
python backend/api.py
```

API docs mặc định tại `http://localhost:8000/docs`.

---

## Triển khai Hugging Face Space

Để deploy ổn định trên Hugging Face, nên tách thành:

- `Space repo`: chỉ chứa code và cấu hình Docker.
- `Dataset repo`: chứa dữ liệu runtime nặng như `csdl_vector/` và PDF.

Repo này đã được chuẩn bị sẵn cho mô hình đó:

- `scripts/bootstrap_space_data.py`: tải dataset từ Hugging Face Dataset repo vào `APP_DATA_DIR`
- `scripts/start_space.py`: bootstrap dataset rồi khởi chạy Streamlit
- `scripts/export_dataset_bundle.py`: xuất bundle dữ liệu từ local để đẩy sang Dataset repo
- `docs/hf_space_dataset_repo.md`: hướng dẫn chi tiết tạo dataset repo và cấu hình Space

Biến môi trường nên cấu hình trên Space:

- `HF_DATASET_REPO`
- `HF_DATASET_REVISION`
- `APP_DATA_DIR`
- `HF_DATASET_REQUIRED` (tùy chọn)
- `HF_DATASET_FORCE_SYNC` (tùy chọn)
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `HF_TOKEN` nếu dataset repo là private

Khuyến nghị:

- dùng `APP_DATA_DIR=/tmp/app_data` nếu không có persistent storage
- dùng `APP_DATA_DIR=/data/app_data` nếu Space có persistent storage

---

## Công nghệ sử dụng

| Công nghệ | Vai trò |
|---|---|
| Python | Ngôn ngữ chính |
| Streamlit | Giao diện người dùng |
| FastAPI + Uvicorn | API backend |
| ChromaDB | Vector database |
| SQLite | Lưu dữ liệu quan hệ |
| Sentence Transformers | Embedding E5 |
| Groq API | LLM chính |
| Google Gemini API | LLM dự phòng |
| LangChain Text Splitters | Chunking văn bản |
| pypdf | Đọc PDF |
| BeautifulSoup + requests | Crawl / làm sạch Wikipedia |
| python-dotenv | Đọc biến môi trường |

---

## Tác giả

**Nguyễn Quốc Vỹ**  
**MSSV: 226148**

Đồ án 2 - Chatbot Tra cứu Lịch sử Việt Nam.
