from pathlib import Path
import uuid

from fastapi import FastAPI, UploadFile, File
import ollama
from openai import OpenAI
from dotenv import load_dotenv

from app.schemas import ChatRequest
from app.services.pdf_service import extract_text_from_pdf
from app.services.chunk_service import create_chunks
from app.services.embedding_service import create_embedding

from app.database import engine, init_db, SessionLocal
from app.models import Base

from app.repositories.chunk_repository import save_chunk, search_similar_chunks

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


app = FastAPI()
init_db()
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {
        "message": "RAG backend is running"
    }


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    document_id = str(uuid.uuid4())

    file_path = BASE_DIR / file.filename

    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    # 1. Extraer texto
    pages = extract_text_from_pdf(str(file_path))

    # 2. Crear chunks
    chunks = create_chunks(pages)

    # 3. Guardar chunks + embeddings
    db = SessionLocal()

    try:
        for chunk in chunks:

            embedding = create_embedding(
                chunk["text"]
            )

            save_chunk(
                db=db,
                document_id=document_id,
                page=chunk["page"],
                content=chunk["text"],
                embedding=embedding
            )

    finally:
        db.close()

    return {
        "document_id": document_id,
        "filename": file.filename,
        "pages": len(pages),
        "chunks": len(chunks)
    }

@app.post("/chat")
def chat(request: ChatRequest):

    db = SessionLocal()

    try:
        # 1. Convertir la pregunta en embedding
        question_embedding = create_embedding(request.message)

        # 2. Buscar los chunks más similares
        chunks = search_similar_chunks(
            db=db,
            embedding=question_embedding,
            document_id=request.document_id,
            limit=3
        )

        # 3. Construir el contexto
        context = "\n\n".join(
            f"[Página {chunk.page}]\n{chunk.content}"
            for chunk in chunks
        )

        # 4. Enviar contexto + pregunta a Ollama
        prompt = f"""
Responde la pregunta utilizando únicamente la información
proporcionada en el contexto.

Si la respuesta no está en el contexto, responde:
"No encontré esa información en el documento."

No inventes información.

Cuando sea posible, indica la página de donde obtuviste
la información.

CONTEXTO:
{context}

PREGUNTA:
{request.message}
"""

        response = ollama.chat(
            model="qwen3:4b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return {
            "question": request.message,
            "answer": response.message.content,
            "sources": [
                {
                    "page": chunk.page,
                    "content": chunk.content
                }
                for chunk in chunks
            ]
        }

    finally:
        db.close()