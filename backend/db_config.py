"""
Cấu hình PostgreSQL (không cần pgvector)
"""

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "lichsu_vietnam_db",
    "user": "postgres",
    "password": "123456", 
}

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384