import traceback

try:
    from dotenv import load_dotenv
    load_dotenv(".env", override=True)
    import sys, os
    sys.path.insert(0, "data_processing")

    from indexing import search, get_collection, EMBEDDING_MODEL
    print(f"[OK] Embedding model: {EMBEDDING_MODEL}")

    col = get_collection()
    count = col.count()
    print(f"[OK] Total chunks: {count}")

    if count == 0:
        print("[ERROR] DB rong!")
    else:
        test_queries = [
            ("Dien Bien Phu", "Chiến dịch Điện Biên Phủ diễn ra năm nào?"),
            ("Ho Chi Minh", "Chủ tịch Hồ Chí Minh sinh ngày tháng năm nào?"),
            ("Bien gioi Viet Trung", "Chiến tranh biên giới Việt Trung 1979 diễn ra như thế nào?"),
            ("Bach Dang 938", "Ngô Quyền đánh trận Bạch Đằng năm 938"),
            ("Hai Ba Trung", "Cuộc khởi nghĩa Hai Bà Trưng diễn ra khi nào?"),
            ("DBP tren khong", "Chiến dịch Điện Biên Phủ trên không 12 ngày đêm"),
            ("Thanh co Quang Tri", "Trận thành cổ Quảng Trị năm 1972"),
            ("Hiep dinh Gionevo", "Hiệp định Giơnevo có nội dung gì?"),
        ]

        for label, query in test_queries:
            print(f"\n=== {label} ===")
            results = search(query, top_k=3, max_distance=1.0)
            print(f"  Results: {len(results)}")
            for r in results:
                src = r["metadata"].get("source", "?")
                dist = r["score"]
                txt = r["content"][:120].replace("\n", " ")
                print(f"  dist={dist:.4f} | {src}")
                print(f"  >>> {txt}")

except Exception as e:
    print(f"[FATAL ERROR] {e}")
    traceback.print_exc()