from typing import Dict, Optional, Any
from docling.document_converter import DocumentConverter
from PIL import Image
import io
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
        
        # Iterate through all pages in the document
        # doc.pages is a Dict[int, PageItem] where keys are page numbers
        for page_no in sorted(doc.pages.keys()):
            # Export content for this specific page using page_no parameter
            page_markdown = doc.export_to_markdown(page_no=page_no)
            
            # If vision model is available, analyze images on this page
            if self.vision_model is not None and self.vision_tokenizer is not None:
                try:
                    page_markdown = self._analyze_page_images(doc, page_no, page_markdown)
                except Exception as e:
                    logger.warning(f"Failed to analyze images on page {page_no}: {e}")
            
            page_contents[page_no] = page_markdown
        
        return page_contents
    
    def _analyze_page_images(self, doc: Any, page_no: int, page_markdown: str) -> str:
        """
        Analyze images on a page and append descriptions to the markdown content.
        
        Args:
            doc: Docling document object
            page_no: Page number to analyze
            page_markdown: Original markdown content
            
        Returns:
            Enhanced markdown content with image descriptions
        """
        page = doc.pages.get(page_no)
        if not page:
            logger.info(f"Page {page_no} not found in document")
            return page_markdown
        
        # Check if the page has any pictures/images
        if not hasattr(page, 'pictures') or not page.pictures:
            logger.info(f"Page {page_no} has no pictures attribute or no pictures")
            return page_markdown
        
        logger.info(f"Page {page_no} has {len(page.pictures)} picture(s) to analyze")
        image_descriptions = []
        
        # Iterate through all pictures on this page
        for idx, picture in enumerate(page.pictures, 1):
            try:
                # Get the image data from the picture object
                # Docling stores images as PIL Images or provides methods to get them
                if hasattr(picture, 'get_image'):
                    pil_image = picture.get_image(doc)
                elif hasattr(picture, 'image'):
                    pil_image = picture.image
                elif hasattr(picture, 'pil_image'):
                    pil_image = picture.pil_image
                else:
                    logger.warning(f"Could not extract image {idx} from page {page_no}")
                    continue
                
                if pil_image is None:
                    continue
                
                # Ensure it's a PIL Image
                if not isinstance(pil_image, Image.Image):
                    logger.warning(f"Image {idx} on page {page_no} is not a PIL Image")
                    continue
                
                # Analyze the image using the vision model
                logger.info(f"Analyzing image {idx} on page {page_no} using device: {self.vision_device}")
                enc_image = self.vision_model.encode_image(pil_image)
                if hasattr(enc_image, 'to'):
                    enc_image = enc_image.to(self.vision_device)
                question = "This is an image from a university lecture slide. Describe this image clearly, including any text, diagrams, charts, or key visual elements."
                description = self.vision_model.answer_question(enc_image, question, self.vision_tokenizer)
                logger.info(f"Generated description for image {idx}: {description[:100]}...")
                
                image_descriptions.append(f"**Image {idx} Description:** {description}")
                
            except Exception as e:
                logger.warning(f"Failed to analyze image {idx} on page {page_no}: {e}")
                continue
        
        # Append image descriptions to the markdown content if any were found
        if image_descriptions:
            page_markdown += "\n\n## Image Analysis\n\n"
            page_markdown += "\n\n".join(image_descriptions)
        
        return page_markdown