#!/usr/bin/env python3
"""
Robust Question Parser for GCP Exam Question Extractor
Completely rewritten with proper question boundary detection and community separation
"""

import sys
import os
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import pdfplumber

@dataclass
class CleanQuestion:
    """Data structure for a properly cleaned question"""
    id: str
    number: str
    description: str
    options: Dict[str, str] = field(default_factory=dict)
    case_study_info: str = ""
    page_number: int = 0
    source_file: str = ""
    confidence_score: float = 0.0
    
    # Community data (separated)
    community_answer: str = ""
    highly_voted_answer: str = ""  
    most_recent_answer: str = ""
    all_community_comments: str = ""  # Raw comments content
    
    # Raw data for analysis
    raw_pdf_text: str = ""
    raw_extracted_text: str = ""

@dataclass
class CommunityComment:
    """Separated community comment"""
    question_id: str
    username: str
    content: str
    timestamp: str
    vote_count: int = 0
    vote_type: str = ""

class RobustQuestionParser:
    def __init__(self):
        self.setup_logging()
        self.setup_patterns()
        self.questions = []
        self.community_comments = []
        
    def setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_patterns(self):
        """Setup robust patterns for parsing"""
        
        # Question start patterns (PRIMARY BOUNDARY DETECTION)
        self.question_start_patterns = [
            r'Question\s*#(\d+)\s+Topic\s+\d+',
            r'Question\s*#(\d+)',
        ]
        
        # Case study patterns (enhanced for introductory info detection)
        self.case_study_patterns = [
            r'For this question, refer to the (.+) case study',
            r'(.+) is a (.+) company',
            r'Company Overview\s*-?\s*([^\n]+)',
            r'Solution Concept\s*-?\s*([^\n]+)', 
            r'Business Requirements\s*-?\s*([^\n]+)',
            r'Technical Requirements\s*-?\s*([^\n]+)',
            r'Existing Technical Environment\s*-?\s*([^\n]+)',
            r'Executive Statement\s*-?\s*([^\n]+)',
        ]
        
        # Answer option patterns
        self.answer_option_patterns = [
            r'([A-F])\.\s*([^\n\uf147]+?)(?=\n[A-F]\.|$|\uf147)',
            r'([A-F])\.\s*(.+?)(?=\n[A-F]\.|$|\uf147)',
            r'([A-F])\.\s*([^.\n]{5,200}?)(?=\n[A-F]\.|$|\uf147)',
        ]
        
        # Community comment start patterns
        self.community_start_patterns = [
            r'\uf147\s*\uf007',
            r'\b[A-Za-z][A-Za-z0-9_]{2,}\s+(Highly\s+Voted|Most\s+Recent)\s+',
            r'\b[A-Za-z][A-Za-z0-9_]{2,}\s+\d+\s+(years?|months?|weeks?|days?)\s+ago',
            r'upvoted\s+\d+\s+times?',
            r'Selected\s+Answer:',
            r'Highly\s+Voted',
            r'Most\s+Recent',
        ]
        
        # OCR correction patterns
        self.ocr_corrections = {
            r'ConKgure': 'Configure',
            r'ReconKgure': 'Reconfigure', 
            r'traOc': 'traffic',
            r'solu"on': 'solution',
            r'applica"on': 'application',
            r'ques"on': 'question',
            r'informa"on': 'information',
            r'migra"on': 'migration',
            r'opera"ons': 'operations',
            r'Data\^ow': 'Dataflow',
            r'Data"ow': 'Dataflow',
            r'\^at\s+Kles': 'flat files',
            r'modiKed': 'modified',
            r'deKne': 'define',
            r'Knd': 'find',
            r'KreVox': 'Firefox',
            r'Profess"onal': 'Professional',
        }
    
    def extract_questions_from_pdf(self, pdf_path: str) -> List[CleanQuestion]:
        """Extract clean questions from PDF with robust boundary detection"""
        self.logger.info(f"🔍 Processing PDF: {os.path.basename(pdf_path)}")
        
        questions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # First, try to extract as individual pages
                all_pages_text = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    self.logger.debug(f"  Processing page {page_num}")
                    
                    # Extract text with layout preservation
                    raw_text = page.extract_text(layout=True)
                    if not raw_text:
                        continue
                    
                    # Accumulate all text for cross-page parsing
                    all_pages_text += f"\n--- PAGE {page_num} ---\n" + raw_text
                    
                    # Find and extract questions from this page
                    page_questions = self._extract_questions_from_page_text(
                        raw_text, page_num, os.path.basename(pdf_path)
                    )
                    questions.extend(page_questions)
                
                # If no questions found, try parsing entire PDF as one unit (for case studies)
                if len(questions) == 0 and all_pages_text:
                    self.logger.info(f"  No questions found in individual pages, trying full PDF parsing...")
                    full_questions = self._extract_questions_from_full_pdf_text(
                        all_pages_text, os.path.basename(pdf_path)
                    )
                    questions.extend(full_questions)
                    
        except Exception as e:
            self.logger.error(f"❌ Error processing {pdf_path}: {e}")
            
        self.logger.info(f"✅ Extracted {len(questions)} clean questions from {os.path.basename(pdf_path)}")
        return questions
    
    def _extract_questions_from_full_pdf_text(self, full_text: str, source_file: str) -> List[CleanQuestion]:
        """Extract questions from full PDF text (for case studies spanning multiple pages)"""
        questions = []
        
        # Clean the text first
        full_text = self._clean_unicode_artifacts(full_text)
        
        # Extract the case study info from the full text
        intro_info = self._extract_introductory_info(full_text)
        
        # Enhanced pattern for case study questions - capture everything after case study
        case_study_match = re.search(r'For this question, refer to the (.+?) case study\.?\s*(.*)', full_text, re.DOTALL | re.IGNORECASE)
        
        if case_study_match:
            case_study_name = case_study_match.group(1).strip()
            question_section = case_study_match.group(2).strip()
            
            self.logger.info(f"  Found case study reference: {case_study_name}")
            
            # Find where the options end and community comments begin
            community_start_match = re.search(r'(upvoted|\bHighly\s+Voted|\bMost\s+Recent|\b[A-Za-z][A-Za-z0-9_]{2,}\s+\d+\s+(years?|months?|weeks?|days?)\s+ago)', question_section, re.IGNORECASE)
            
            if community_start_match:
                options_section = question_section[:community_start_match.start()].strip()
                community_section = question_section[community_start_match.start():].strip()
            else:
                options_section = question_section
                community_section = ""
            
            # Split by option letters to extract options from clean section
            parts = re.split(r'([A-F]\.)\s*', options_section)[1:]  # Skip first empty part
            option_matches = []
            
            # Group pairs (letter, content)
            for i in range(0, len(parts) - 1, 2):
                if i + 1 < len(parts):
                    letter = parts[i].replace('.', '')  # Remove dot
                    content = parts[i + 1].strip()
                    # Clean any remaining artifacts from options
                    content = re.sub(r'(upvoted|\bHighly\s+Voted|\bMost\s+Recent).*$', '', content, flags=re.IGNORECASE | re.DOTALL).strip()
                    if content:  # Only add non-empty content
                        option_matches.append((letter, content))
            
            if len(option_matches) >= 2:  # Must have at least 2 options
                # Extract the question description (everything before option A)
                desc_match = re.search(r'^(.*?)(?=A\.)', question_section, re.DOTALL)
                if desc_match:
                    description = desc_match.group(1).strip()
                else:
                    # Fallback: use first part of question section
                    description = question_section.split('A.')[0].strip()
                
                # Build options dictionary
                options = {}
                for letter, text in option_matches:
                    # Clean up the option text
                    cleaned_text = re.sub(r'\s+', ' ', text.strip())
                    options[letter] = cleaned_text
                
                if len(description) > 10 and len(options) >= 2:
                    # Create the question
                    question = CleanQuestion(
                        id=f"case_study_{case_study_name.lower().replace(' ', '_')}_1",
                        number="1",
                        description=f"For this question, refer to the {case_study_name} case study. {description}",
                        options=options,
                        case_study_info=intro_info,
                        page_number=1,
                        source_file=source_file,
                        confidence_score=0.85,
                        raw_pdf_text=full_text[:1000],
                        raw_extracted_text=options_section[:1000]
                    )
                    
                    # Extract community data from the separated community section
                    self._extract_community_answers_from_text(question, community_section)
                    
                    questions.append(question)
                    self.logger.info(f"✅ Extracted case study question: {len(options)} options found")
        
        return questions
    
    def _extract_introductory_info(self, text: str) -> str:
        """Extract introductory information/case study from text"""
        intro_info = ""
        
        # Introductory info section patterns (enhanced for case studies)
        intro_patterns = [
            r'Introductory Info\s*([\s\S]*?)(?=Question\s*#?\d+|$)',
            r'Company Overview\s*-?\s*([\s\S]*?)(?=Solution Concept|Question|$)',
            r'(For this question, refer to the Dress4Win case study[\s\S]*?)(?=Question\s*#?\d+|$)',
            r'(Dress4Win[\s\S]*?)(?=Question|$)',
            r'(TerramEarth[\s\S]*?)(?=Question|$)',
            r'(Mountkirk Games[\s\S]*?)(?=Question|$)',
            # Pattern for case studies that span multiple pages
            r'([\s\S]*?Redis.*?server cluster[\s\S]*?capital expenditure[\s\S]*?)(?=Question|$)',
        ]
        
        # Look for introductory info patterns
        for pattern in intro_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                intro_info = match.group(1).strip()
                break
                
        # Clean up the extracted info
        if intro_info:
            # Remove excessive whitespace
            intro_info = re.sub(r'\s+', ' ', intro_info)
            # Remove common PDF artifacts
            intro_info = re.sub(r'Page\s+\d+', '', intro_info)
            intro_info = re.sub(r'ExamTopics[^\n]*', '', intro_info)
            intro_info = intro_info.strip()
            
        return intro_info[:2000]  # Limit to 2000 characters
    
    def _extract_questions_from_page_text(self, text: str, page_num: int, source_file: str) -> List[CleanQuestion]:
        """Extract questions from individual page text"""
        questions = []
        
        # Clean the text first
        text = self._clean_unicode_artifacts(text)
        
        # Look for question patterns
        for pattern in self.question_start_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for i, match in enumerate(matches):
                question_start = match.start()
                
                # Determine question end (next question or end of text)
                if i + 1 < len(matches):
                    question_end = matches[i + 1].start()
                    question_text = text[question_start:question_end]
                else:
                    question_text = text[question_start:]
                
                # Extract question components
                question = self._parse_single_question(question_text, match.group(1), page_num, source_file)
                if question:
                    questions.append(question)
        
        return questions
    
    def _parse_single_question(self, question_text: str, question_number: str, page_num: int, source_file: str) -> Optional[CleanQuestion]:
        """Parse a single question from text"""
        
        # Extract description (everything before first option)
        desc_match = re.search(r'Question\s*#?\d+[^\n]*\n(.*?)(?=\n[A-F]\.|$)', question_text, re.DOTALL)
        if not desc_match:
            return None
            
        description = desc_match.group(1).strip()
        
        # Extract options
        options = {}
        for pattern in self.answer_option_patterns:
            option_matches = re.finditer(pattern, question_text, re.MULTILINE | re.DOTALL)
            for match in option_matches:
                letter, text = match.groups()
                if letter and text:
                    options[letter] = text.strip()
        
        # Must have at least 2 options and meaningful description
        if len(options) < 2 or len(description.strip()) < 10:
            return None
        
        # Create question object
        question = CleanQuestion(
            id=f"Q{page_num}_{question_number}",
            number=question_number,
            description=description,
            options=options,
            page_number=page_num,
            source_file=source_file,
            confidence_score=0.8,
            raw_pdf_text=question_text[:1000],
            raw_extracted_text=question_text[:1000]
        )
        
        # Extract community answers
        community_section = question_text[desc_match.end():]
        self._extract_community_answers_from_text(question, community_section)
        
        return question
    
    def _extract_community_answers_from_text(self, question: CleanQuestion, community_text: str):
        """Extract community answers from text"""
        
        # Store all raw community comments for display
        question.all_community_comments = community_text.strip()
        
        # Look for answer patterns
        highly_voted_match = re.search(r'Highly\s+Voted[^A-F]*([A-F])', community_text, re.IGNORECASE)
        if highly_voted_match:
            question.highly_voted_answer = highly_voted_match.group(1)
        
        most_recent_match = re.search(r'Most\s+Recent[^A-F]*([A-F])', community_text, re.IGNORECASE)
        if most_recent_match:
            question.most_recent_answer = most_recent_match.group(1)
        
        # Generic community answer
        answer_match = re.search(r'Selected\s+Answer:\s*([A-F])', community_text, re.IGNORECASE)
        if answer_match:
            question.community_answer = answer_match.group(1)
        elif question.highly_voted_answer:
            question.community_answer = question.highly_voted_answer
        elif question.most_recent_answer:
            question.community_answer = question.most_recent_answer
    
    def _clean_unicode_artifacts(self, text: str) -> str:
        """Clean Unicode artifacts from text"""
        if not text:
            return text
        
        # Remove specific problematic Unicode characters
        text = text.replace('\uf147', '').replace('\uf007', '').replace('\uf0c9', '')
        text = text.replace('\u2588', '').replace('\u2590', '').replace('\u2591', '')
        
        # Remove other Unicode symbols in private use areas
        text = re.sub(r'[\uf000-\uf8ff]', '', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

def main():
    """Simple test function"""
    parser = RobustQuestionParser()
    questions = parser.extract_questions_from_pdf('./data/input/Questions_40.pdf')
    print(f'Extracted {len(questions)} questions')
    for q in questions:
        print(f'Q{q.number}: {q.description[:100]}...')
        print(f'  Options: {list(q.options.keys())}')
        print()

if __name__ == "__main__":
    main()