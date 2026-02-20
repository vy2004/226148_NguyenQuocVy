import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_API_KEY, CHROMA_DB_PATH, USE_GROQ
from vector_store import VectorStore

class HistoryChatbot:
    def __init__(self):
        if USE_GROQ:
            from groq import Groq
            groq_key = os.getenv("GROQ_API_KEY")
            if not groq_key:
                raise ValueError("Chưa cấu hình GROQ_API_KEY trong file .env!")
            self.groq_client = Groq(api_key=groq_key)
            self.use_groq = True
            print("✅ Đã kết nối Groq API (llama-3.3-70b)")
        else:
            import google.generativeai as genai
            if not GEMINI_API_KEY:
                raise ValueError("Chưa cấu hình GEMINI_API_KEY!")
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.0-flash")
            self.use_groq = False
            print("✅ Đã kết nối Gemini API")
        
        self.vector_store = VectorStore()
        self.sessions = {}
    
    def _get_session_history(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]
    
    def _format_history(self, session_id, max_turns=3):
        history = self._get_session_history(session_id)
        if not history:
            return "Chưa có cuộc hội thoại trước đó."
        recent = history[-max_turns:]
        formatted = ""
        for turn in recent:
            formatted += f"Người dùng: {turn['user']}\n"
            formatted += f"Trợ lý: {turn['bot'][:200]}...\n\n"
        return formatted
    
    def _build_prompt(self, query, context, session_id):
        history = self._format_history(session_id)
        
        prompt = f"""Bạn là một chuyên gia lịch sử Việt Nam. Tên của bạn là "Trợ lý Lịch sử".

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời dựa trên thông tin trong phần TÀI LIỆU THAM KHẢO bên dưới
2. Nếu tài liệu không chứa đủ thông tin, hãy nói rõ
3. KHÔNG được bịa đặt thông tin
4. Trả lời bằng tiếng Việt, rõ ràng, mạch lạc
5. Nếu câu hỏi KHÔNG liên quan đến lịch sử Việt Nam, hãy từ chối lịch sự
6. Ở cuối câu trả lời, liệt kê CHÍNH XÁC những nguồn tài liệu bạn đã sử dụng theo format:
   NGUỒN SỬ DỤNG: [tên file 1], [tên file 2]
   Chỉ liệt kê nguồn mà bạn THỰC SỰ trích dẫn thông tin từ đó.

TÀI LIỆU THAM KHẢO:
{context}

LỊCH SỬ HỘI THOẠI:
{history}

CÂU HỎI: {query}

TRẢ LỜI:"""
        return prompt
    
    def _call_llm(self, prompt):
        if self.use_groq:
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048
            )
            return response.choices[0].message.content
        else:
            response = self.model.generate_content(prompt)
            return response.text
    
    def _extract_used_sources(self, answer, all_sources):
        """
        Trích xuất nguồn thực sự được sử dụng từ câu trả lời của LLM.
        LLM sẽ liệt kê nguồn ở cuối câu trả lời.
        """
        used_sources = []
        answer_lower = answer.lower()
        
        for source in all_sources:
            source_lower = source.lower().replace('.txt', '')
            # Kiểm tra tên file có được đề cập trong câu trả lời không
            if source_lower in answer_lower:
                used_sources.append(source)
                continue
            
            # Kiểm tra từ khóa chính của tên file
            # VD: "TRIỀU ĐẠI NHÀ TRẦN (1226 - 1400).txt" -> ["triều", "đại", "nhà", "trần"]
            keywords = source_lower.replace('(', '').replace(')', '').replace('-', '').split()
            # Loại bỏ từ ngắn và số
            keywords = [k for k in keywords if len(k) > 2 and not k.isdigit()]
            
            if not keywords:
                continue
            
            # Đếm số từ khóa xuất hiện trong câu trả lời
            matched = sum(1 for k in keywords if k in answer_lower)
            match_ratio = matched / len(keywords)
            
            # Cần ít nhất 50% từ khóa khớp
            if match_ratio >= 0.5:
                used_sources.append(source)
        
        return used_sources
    
    def _clean_answer(self, answer):
        """Xóa phần NGUỒN SỬ DỤNG ở cuối câu trả lời."""
        lines = answer.split('\n')
        clean_lines = []
        for line in lines:
            if line.strip().upper().startswith('NGUỒN SỬ DỤNG'):
                break
            clean_lines.append(line)
        
        # Xóa dòng trống cuối
        while clean_lines and clean_lines[-1].strip() == '':
            clean_lines.pop()
        
        return '\n'.join(clean_lines)
    
    def chat(self, query, session_id="default"):
        try:
            context, all_sources = self.vector_store.get_formatted_context(
                query, n_results=3, min_similarity=0.3
            )
            prompt = self._build_prompt(query, context, session_id)
            
            for attempt in range(3):
                try:
                    answer = self._call_llm(prompt)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        wait_time = 20 * (attempt + 1)
                        print(f"⏳ Rate limit! Đợi {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise e
            
            # Trích xuất nguồn thực sự được sử dụng
            used_sources = self._extract_used_sources(answer, all_sources)
            
            # Xóa phần nguồn sử dụng khỏi câu trả lời
            clean_answer = self._clean_answer(answer)
            
            history = self._get_session_history(session_id)
            history.append({'user': query, 'bot': clean_answer})
            
            return {
                'answer': clean_answer,
                'sources': used_sources,
                'context_used': len(used_sources) > 0
            }
        except Exception as e:
            return {'answer': f"Xin lỗi, đã xảy ra lỗi: {str(e)}", 'sources': [], 'context_used': False}
    
    def clear_session(self, session_id="default"):
        if session_id in self.sessions:
            self.sessions[session_id] = []

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST CHATBOT LỊCH SỬ VIỆT NAM")
    print("=" * 60)
    
    chatbot = HistoryChatbot()
    print("\nGõ câu hỏi (gõ 'quit' để thoát):\n")
    
    while True:
        query = input("🧑 Bạn: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            print("Tạm biệt! 👋")
            break
        if not query:
            continue
        
        print("⏳ Đang xử lý...")
        result = chatbot.chat(query)
        print(f"\n🤖 Trợ lý:\n{result['answer']}")
        if result['sources']:
            print(f"\n📚 Nguồn: {', '.join(result['sources'])}")
        print("-" * 40)