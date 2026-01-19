"""
Page-by-Page Content Extractor for Docling Documents

This module provides functionality to extract content from PDF files
organized by page number using Docling's document parsing capabilities.
"""

from typing import Dict
from docling.document_converter import DocumentConverter


class PageContentExtractor:
    """Extract and organize PDF content by page number."""
    
    def __init__(self):
        """Initialize the document converter."""
        self.converter = DocumentConverter()
    
    def extract_pages(self, pdf_path: str) -> Dict[int, str]:
        """
        Extract content from a PDF file organized by page number.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary mapping page numbers to page content as markdown strings
            Example: {1: "Page 1 content...", 2: "Page 2 content...", ...}
        """
        # Convert the PDF document
        result = self.converter.convert(pdf_path)
        doc = result.document
        
        # Initialize page content dictionary
        page_contents = {}
        
        # Iterate through all pages in the document
        # doc.pages is a Dict[int, PageItem] where keys are page numbers
        for page_no in sorted(doc.pages.keys()):
            # Export content for this specific page using page_no parameter
            page_markdown = doc.export_to_markdown(page_no=page_no)
            page_contents[page_no] = page_markdown
        
        return page_contents
    
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        Get the total number of pages in a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Number of pages in the document
        """
        result = self.converter.convert(pdf_path)
        doc = result.document
        return len(doc.pages)