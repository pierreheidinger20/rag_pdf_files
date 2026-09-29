from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector


Base = declarative_base()


class DocumentChunk(Base):

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)

    document_id = Column(Text, nullable=False)

    page = Column(Integer, nullable=False)

    content = Column(Text, nullable=False)

    embedding = Column(Vector(768), nullable=False)