# Semantic chunking of slides.pdf and transcripts.txt

This is an open source version of a larger personal project. To build high-quality study material from lecture material, both the slides and the lecturer's words are important. Either one on it's own is not sufficient. At Tilburg University, we get access to the lecture slides and the lecture recording, which allows us to download the auto-generated transcripts of the lecture.

I built this semantic chunking algorithm to match the unstructured transcripts.txt with the lecture slides. Once this program has successfully chunked the data, it can be used for various purposes and you are guaranteed to have captured everything the lecture consisted of. This program effectively reconstructs what the teacher said while a specific slide was being shown.

## Features

- Extract text content from PDF lecture slides
- Process and parse transcript files
- Semantic matching using transformer embeddings
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
Note: The first build can take quite some time! Took around 15m for me.

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
