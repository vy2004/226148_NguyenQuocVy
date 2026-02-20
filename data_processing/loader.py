import os
import glob

def load_txt_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return content

def load_all_documents(data_dir="data/raw"):
    documents = []
    
    # Tìm tất cả file .txt trong thư mục và thư mục con
    for ext in ['*.txt']:
        pattern = os.path.join(data_dir, ext)
        files = glob.glob(pattern)
        
        pattern_sub = os.path.join(data_dir, '**', ext)
        files += glob.glob(pattern_sub, recursive=True)
        
        for filepath in files:
            try:
                filename = os.path.basename(filepath)
                print(f"  Đang đọc: {filepath}")
                
                content = load_txt_file(filepath)
                
                if content.strip():
                    documents.append({
                        'content': content,
                        'source': filename,
                        'filepath': filepath
                    })
            except Exception as e:
                print(f"  Lỗi khi đọc {filepath}: {e}")
    
    print(f"\nTổng cộng đã đọc: {len(documents)} tài liệu")
    return documents

if __name__ == "__main__":
    docs = load_all_documents()
    for doc in docs:
        print(f"- {doc['source']}: {len(doc['content'])} ký tự")