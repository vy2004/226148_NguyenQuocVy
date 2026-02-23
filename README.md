# 🇻🇳 Chatbot Tra Cứu Lịch Sử Việt Nam

Hệ thống chatbot thông minh sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)** để trả lời các câu hỏi về lịch sử Việt Nam, từ thời cổ đại đến hiện đại.

## 📋 Mục lục

- [Tổng quan](#-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Luồng dữ liệu](#-luồng-dữ-liệu)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Chức năng từng file](#-chức-năng-từng-file)
- [Cơ sở dữ liệu](#-cơ-sở-dữ-liệu)
- [Cài đặt & Chạy](#-cài-đặt--chạy)
- [Công nghệ sử dụng](#-công-nghệ-sử-dụng)

---

## 🎯 Tổng quan

| Thành phần | Mô tả |
|---|---|
| **Loại ứng dụng** | Chatbot hỏi đáp lịch sử Việt Nam |
| **Kỹ thuật AI** | RAG (Retrieval-Augmented Generation) |
| **Mô hình LLM** | Groq LLaMA 3.3 70B / Google Gemini |
| **Vector DB** | PostgreSQL (cosine similarity) |
| **Embedding** | Sentence Transformers (`all-MiniLM-L6-v2`, 384 chiều) |
| **Giao diện** | Streamlit (theme cờ Việt Nam 🇻🇳) |
| **Nguồn dữ liệu** | Wikipedia tiếng Việt + Tài liệu .txt |

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                    GIAO DIỆN NGƯỜI DÙNG                     │
│                   (Streamlit - app.py)                       │
│              Theme cờ Việt Nam (Đỏ - Vàng)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ Câu hỏi người dùng
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     RAG CHAIN ENGINE                         │
│                   (rag_chain_pg.py)                          │
│                                                              │
│  1. Nhận câu hỏi → Tạo embedding                           │
│  2. Tìm kiếm trong PostgreSQL (cosine similarity)           │
│  3. Ghép context + câu hỏi → Gửi đến LLM                  │
│  4. LLM sinh câu trả lời → Trả về người dùng               │
└──────────┬─────────────────────┬────────────────────────────┘
           │                     │
           ▼                     ▼
┌──────────────────┐  ┌──────────────────────────────────────┐
│   LLM (Groq /    │  │         POSTGRESQL DATABASE           │
│    Gemini API)   │  │    (pg_vector_store.py + db_config)   │
│                  │  │                                        │
│  Sinh câu trả    │  │  • tai_lieu_lich_su (chunks + vectors)│
│  lời từ context  │  │  • lich_su_nhan_tin (chat history)    │
│                  │  │  • nguon_tai_lieu (nguồn trích dẫn)   │
│                  │  │  • + 7 bảng khác                      │
└──────────────────┘  └──────────────────────────────────────┘
                                 ▲
                                 │ Nạp dữ liệu
           ┌─────────────────────┴──────────────────────┐
           │                                             │
┌──────────▼──────────┐              ┌───────────────────▼───┐
│  DATA PROCESSING    │              │   DATA COLLECTION     │
│  (run_pipeline.py)  │              │   (bulk_crawl.py)     │
│                     │              │                       │
│  Đọc file .txt     │              │  Crawl Wikipedia VN   │
│  → Chia chunks     │              │  → Chia chunks        │
│  → Tạo embedding   │              │  → Tạo embedding      │
│  → Lưu PostgreSQL  │              │  → Lưu PostgreSQL     │
└─────────────────────┘              └───────────────────────┘
```

---

## 🔄 Luồng dữ liệu

### 1. Luồng nạp dữ liệu (Offline)

```
File .txt (data/raw/)          Wikipedia tiếng Việt
        │                              │
        ▼                              ▼
   loader.py                    wiki_crawler.py
   (đọc file)                  (tìm kiếm Wikipedia)
        │                              │
        ▼                              ▼
   chunking.py                  source_manager.py
   (chia nhỏ text)             (quản lý URL đã crawl)
        │                              │
        ▼                              ▼
   indexing.py                  dynamic_indexing.py
        │                              │
        └──────────┬───────────────────┘
                   ▼
           pg_vector_store.py
           (tạo embedding + lưu PostgreSQL)
```

### 2. Luồng hỏi đáp (Online)

```
Người dùng nhập câu hỏi
        │
        ▼
   app.py (Streamlit)
        │
        ▼
   rag_chain_pg.py
        │
        ├──► pg_vector_store.search()
        │    → Tạo embedding cho câu hỏi
        │    → Tìm top 10 chunks gần nhất (cosine similarity)
        │    → Trả về context
        │
        ├──► context_evaluator.py
        │    → Đánh giá context có đủ không
        │    → Nếu thiếu → Auto crawl Wikipedia bổ sung
        │
        ├──► LLM API (Groq / Gemini)
        │    → Sinh câu trả lời từ context + câu hỏi
        │
        └──► Lưu lịch sử chat vào PostgreSQL
```

---

## 📁 Cấu trúc thư mục

```
DoAn2-ChatbotLichSu/
├── backend/                    # Xử lý logic chính
│   ├── config.py               # Cấu hình API keys
│   ├── db_config.py            # Cấu hình kết nối PostgreSQL
│   ├── pg_vector_store.py      # Quản lý vector store (PostgreSQL)
│   ├── rag_chain_pg.py         # RAG Engine chính
│   ├── context_evaluator.py    # Đánh giá chất lượng context
│   └── api.py                  # FastAPI endpoints
│
├── data_collection/            # Thu thập dữ liệu
│   ├── bulk_crawl.py           # Crawl hàng loạt từ Wikipedia
│   ├── wiki_crawler.py         # Tìm kiếm & lấy nội dung Wikipedia
│   ├── web_scraper.py          # Scrape nội dung từ URL bất kỳ
│   ├── google_search.py        # Tìm kiếm Google (bổ sung)
│   └── source_manager.py       # Quản lý nguồn đã crawl
│
├── data_processing/            # Xử lý dữ liệu
│   ├── loader.py               # Đọc file .txt từ data/raw/
│   ├── chunking.py             # Chia văn bản thành chunks
│   ├── indexing.py             # Index dữ liệu vào PostgreSQL
│   ├── dynamic_indexing.py     # Index realtime (khi crawl mới)
│   └── run_pipeline.py         # Pipeline xử lý tổng hợp
│
├── frontend/                   # Giao diện người dùng
│   └── app.py                  # Streamlit UI (theme cờ Việt Nam)
│
├── data/                       # Dữ liệu
│   ├── raw/                    # File .txt lịch sử gốc
│   ├── processed/              # Dữ liệu đã xử lý
│   └── crawl_log.json          # Log các URL đã crawl
│
├── evaluation/                 # Đánh giá chất lượng
├── .env                        # Biến môi trường (API keys)
├── requirements.txt            # Thư viện Python
└── README.md                   # Tài liệu này
```

---

## 📝 Chức năng từng file

### 🔧 Backend

| File | Chức năng |
|---|---|
| **`config.py`** | Đọc API keys từ `.env` (GROQ_API_KEY, GEMINI_API_KEY). Thiết lập `USE_GROQ` tự động dựa trên key có sẵn. |
| **`db_config.py`** | Cấu hình kết nối PostgreSQL: host, port, database name, user, password. |
| **`pg_vector_store.py`** | **File quan trọng nhất.** Quản lý toàn bộ PostgreSQL: tạo bảng, thêm documents, tạo embedding bằng Sentence Transformers, tìm kiếm bằng cosine similarity, lưu/đọc lịch sử chat, đếm chunks. Chunk size = 100 words. |
| **`rag_chain_pg.py`** | **RAG Engine chính.** Nhận câu hỏi → tìm context từ PostgreSQL → đánh giá context → nếu thiếu thì auto crawl Wikipedia → gửi prompt cho LLM → trả về câu trả lời kèm nguồn trích dẫn. |
| **`context_evaluator.py`** | Đánh giá xem context tìm được có đủ để trả lời câu hỏi không. Nếu không đủ, hệ thống sẽ tự động crawl thêm dữ liệu từ Wikipedia. |
| **`api.py`** | FastAPI server cung cấp REST API endpoints (`/ask`, `/stats`) để tích hợp với các ứng dụng khác. |

### 🌐 Data Collection

| File | Chức năng |
|---|---|
| **`bulk_crawl.py`** | Crawl hàng loạt ~550 chủ đề lịch sử từ Wikipedia tiếng Việt. Chia theo 28 nhóm: Thời kỳ cổ đại, Bắc thuộc, Phong kiến, Chống Pháp, Chống Mỹ, Pol Pot, Biên giới phía Bắc, Không quân, Văn hóa, Tôn giáo, Di sản, v.v. |
| **`wiki_crawler.py`** | Tìm kiếm từ khóa trên Wikipedia tiếng Việt bằng API, lấy nội dung toàn bộ bài viết. |
| **`web_scraper.py`** | Scrape nội dung từ URL bất kỳ (BeautifulSoup), hỗ trợ crawl từ các trang web lịch sử khác. |
| **`google_search.py`** | Tìm kiếm Google để bổ sung nguồn dữ liệu khi Wikipedia không đủ. |
| **`source_manager.py`** | Quản lý danh sách URL đã crawl (`crawl_log.json`) để tránh crawl trùng lặp. Đánh giá độ tin cậy của nguồn. |

### ⚙️ Data Processing

| File | Chức năng |
|---|---|
| **`loader.py`** | Đọc các file `.txt` từ thư mục `data/raw/`, trích xuất tiêu đề và nội dung. |
| **`chunking.py`** | Chia văn bản dài thành các đoạn nhỏ (chunks) bằng `RecursiveCharacterTextSplitter` (chunk_size=800, overlap=200) để phù hợp với giới hạn embedding model. |
| **`indexing.py`** | Đọc file → chia chunks → tạo embedding → lưu vào PostgreSQL (pipeline đầy đủ cho file .txt). |
| **`dynamic_indexing.py`** | Index dữ liệu mới crawl được vào PostgreSQL ngay lập tức (realtime indexing). |
| **`run_pipeline.py`** | Pipeline tổng hợp: chạy `loader.py` → `chunking.py` → `indexing.py` cho toàn bộ file trong `data/raw/`. |

### 🎨 Frontend

| File | Chức năng |
|---|---|
| **`app.py`** | Giao diện chatbot bằng Streamlit. Theme cờ Việt Nam (đỏ-vàng 🇻🇳). Bao gồm: header với icon cờ VN, sidebar với câu hỏi gợi ý, welcome box, chat interface, hiển thị nguồn tham khảo, và auto-crawl notification. |

---

## 🗄️ Cơ sở dữ liệu (PostgreSQL)

Hệ thống sử dụng **10 bảng** trong PostgreSQL:

| STT | Tên bảng | Chức năng |
|-----|----------|-----------|
| 1 | `tai_lieu_lich_su` | **Bảng chính.** Lưu chunks văn bản + vector embedding (384 chiều) |
| 2 | `nguon_tai_lieu` | Quản lý nguồn (Wikipedia, sách, web) và URL |
| 3 | `thoi_ky_lich_su` | Thông tin các triều đại, thời kỳ lịch sử |
| 4 | `nhan_vat_lich_su` | Thông tin nhân vật lịch sử (tên, tiểu sử, thời kỳ) |
| 5 | `su_kien_lich_su` | Sự kiện, trận đánh, cột mốc quan trọng |
| 6 | `quan_he_thuc_the` | Liên kết nhân vật – sự kiện (Knowledge Graph) |
| 7 | `phien_tro_chuyen` | Quản lý phiên chat (session ID, thời gian) |
| 8 | `lich_su_nhan_tin` | Nội dung chi tiết hỏi đáp (user/bot messages) |
| 9 | `danh_gia_nguoi_dung` | Đánh giá Like/Dislike cho câu trả lời |
| 10 | `thong_ke_tim_kiem` | Log từ khóa tìm kiếm (Analytics) |

---

## 🚀 Cài đặt & Chạy

### Yêu cầu

- Python 3.10+
- PostgreSQL 14+
- API Key: Groq hoặc Google Gemini

### Bước 1: Cài đặt thư viện

```bash
python -m venv venv
.\venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### Bước 2: Cấu hình `.env`

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxx
```

### Bước 3: Tạo database PostgreSQL

```sql
CREATE DATABASE lichsu_vietnam_db;
```

> Các bảng sẽ được tự động tạo khi chạy ứng dụng lần đầu.

### Bước 4: Nạp dữ liệu

```bash
# Nạp từ file .txt
python data_processing/run_pipeline.py

# Crawl từ Wikipedia (~550 chủ đề)
python data_collection/bulk_crawl.py
```

### Bước 5: Chạy chatbot

```bash
streamlit run frontend/app.py --server.port 8502
```

Mở trình duyệt tại **http://localhost:8502**

---

## 🛠️ Công nghệ sử dụng

| Công nghệ | Mục đích |
|---|---|
| **Python 3.10+** | Ngôn ngữ lập trình chính |
| **Streamlit** | Giao diện web chatbot |
| **PostgreSQL** | Cơ sở dữ liệu quan hệ + vector store |
| **Sentence Transformers** | Tạo vector embedding (all-MiniLM-L6-v2) |
| **Groq API** | LLM LLaMA 3.3 70B (sinh câu trả lời) |
| **Google Gemini** | LLM dự phòng |
| **LangChain** | Text splitting, prompt template |
| **Wikipedia API** | Nguồn dữ liệu chính |
| **BeautifulSoup** | Web scraping |
| **FastAPI** | REST API server |

---

## 👨‍💻 Tác giả
**Nguyễn Quốc Vỹ**
**MSSV: 226148**

**Đồ án 2** — Chatbot Tra Cứu Lịch Sử Việt Nam  
Sử dụng kỹ thuật RAG + PostgreSQL + LLM

🇻🇳 *"Dân ta phải biết sử ta, cho tường gốc tích nước nhà Việt Nam"* — Hồ Chí Minh