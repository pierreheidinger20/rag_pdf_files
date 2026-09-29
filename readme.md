# RAG Documents API

This service accepts PDF files, stores their text as searchable chunks, and answers questions using the matching content from a selected document.

## Requirements

- Python 3.10 or newer
- Docker and Docker Compose
- [Ollama](https://ollama.com/) running locally
- PostgreSQL with the `pgvector` extension (the included Compose file provides this)
- Tesseract OCR and English language data for scanned or image based PDF pages

The service uses Ollama model `nomic-embed-text` to create 768 dimension embeddings and `qwen3:4b` to answer questions. Pull both models before starting the API:

```bash
ollama pull nomic-embed-text
ollama pull qwen3:4b
```

## Setup and run

From the project root, start PostgreSQL:

```bash
docker compose up -d postgres
```

Create a `.env` file in the project root. The local values below match `docker-compose.yml`:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/rag
```

Install dependencies and start the server:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The base URL is `http://localhost:8000`. Interactive Swagger documentation is available at [`/docs`](http://localhost:8000/docs), with the OpenAPI schema at `/openapi.json`.

> OCR code imports `pytesseract` and Pillow. Those packages and the Tesseract executable are not listed in `requirements.txt`; install them separately if you need scanned PDF support. Tesseract is configured to OCR in English (`eng`).

## Endpoints

### `GET /` — health check

Confirms that the API process is responding. It does not check PostgreSQL or Ollama connectivity.

```bash
curl http://localhost:8000/
```

Response:

```json
{"message":"RAG backend is running"}
```

### `POST /documents` — upload a PDF

Send a `multipart/form-data` request with a `file` field. The service extracts text page by page, splits it into overlapping chunks, creates embeddings, and stores the chunks. A generated `document_id` identifies this upload and is required to ask questions about it.

```bash
curl -X POST http://localhost:8000/documents \
  -F 'file=@./example.pdf;type=application/pdf'
```

Example response:

```json
{
  "document_id": "8d57eb18-b054-4735-9a8c-bba710257084",
  "filename": "example.pdf",
  "pages": 12,
  "chunks": 18
}
```

Keep the returned `document_id`; the API currently does not provide an endpoint to list or retrieve document IDs. `pages` counts PDF pages, including pages with no extracted text. `chunks` counts stored text chunks. Chunk size is 1,000 characters with 200 characters of overlap.

### `POST /chat` — ask a question

Send a JSON body containing the question and the ID returned by the upload endpoint. The service searches only within that document, sends up to three most similar chunks to the language model, and returns the answer along with those source chunks.

```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "document_id": "8d57eb18-b054-4735-9a8c-bba710257084",
    "message": "What are the main conclusions?"
  }'
```

Request fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `document_id` | string | Yes | ID returned by `POST /documents` |
| `message` | string | Yes | Question to answer from the document |

Example response:

```json
{
  "question": "What are the main conclusions?",
  "answer": "The document concludes that ... (page 10).",
  "sources": [
    {
      "page": 10,
      "content": "The extracted text of a relevant passage..."
    }
  ]
}
```

If no relevant text is available, the response can have an empty `sources` array. The model is instructed to say `No encontré esa información en el documento.` (Spanish: “I did not find that information in the document.”) when the context does not contain the answer. Page numbers are one-based.

## Typical integration flow

1. Upload a PDF with `POST /documents`.
2. Save its `document_id` in your application.
3. Send each question and that ID to `POST /chat`.
4. Display `answer`; optionally show `sources` to let users inspect supporting passages.

## Errors and operational notes

- FastAPI validation errors are returned for missing required fields or malformed requests. Uploads must include a file; chat requests must include both string fields.
- Failures connecting to PostgreSQL or Ollama, unsupported/corrupt PDFs, and OCR failures can cause a server error. Ensure the database and Ollama are running and the two Ollama models have been pulled.
- Upload accepts any filename at the HTTP layer, but the processing code expects a readable PDF. There is currently no explicit file size or content-type validation.
- There is no authentication or authorization. Do not expose this service to untrusted networks without adding access controls.
- Uploaded source files are written under the project root; the database stores extracted chunks and embeddings. There is no delete endpoint.
- The database schema fixes embeddings at 768 dimensions, matching the configured `nomic-embed-text` model. Changing the embedding model may require a schema migration.

