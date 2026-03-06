"""Test full conversation flow including follow-ups"""
import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, "backend")
sys.path.insert(0, "data_processing")
from rag_chain_pg import ask_pg, clear_history_pg

SID = "test_conv"
clear_history_pg(SID)

def test(q):
    print("=" * 60)
    print(f"USER: {q}")
    r = ask_pg(q, session_id=SID)
    a = r["answer"]
    print(f"BOT ({len(a)} chars): {a[:500]}")
    print(f"SOURCES: {r['sources'][:3]}")
    print()

# Test 1: HCM sinh ngay (accented)
test("Chủ tịch Hồ Chí Minh sinh ngày tháng năm nào?")

# Test 2: follow-up ngắn (accented)
test("ông mất ngày nào?")

# Clear and test new topic
clear_history_pg(SID)

# Test 3: DBP tren khong (unaccented - tests diacritics handling)
test("tom tat chien dich Dien Bien Phu tren khong")

# Test 4: follow-up unaccented
test("ke lai chi tiet dien bien cua chien dich nay")
