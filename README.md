# PDF Lecture Parser

A FastAPI-based service that intelligently matches lecture transcripts to PDF slides using AI embeddings. Upload a lecture PDF and transcript, and the system automatically aligns spoken content with corresponding slides.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│                    (TypeScript Frontend)                        │
│                         Port 3000                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTP/REST API
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                            │
│                         Port 8000                               │
├─────────────────────────────────────────────────────────────────┤
│  POST /process-lecture                                          │
│    ├─ PDF File (slides.pdf)                                     │
│    └─ Transcript File (transcript.txt)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────────┐  ┌─────────────────┐
│   Docling    │  │  Transformers    │  │ Sentence        │
│ PDF Extractor│  │  (AI Embeddings) │  │ Transformers    │
└──────────────┘  └──────────────────┘  └─────────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │   Slide Transcripts  │
                │   Matched Output     │
                └──────────────────────┘
```

## Features

- Extract text content from PDF lecture slides
- Process and parse transcript files
- AI-powered semantic matching using transformer embeddings
- Configurable similarity thresholds and window sizes
- Fully containerized with Docker
- REST API with modern web interface

## Prerequisites

- Docker and Docker Compose
- Or, for local development:
  - Python 3.9+
  - Node.js 16+

## Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pdf_parser_opensource
   ```

2. **Start the services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000

4. **Stop the services**
   ```bash
   docker-compose down
   ```

## API Usage

### Process Lecture Endpoint

**POST** `/process-lecture`

**Parameters:**
- `pdf_file` (file): PDF containing lecture slides
- `transcript_file` (file): Text file with transcripts
- `window_size` (int, optional): Window size for matching (default: 5)
- `similarity_threshold` (float, optional): Matching threshold 0-1 (default: 0.60)

**Example with curl:**
```bash
curl -X POST "http://localhost:8000/process-lecture?window_size=5&similarity_threshold=0.60" \
  -F "pdf_file=@lecture.pdf" \
  -F "transcript_file=@transcript.txt"
```

**Response:**
```json
{
  "success": true,
  "message": "Lecture processed successfully...",
  "data": {
    "slide_data": {
      "1": {
        "slide_number": 1,
        "content": "Slide content...",
        "transcripts": ["Matched transcript segments..."]
      }
    }
  }
}
```

## Project Structure

```
pdf_parser_opensource/
├── app.py                 # FastAPI main application
├── docker-compose.yml     # Docker orchestration
├── Dockerfile            # Backend container
├── requirements.txt      # Python dependencies
├── frontend/             # TypeScript web interface
│   ├── src/
│   ├── public/
│   └── Dockerfile
├── src/
│   ├── core/            # Embedding models
│   ├── extractors/      # PDF extraction
│   ├── processors/      # Transcript & matching logic
│   └── utils/           # Utility functions
└── lecture/             # Sample data directory
```

## Configuration

Adjust matching behavior by modifying these parameters:

- **window_size**: Number of transcript sentences to consider together (higher = more context)
- **similarity_threshold**: Minimum similarity score for matching (0.0-1.0, higher = stricter)

## Troubleshooting

**No transcripts matched to slides:**
- Try lowering `similarity_threshold` (e.g., 0.40-0.50)
- Ensure transcript content relates to slide content
- Check that both files uploaded correctly

**Out of memory errors:**
- Reduce PDF file size or number of pages
- For GPU support, install PyTorch with CUDA:
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
  ```

## License

MIT
