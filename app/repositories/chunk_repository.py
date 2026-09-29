from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk


def save_chunk(
    db: Session,
    document_id: str,
    page: int,
    content: str,
    embedding: list[float]
):
    chunk = DocumentChunk(
        document_id=document_id,
        page=page,
        content=content,
        embedding=embedding
    )

    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return chunk

def search_similar_chunks(
    db: Session,
    embedding: list[float],
    document_id: str,
    limit: int = 3
):
    distance = DocumentChunk.embedding.cosine_distance(embedding)

    statement = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(distance)
        .limit(limit)
    )

    return db.execute(statement).scalars().all()