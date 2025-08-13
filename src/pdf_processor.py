"""
PDF Processing Module for GCP Exam Question Extractor
Handles PDF text extraction, page management, and text cleaning
"""

import os
import re
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import pdfplumber
from dataclasses import dataclass

@dataclass
class PageContent:
    page_number: int
    text: str
    source_file: str
    raw_text: str

class PDFProcessor:
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from project config"""
        import json
        if config_path is None:
            config_path = "./project_config.json"
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Default configuration if config file is not found"""
        return {
            "paths": {
                "input_directory": "./data/input",
                "output_directory": "./data/output"
            },
            "pdf_processing": {
                "file_pattern": "Questions_*.pdf",
                "batch_size": 3,
                "encoding": "utf-8"
            }
        }
    
    def extract_text_from_pdf(self, file_path: str, page_range: Optional[Tuple[int, int]] = None) -> List[PageContent]:
        """
        Extract text from PDF file with page tracking
        
        Args:
            file_path: Path to the PDF file
            page_range: Optional tuple of (start_page, end_page) for selective extraction
            
        Returns:
            List of PageContent objects with extracted text
        """
        pages = []
        source_file = os.path.basename(file_path)
        
        try:
            self.logger.info(f"Starting PDF extraction from {source_file}")
            
            # Use pdfplumber for better text extraction
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"Total pages in {source_file}: {total_pages}")
                
                start_page = page_range[0] if page_range else 0
                end_page = page_range[1] if page_range else total_pages
                
                for page_num in range(start_page, min(end_page, total_pages)):
                    try:
                        page = pdf.pages[page_num]
                        raw_text = page.extract_text()
                        
                        if raw_text:
                            cleaned_text = self.clean_pdf_artifacts(raw_text)
                            
                            page_content = PageContent(
                                page_number=page_num + 1,  # 1-based indexing
                                text=cleaned_text,
                                source_file=source_file,
                                raw_text=raw_text
                            )
                            pages.append(page_content)
                            
                            self.logger.debug(f"Extracted text from page {page_num + 1} ({len(cleaned_text)} chars)")
                        else:
                            self.logger.warning(f"No text found on page {page_num + 1} in {source_file}")
                            
                    except Exception as e:
                        self.logger.error(f"Error extracting page {page_num + 1} from {source_file}: {str(e)}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error opening PDF file {file_path}: {str(e)}")
            raise
        
        self.logger.info(f"Successfully extracted {len(pages)} pages from {source_file}")
        return pages
    
    def clean_pdf_artifacts(self, text: str) -> str:
        """
        Clean PDF extraction artifacts and unwanted elements
        
        Args:
            text: Raw text from PDF extraction
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Get ignore elements from config
        ignore_elements = self.config.get("pdf_processing", {}).get("ignore_elements", [])
        
        # Remove URLs (ExamTopics specific)
        text = re.sub(r'https://www\.examtopics\.com[^\s]*', '', text)
        
        # Remove page numbers at the beginning/end of lines
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'Page \d+', '', text, flags=re.IGNORECASE)
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines
        text = re.sub(r' {3,}', '  ', text)  # Multiple spaces
        
        # Fix broken words across lines (common in PDF extraction)
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Standardize line breaks
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        # Remove standalone single characters that are likely OCR errors
        text = re.sub(r'\n[a-zA-Z]\n', '\n', text)
        
        return text.strip()
    
    def identify_question_boundaries(self, pages: List[PageContent]) -> List[Dict]:
        """
        Identify question boundaries across pages
        
        Args:
            pages: List of PageContent objects
            
        Returns:
            List of dictionaries with question boundary information
        """
        questions = []
        current_question = None
        
        for page in pages:
            text_lines = page.text.split('\n')
            
            for i, line in enumerate(text_lines):
                line_stripped = line.strip()
                
                # Look specifically for "Question #N" patterns (the actual question markers)
                if re.search(r'Question\s*#\s*\d+', line_stripped, re.IGNORECASE):
                    # Save previous question if exists
                    if current_question:
                        questions.append(current_question)
                    
                    # Start new question - collect context from previous lines and following lines
                    context_lines = []
                    
                    # Add extensive previous lines as context for case studies like Dress4Win
                    start_context = max(0, i - 20)  # Look back 20 lines for more context
                    for ctx_i in range(start_context, i):
                        ctx_line = text_lines[ctx_i].strip()
                        # Include substantial context but skip headers/artifacts
                        if (ctx_line and 
                            len(ctx_line) > 15 and  # Substantial content
                            not re.search(r'ExamTopics|Profess.*onal|Selected Answer:|^\d+\s*$|Page \d+', ctx_line, re.IGNORECASE) and
                            not re.search(r'^\w+\s+\d+\s+(months?|weeks?|days?)\s+ago', ctx_line, re.IGNORECASE)):  # Skip user timestamps
                            context_lines.append(ctx_line)
                    
                    # Add the question line itself
                    context_lines.append(line_stripped)
                    
                    # Add following lines until next question or end of meaningful content
                    for j in range(i + 1, min(len(text_lines), i + 50)):  # Look ahead 50 lines max
                        next_line = text_lines[j].strip()
                        if next_line:
                            # Stop if we hit another question
                            if re.search(r'Question\s*#\s*\d+', next_line, re.IGNORECASE):
                                break
                            context_lines.append(next_line)
                    
                    current_question = {
                        'start_page': page.page_number,
                        'start_line': i,
                        'question_header': line_stripped,
                        'content_lines': context_lines,
                        'source_file': page.source_file,
                        'full_content': '\n'.join(context_lines)
                    }
        
        # Add the last question
        if current_question:
            questions.append(current_question)
        
        self.logger.info(f"Identified {len(questions)} question boundaries")
        return questions
    
    def process_pdf_batch(self, pdf_directory: str = None) -> List[PageContent]:
        """
        Process all PDF files in the specified directory
        
        Args:
            pdf_directory: Directory containing PDF files
            
        Returns:
            List of all extracted PageContent objects
        """
        if pdf_directory is None:
            pdf_directory = self.config["paths"]["input_directory"]
        
        pdf_directory = Path(pdf_directory)
        file_pattern = self.config["pdf_processing"]["file_pattern"]
        
        self.logger.info(f"Processing PDFs in directory: {pdf_directory}")
        self.logger.info(f"File pattern: {file_pattern}")
        
        # Find all PDF files matching the pattern
        pdf_files = list(pdf_directory.glob(file_pattern))
        pdf_files.sort()  # Ensure consistent ordering
        
        if not pdf_files:
            self.logger.warning(f"No PDF files found matching pattern '{file_pattern}' in {pdf_directory}")
            return []
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        all_pages = []
        
        for pdf_file in pdf_files:
            try:
                self.logger.info(f"Processing file: {pdf_file.name}")
                pages = self.extract_text_from_pdf(str(pdf_file))
                all_pages.extend(pages)
                
                self.logger.info(f"Completed processing {pdf_file.name}: {len(pages)} pages extracted")
                
            except Exception as e:
                self.logger.error(f"Failed to process {pdf_file.name}: {str(e)}")
                continue
        
        self.logger.info(f"Batch processing completed: {len(all_pages)} total pages extracted")
        return all_pages
    
    def save_extracted_text(self, pages: List[PageContent], output_file: str = None) -> str:
        """
        Save extracted text to file for review/debugging
        
        Args:
            pages: List of PageContent objects
            output_file: Output file path
            
        Returns:
            Path to saved file
        """
        if output_file is None:
            output_dir = Path(self.config["paths"]["output_directory"])
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "extracted_text.txt"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for page in pages:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"FILE: {page.source_file} | PAGE: {page.page_number}\n")
                    f.write(f"{'='*50}\n")
                    f.write(page.text)
                    f.write(f"\n{'='*50}\n")
            
            self.logger.info(f"Extracted text saved to: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error saving extracted text: {str(e)}")
            raise