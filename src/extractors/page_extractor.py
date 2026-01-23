from typing import Dict, Optional, Any
from docling.document_converter import DocumentConverter
from PIL import Image
import io
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)


class PageContentExtractor:
    
    def __init__(self, vision_model=None, vision_tokenizer=None, vision_device=None):
        """Initialize the document converter.
        
        Args:
            vision_model: Optional vision model for image analysis
            vision_tokenizer: Optional tokenizer for the vision model
            vision_device: Optional device (cuda/cpu) for vision model
        """
        self.converter = DocumentConverter()
        self.vision_model = vision_model
        self.vision_tokenizer = vision_tokenizer
        self.vision_device = vision_device if vision_device else "cpu"
    
    def extract_pages(self, pdf_path: str) -> Dict[int, str]:
        """
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping page numbers to page content as markdown strings
            Example: {1: "Page 1 content...", 2: "Page 2 content...", ...}
        """
        # Convert pdf
        result = self.converter.convert(pdf_path)
        doc = result.document
        
        # Initialize dictionary
        page_contents = {}
        
        # Open PDF with fitz for image extraction (if vision model available)
        fitz_doc = None
        if self.vision_model is not None and self.vision_tokenizer is not None:
            try:
                fitz_doc = fitz.open(pdf_path)
                logger.info(f"Opened PDF with fitz for image extraction: {len(fitz_doc)} pages")
            except Exception as e:
                logger.warning(f"Failed to open PDF with fitz: {e}")
        
        # Iterate through all pages in the document
        # doc.pages is a Dict[int, PageItem] where keys are page numbers
        for page_no in sorted(doc.pages.keys()):
            # Export content for this specific page using page_no parameter
            page_markdown = doc.export_to_markdown(page_no=page_no)
            
            # If vision model is available, analyze images on this page using fitz
            if fitz_doc is not None and self.vision_model is not None and self.vision_tokenizer is not None:
                try:
                    page_markdown = self._analyze_page_images_fitz(fitz_doc, page_no, page_markdown)
                except Exception as e:
                    logger.warning(f"Failed to analyze images on page {page_no}: {e}")
            
            page_contents[page_no] = page_markdown
        
        # Close fitz document
        if fitz_doc is not None:
            fitz_doc.close()
        
        return page_contents
    
    def _analyze_page_images_fitz(self, fitz_doc: fitz.Document, page_no: int, page_markdown: str) -> str:
        """
        Analyze images on a page using fitz and append descriptions to the markdown content.
        
        Args:
            fitz_doc: Fitz document object
            page_no: Page number to analyze (1-indexed)
            page_markdown: Original markdown content (used as context for image analysis)
            
        Returns:
            Enhanced markdown content with image descriptions
        """
        # Convert to 0-indexed for fitz
        page_index = page_no - 1
        
        # Use the page_markdown as context for better image descriptions
        slide_context = page_markdown.strip() if page_markdown.strip() else "No text content found on this slide."
        
        if page_index < 0 or page_index >= len(fitz_doc):
            logger.warning(f"Page {page_no} out of range in fitz document")
            return page_markdown
        
        page = fitz_doc[page_index]
        images = page.get_images(full=True)
        
        if not images:
            logger.info(f"Page {page_no} has no images")
            return page_markdown
        
        logger.info(f"Page {page_no} has {len(images)} image(s) to analyze")
        image_descriptions = []
        
        # Process each image on the page
        for img_index, img in enumerate(images, 1):
            try:
                # Extract image using fitz
                xref = img[0]
                base_image = fitz_doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert bytes to PIL Image
                pil_image = Image.open(io.BytesIO(image_bytes))
                logger.info(f"Extracted image {img_index} from page {page_no}: {pil_image.size} {pil_image.mode}")
                
                # Analyze the image using moondream vision model
                logger.info(f"Analyzing image {img_index} on page {page_no} using device: {self.vision_device}")
                enc_image = self.vision_model.encode_image(pil_image)
                if hasattr(enc_image, 'to'):
                    enc_image = enc_image.to(self.vision_device)
                
                # Build question with slide context for better descriptions
                question = f"""This is an image from a university lecture slide. 

Slide text content:
{slide_context}

Based on the slide content above, describe this image clearly, including any text, diagrams, charts, or key visual elements. Explain how the image relates to the slide content."""
                
                description = self.vision_model.answer_question(enc_image, question, self.vision_tokenizer)
                logger.info(f"Generated description for image {img_index}: {description[:100]}...")
                
                # Format the description
                image_descriptions.append(f"**Image {img_index} Description:** {description}")
                
            except Exception as e:
                logger.warning(f"Failed to analyze image {img_index} on page {page_no}: {e}")
                continue
        
        # Append image descriptions to the markdown content if any were found
        if image_descriptions:
            page_markdown += "\n\n## Image Analysis\n\n"
            page_markdown += "\n\n".join(image_descriptions)
        
        return page_markdown