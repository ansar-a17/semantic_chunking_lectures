from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Optional

from src.extractors.page_extractor import PageContentExtractor
from src.processors.transcriptions import process_transcripts
from src.processors.build_data import build_transcripts
from src.processors.chunk_matcher import TranscriptSlideChunker
from src.core.embedding import model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Lecture Parser API",
    description="API for processing lecture PDFs and matching them with transcripts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "PDF Lecture Parser API is running",
        "version": "1.0.0"
    }


@app.post("/process-lecture")
async def process_lecture(
    pdf_file: UploadFile = File(..., description="PDF file containing lecture slides"),
    transcript_file: UploadFile = File(..., description="Text file containing transcripts"),
    window_size: int = 5,
    similarity_threshold: float = 0.60
):
    """
    Process a lecture PDF and transcript file to match transcripts with slides.
    
    Parameters:
    - pdf_file: PDF file with lecture slides
    - transcript_file: Text file with transcripts
    - window_size: Window size for chunk matching (default: 5)
    - similarity_threshold: Similarity threshold for matching (default: 0.60)
    
    Returns:
    - slide_data: Dictionary mapping slide numbers to content and transcripts
    - statistics: Processing statistics
    """
    
    # Validate file types
    if not pdf_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF file must have .pdf extension")
    
    if not transcript_file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Transcript file must have .txt extension")
    
    temp_pdf_path = None
    temp_transcript_path = None
    
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf_path = temp_pdf.name
            content = await pdf_file.read()
            temp_pdf.write(content)
            logger.info(f"Saved PDF to temporary file: {temp_pdf_path}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as temp_transcript:
            temp_transcript_path = temp_transcript.name
            content = await transcript_file.read()
            temp_transcript.write(content.decode('utf-8'))
            logger.info(f"Saved transcript to temporary file: {temp_transcript_path}")
        
        # Step 1: Extract slides from PDF
        logger.info("Step 1: Extracting slides from PDF")
        extractor = PageContentExtractor()
        pages = extractor.extract_pages(temp_pdf_path)
        logger.info(f"Extracted {len(pages)} pages")
        
        if not pages:
            raise HTTPException(status_code=400, detail="No pages could be extracted from PDF")
        
        # Step 2: Process transcripts and generate embeddings
        logger.info("Step 2: Processing transcripts")
        lines = process_transcripts(temp_transcript_path)
        transcripts = build_transcripts(lines)
        logger.info(f"Processed {len(transcripts)} transcript sentences")
        
        if not transcripts:
            raise HTTPException(status_code=400, detail="No transcripts could be processed from file")
        
        # Step 3: Match transcripts to slides and create chunks
        logger.info("Step 3: Matching transcripts to slides")
        chunker = TranscriptSlideChunker(model)
        chunks = chunker.build_chunks_with_windows(
            transcript_sentences=transcripts,
            slide_pages=pages,
            window_size=window_size,
            similarity_threshold=similarity_threshold
        )
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Step 4: Build simple dictionary structure
        logger.info("Step 4: Building data structure")
        slide_data = chunker.build_simple_dict(chunks, pages)
        
        # Check if any transcripts were matched
        matched_slides = sum(1 for _, (_, transcripts) in slide_data.items() if len(transcripts) > 0)
        total_transcripts = sum(len(transcripts) for _, (_, transcripts) in slide_data.items())
        
        if matched_slides == 0:
            logger.warning("No transcripts were matched to any slides. The similarity threshold may be too high or the content doesn't match.")
        
        # Prepare response
        response_data = {
            "success": True,
            "message": f"Lecture processed successfully. Matched {total_transcripts} transcript segments to {matched_slides} of {len(pages)} slides.",
            "data": {
                "slide_data": {
                    str(slide_num): {
                        "slide_number": slide_num,
                        "content": content,
                        "transcripts": transcripts
                    }
                    for slide_num, (content, transcripts) in slide_data.items()
                },
                "parameters": {
                    "window_size": window_size,
                    "similarity_threshold": similarity_threshold
                }
            }
        }
        
        logger.info("Processing completed successfully")
        return JSONResponse(content=response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing lecture: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing lecture: {str(e)}")
    
    finally:
        # Cleanup temporary files
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.unlink(temp_pdf_path)
                logger.info(f"Cleaned up temporary PDF file")
            except Exception as e:
                logger.warning(f"Could not delete temporary PDF file: {e}")
        
        if temp_transcript_path and os.path.exists(temp_transcript_path):
            try:
                os.unlink(temp_transcript_path)
                logger.info(f"Cleaned up temporary transcript file")
            except Exception as e:
                logger.warning(f"Could not delete temporary transcript file: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
