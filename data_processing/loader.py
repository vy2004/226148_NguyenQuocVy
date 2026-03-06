"""
Module loader: Đọc file PDF từ thư mục data/pdf/
"""

import os
import glob
from pypdf import PdfReader


def load_pdf_file(filepath):
    """Đọc nội dung từ một file PDF."""
    reader = PdfReader(filepath)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def load_all_documents(data_dir="data/pdf"):
    """
    Đọc tất cả file PDF từ thư mục data_dir.
    Trả về danh sách dict: {"content": ..., "source": ..., "filepath": ...}
    """
    documents = []

    # Tìm tất cả file .pdf trong thư mục và thư mục con
    pattern = os.path.join(data_dir, "*.pdf")
    files = glob.glob(pattern)

    pattern_sub = os.path.join(data_dir, "**", "*.pdf")
    files += glob.glob(pattern_sub, recursive=True)

    # Loại bỏ trùng lặp, giữ nguyên thứ tự
    seen = set()
    unique_files = []
    for f in files:
        abs_path = os.path.abspath(f)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_files.append(f)

    for filepath in sorted(unique_files):
        try:
            filename = os.path.basename(filepath)
            print(f"  📄 Đang đọc: {filepath}")

            content = load_pdf_file(filepath)

            if content.strip():
                documents.append({
                    "content": content,
                    "source": filename,
                    "filepath": filepath,
                })
                print(f"     ✅ {len(content)} ký tự")
            else:
                print(f"     ⚠️ File rỗng hoặc không trích xuất được text")
        except Exception as e:
            print(f"  ❌ Lỗi khi đọc {filepath}: {e}")

    print(f"\n📊 Tổng cộng đã đọc: {len(documents)} tài liệu PDF")
    return documents


if __name__ == "__main__":
    docs = load_all_documents()
    for doc in docs:
        print(f"- {doc['source']}: {len(doc['content'])} ký tự")