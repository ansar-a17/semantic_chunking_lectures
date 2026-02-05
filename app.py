from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import tempfile
import os
import json
import logging
from typing import Dict, List
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.extractors.page_extractor import PageContentExtractor
from src.processors.transcriptions import process_transcripts
from src.processors.build_data import build_transcripts
from src.processors.chunk_matcher import TranscriptSlideChunker
from src.core.embedding import model

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for vision model
vision_model = None
vision_tokenizer = None
vision_device = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - loads vision model at startup"""
    global vision_model, vision_tokenizer, vision_device
    
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    vision_device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device for vision model: {vision_device}")
    
    model_id = "vikhyatk/moondream2"
    logger.info("Loading Moondream2 vision model...")
    try:
        vision_model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
        ).to(vision_device)
        
        vision_tokenizer = AutoTokenizer.from_pretrained(model_id)
        logger.info("Vision model loaded successfully!")
    except Exception as e:
        logger.error(f"Failed to load vision model: {e}")
        logger.warning("Vision model endpoints will not be available")
    
    yield
    
    logger.info("Shutting down...")

app = FastAPI(
    title="PDF Lecture Parser API",
    description="API for processing lecture PDFs and matching them with transcripts",
    version="1.0.0",
    lifespan=lifespan
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
    transcript_files: List[UploadFile] = File(default=[], description="Optional: One or more text files containing transcripts (will be merged if multiple)"),
    window_size: int = Form(5),
    similarity_threshold: float = Form(0.60)
):
    """
    Process a lecture PDF and optionally match with transcript file(s).
    
    Parameters:
    - pdf_file: PDF file with lecture slides
    - transcript_files: Optional - One or more text files with transcripts (will be merged if multiple)
    - window_size: Window size for chunk matching (default: 5, only used with transcripts)
    - similarity_threshold: Similarity threshold for matching (default: 0.60, only used with transcripts)
    
    Returns:
    - slide_data: Dictionary mapping slide numbers to content and optionally transcripts
    - statistics: Processing statistics
    """
    
    # Validate file types
    if not pdf_file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF file must have .pdf extension")
    
    # Validate number of transcript files (0-2 allowed)
    if len(transcript_files) > 2:
        raise HTTPException(status_code=400, detail=f"Please provide 0, 1, or 2 transcript files. Received {len(transcript_files)} files.")
    
    # Validate all transcript files
    for transcript_file in transcript_files:
        if not transcript_file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail=f"Transcript file '{transcript_file.filename}' must have .txt extension")
    
    temp_pdf_path = None
    temp_transcript_paths = []
    
    try:
        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf_path = temp_pdf.name
            content = await pdf_file.read()
            temp_pdf.write(content)
            logger.info(f"Saved PDF to temporary file: {temp_pdf_path}")
        
        # Save all transcript files to temporary locations
        for i, transcript_file in enumerate(transcript_files):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8') as temp_transcript:
                temp_transcript_path = temp_transcript.name
                temp_transcript_paths.append(temp_transcript_path)
                content = await transcript_file.read()
                temp_transcript.write(content.decode('utf-8'))
                logger.info(f"Saved transcript file {i+1} ('{transcript_file.filename}') to: {temp_transcript_path}")
        
        # Step 1: Extract slides from PDF
        logger.info("Step 1: Extracting slides from PDF")
        if vision_model is not None:
            logger.info("Vision model available - will analyze images in slides")
            extractor = PageContentExtractor(vision_model=vision_model, vision_tokenizer=vision_tokenizer, vision_device=vision_device)
        else:
            logger.warning("Vision model not available - images will not be analyzed")
            extractor = PageContentExtractor()
        pages = extractor.extract_pages(temp_pdf_path)
        logger.info(f"Extracted {len(pages)} pages")
        
        if not pages:
            raise HTTPException(status_code=400, detail="No pages could be extracted from PDF")
        
        # Check if transcripts are provided
        has_transcripts = len(temp_transcript_paths) > 0
        
        if has_transcripts:
            # Step 2: Process transcripts and generate embeddings
            logger.info(f"Step 2: Processing {len(temp_transcript_paths)} transcript file(s)")
            lines = process_transcripts(temp_transcript_paths)
            transcripts = build_transcripts(lines)
            logger.info(f"Processed {len(transcripts)} transcript sentences from {len(temp_transcript_paths)} file(s)")
            
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
            slide_data, unmatched_transcripts = chunker.build_simple_dict(chunks, pages, lines)
            
            # Check if any transcripts were matched
            matched_slides = sum(1 for _, (_, transcripts) in slide_data.items() if len(transcripts) > 0)
            total_transcripts = sum(len(transcripts) for _, (_, transcripts) in slide_data.items())
            
            if matched_slides == 0:
                logger.warning("No transcripts were matched to any slides. The similarity threshold may be too high or the content doesn't match.")
            
            logger.info(f"Matched {total_transcripts} transcript segments, {len(unmatched_transcripts)} unmatched")
        else:
            # No transcripts provided - build structure with only slide content
            logger.info("Step 2: No transcript files provided - building slide-only data structure")
            slide_data = {page_num: (content, []) for page_num, content in pages.items()}
            unmatched_transcripts = []
            matched_slides = 0
            total_transcripts = 0
        
        # Prepare response
        if has_transcripts:
            message = f"Lecture processed successfully. Matched {total_transcripts} transcript segments to {matched_slides} of {len(pages)} slides. {len(unmatched_transcripts)} transcripts unmatched."
        else:
            message = f"Lecture processed successfully. Extracted {len(pages)} slides (no transcripts provided)."
        
        response_data = {
            "success": True,
            "message": message,
            "data": {
                "slide_data": {
                    str(slide_num): {
                        "slide_number": slide_num,
                        "content": content,
                        "transcripts": transcripts
                    }
                    for slide_num, (content, transcripts) in slide_data.items()
                },
                "unmatched_transcripts": unmatched_transcripts,
                "parameters": {
                    "window_size": window_size,
                    "similarity_threshold": similarity_threshold
                },
                "has_transcripts": has_transcripts
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
        
        for temp_transcript_path in temp_transcript_paths:
            if temp_transcript_path and os.path.exists(temp_transcript_path):
                try:
                    os.unlink(temp_transcript_path)
                    logger.info(f"Cleaned up temporary transcript file")
                except Exception as e:
                    logger.warning(f"Could not delete temporary transcript file: {e}")


@app.post("/convert-to-markdown")
async def convert_to_markdown(
    json_file: UploadFile = File(..., description="JSON file from process-lecture endpoint")
):
    """
    Convert a JSON result file to markdown format.
    
    Parameters:
    - json_file: JSON file from the process-lecture endpoint
    
    Returns:
    - Markdown formatted content
    """
    try:
        content = await json_file.read()
        data = json.loads(content.decode('utf-8'))
        
        if not data.get("success"):
            raise HTTPException(status_code=400, detail="Invalid JSON format or processing failed")
        
        slide_data = data.get("data", {}).get("slide_data", {})
        
        if not slide_data:
            raise HTTPException(status_code=400, detail="No slide data found in JSON")
        
        # Convert dictionary to markdown
        markdown_content = convert_slide_data_to_markdown(slide_data)
        
        return {
            "success": True,
            "markdown": markdown_content,
            "message": f"Successfully converted {len(slide_data)} slides to markdown"
        }
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error converting to markdown: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error converting to markdown: {str(e)}")


def _clean_slide_content(content: str) -> str:
    """Clean and format slide content by removing markdown artifacts."""
    lines = []
    
    for line in content.split("\n"):
        line = line.strip()
        
        # Skip empty lines at the start
        if not line and not lines:
            continue
        
        # Skip image and formula comments
        if line in ["<!-- image -->", "<!-- formula-not-decoded -->"]:
            continue
        
        # Convert Image Analysis heading to H3 (###)
        if line == "## Image Analysis":
            line = "### Image Analysis"
        # Remove other markdown heading symbols (##) but keep the text content
        elif line.startswith("##"):
            line = line.lstrip("#").strip()
        
        # Remove bold markdown (**) from text
        if "**" in line:
            line = line.replace("**", "")
        
        # Remove bullet points from markdown lists (optional - keep if you want structure)
        # if line.startswith("- "):
        #     line = line[2:]
        
        if line:  # Only add non-empty lines
            lines.append(line)
    
    return "\n".join(lines)


def convert_slide_data_to_markdown(slide_data: Dict) -> str:
    """
    Convert slide data dictionary to markdown format.
    
    Args:
        slide_data: Dictionary with slide data in format {slide_num: {"slide_number": int, "content": str, "transcripts": list}}
    
    Returns:
        Markdown formatted string with proper headings and cleaned content
    """
    results = []
    
    for slide_num in sorted(slide_data.keys(), key=lambda x: int(x)):
        slide_info = slide_data[slide_num]
        slide_number = slide_info["slide_number"]
        slide_content = _clean_slide_content(slide_info["content"])
        slide_transcripts = slide_info["transcripts"]
        
        # Format with proper markdown headings (H1 for slide number, H2 for sections)
        result = f"# slide number {slide_number}\n\n## slide_content\n\n{slide_content}"
        
        # Only add transcript section if transcripts exist
        if slide_transcripts and len(slide_transcripts) > 0:
            transcripts_text = "\n".join(slide_transcripts)
            result += f"\n\n## slide_transcripts\n{transcripts_text}"
        
        result += "\n" + "_"*80 + "\n"
        results.append(result)
    
    return "\n".join(results)
