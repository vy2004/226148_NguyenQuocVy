"""Debug: trace full RAG pipeline to see what context is sent to LLM"""
import sys, os
sys.path.insert(0, "backend")
sys.path.insert(0, "data_processing")

from rag_chain_pg import (
    _embedding_search, _build_context, _find_matching_sources,
    _is_follow_up_question, _extract_topic,
    MAX_TOTAL_CHUNKS, MAX_CONTEXT_CHARS
)

def debug_question(question, prev_topic=None):
    print("=" * 60)
    print(f"QUESTION: {question}")
    print(f"  is_follow_up: {_is_follow_up_question(question)}")
    print(f"  topic: {_extract_topic(question)}")
    print(f"  matching_sources: {_find_matching_sources(question)}")
    if prev_topic:
        combined = f"{prev_topic} {question}"
        print(f"  combined_query: {combined}")
        print(f"  combined_sources: {_find_matching_sources(combined)}")

    results = _embedding_search(question, top_k=MAX_TOTAL_CHUNKS)
    print(f"  search_results: {len(results)}")

    context = _build_context(results, max_chars=MAX_CONTEXT_CHARS)
    print(f"  context_length: {len(context)} chars")
    print(f"  context_preview (first 500 chars):")
    print(f"  ---")
    print(f"  {context[:500]}")
    print(f"  ---")
    print()

# Test 1: HCM sinh ngay
debug_question("Chủ tịch Hồ Chí Minh sinh ngày tháng năm nào?")

# Test 2: short follow-up "ngày mấy" (simulating user question)
debug_question("ngày mấy", prev_topic="chủ tịch hồ chí minh")

# Test 3: ĐBP trên không 
debug_question("tóm tắt chiến dịch Điện Biên Phủ trên không")

# Test 4: follow-up asking for detail
debug_question("kể lại chi tiết diễn biến của chiến dịch này", prev_topic="chiến dịch điện biên phủ trên không")
