from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rag_chain_pg import ask_pg, clear_history_pg

app = FastAPI(title="Chatbot Lịch Sử Việt Nam API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Đang khởi tạo chatbot...")
print("✅ Chatbot đã sẵn sàng!")

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    session_id: str

@app.get("/")
async def root():
    return {"status": "ok", "message": "Chatbot Lịch Sử API đang hoạt động!"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")
    
    session_id = request.session_id or str(uuid.uuid4())
    result = ask_pg(request.message, session_id=session_id)
    
    return ChatResponse(
        answer=result['answer'],
        sources=result.get('sources', []),
        session_id=session_id
    )

@app.post("/clear")
async def clear_session(session_id: str = "default"):
    clear_history_pg(session_id)
    return {"message": f"Đã xóa lịch sử session: {session_id}"}

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Khởi động API server...")
    print("📝 API docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)