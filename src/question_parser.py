"""
Question Parser Module for GCP Exam Question Extractor
Handles question structure parsing, answer extraction, and community response analysis
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class CommunityComment:
    """Data structure for community comments"""
    question_id: str = ""
    username: str = ""
    content: str = ""
    timestamp: str = ""
    vote_count: int = 0
    vote_type: str = ""  # 'Highly Voted', 'Most Recent', 'Selected Answer'
    page_number: int = 0
    source: str = ""

@dataclass
class Question:
    """Data structure for a parsed question"""
    unique_id: str = ""
    original_number: str = ""
    description: str = ""
    options: Dict[str, str] = field(default_factory=dict)
    community_answer: str = ""
    highly_voted_answer: str = ""
    most_recent_answer: str = ""
    claude_answer: str = ""
    claude_reasoning: str = ""
    latest_date: str = ""
    topic: str = ""
    page_number: int = 0
    confidence_score: float = 0.0
    source: str = ""
    raw_content: str = ""
    source_pdf_path: str = ""  # Path to original PDF for hyperlinking
    introductory_info: str = ""  # Case study information
    has_claude_answer: bool = False  # Flag for filtering

class QuestionParser:
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.question_counter = 0
        self.community_comments = []  # Store extracted community comments
        self.setup_community_patterns()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        if config_path is None:
            config_path = "./project_config.json"
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Default configuration"""
        return {
            "question_parsing": {
                "question_markers": ["Question #\\d+", "Topic \\d+"],
                "option_patterns": ["^[A-F]\\.", "^[A-F]\\)", "^[A-F]\\s+"],
                "community_answer_indicators": ["Selected Answer:", "Highly Voted", "Most Recent"],
                "minimum_question_length": 50,
                "maximum_options": 6
            }
        }
    
    def setup_community_patterns(self):
        """Setup patterns for community comment detection"""
        # Community comment indicators (NEVER include in questions)
        # Based on debug analysis: Unicode symbols \uf147 \uf007 precede usernames
        self.community_indicators = [
            # Unicode symbols (most reliable indicator from debug analysis)
            r'\uf147\s*\uf007',  # Unicode symbols that start community comments
            
            # Username + timestamp patterns
            r'^(\s*)[A-Za-z][A-Za-z0-9_]{2,}\s+\d+\s+(years?|months?|weeks?|days?),?\s*(\d+\s+(months?|weeks?|days?))?\s+ago',
            
            # Direct vote type indicators (enhanced)
            r'(Selected Answer|Highly Voted|Most Recent|Community Answer):\s*',
            r'Highly\s+Voted',  # Direct pattern
            r'Most\s+Recent',   # Direct pattern
            
            # Image/button indicators
            r'^(\s*)[▶▼►◄⬅➡🔘□■📷🖼📸]',
            
            # Known usernames pattern (expanded)
            r'^(\s*)(Ahmed_Safwat|SAMBIT|kopper2019|ChinaSailor|AzureDP900|minmin2020|megumin|Mahmoud_E|holerina|BiddlyBdoyng|nagibator163|Ausias18|lynx256|practicioner|gcparchitect007|Kabiliravi|ry9280087|mlantonis|roastc|hems4all|AdityaGupta|zzaric|Rightsaidfred|bnlcnd|joe2211|PeppaPig|sjmsummer|vincy2202|AniketD|mifrah|JC0926|belly265)',
            
            # URL patterns
            r'https?://[^\s]+',
            
            # Quote/comment style
            r'^(\s*)[>|\\-]\s*',
            
            # Upvoted patterns (enhanced)
            r'upvoted\s+\d+\s+times?',
            r'upvoted\s+\d+',  # Simple upvoted pattern
            
            # Generic username patterns (more flexible)
            r'^(\s*)[A-Za-z][A-Za-z0-9_]{2,}\s+(Highly\s+Voted|Most\s+Recent)\s+',
            r'^(\s*)[A-Za-z][A-Za-z0-9_]{2,}\s+\d+\s+(years?|months?|weeks?|days?)\s+ago',
        ]
    
    def parse_question_structure(self, text_block: str, page_number: int, source_file: str, source_pdf_path: str = "") -> Optional[Question]:
        """
        Parse a text block into a structured Question object
        
        Args:
            text_block: Text containing the question
            page_number: Source page number
            source_file: Source PDF filename
            
        Returns:
            Parsed Question object or None if parsing fails
        """
        if not text_block or len(text_block.strip()) < self.config["question_parsing"]["minimum_question_length"]:
            return None
        
        try:
            question = Question()
            question.page_number = page_number
            question.source = source_file
            question.raw_content = text_block
            question.source_pdf_path = source_pdf_path
            
            # Extract question number and generate unique ID
            question_number = self._extract_question_number(text_block)
            if question_number:
                question.original_number = question_number
                question.unique_id = f"Q{page_number}_{question_number}"
            else:
                self.question_counter += 1
                question.unique_id = f"Q{page_number}_{self.question_counter}"
            
            # Extract topic
            question.topic = self._extract_topic(text_block)
            
            # Parse question description
            question.description = self._extract_question_description(text_block)
            
            # Parse answer options
            question.options = self._extract_answer_options(text_block)
            
            # Parse community responses
            community_data = self._parse_community_responses(text_block)
            question.community_answer = community_data.get('community_answer', '')
            question.highly_voted_answer = community_data.get('highly_voted', '')
            question.most_recent_answer = community_data.get('most_recent', '')
            question.latest_date = community_data.get('latest_date', '')
            
            # Extract and separate community comments
            question_text, extracted_comments = self._separate_community_comments(
                text_block, question.unique_id, page_number, source_file
            )
            
            # Store community comments
            self.community_comments.extend(extracted_comments)
            
            # Set Claude answer flag
            question.has_claude_answer = bool(question.claude_answer)
            
            # Calculate confidence score
            question.confidence_score = self._calculate_confidence(question)
            
            self.logger.debug(f"Parsed question: {question.unique_id} with {len(extracted_comments)} community comments")
            return question
            
        except Exception as e:
            self.logger.error(f"Error parsing question structure: {str(e)}")
            return None
    
    def _extract_question_number(self, text: str) -> Optional[str]:
        """Extract question number from text"""
        patterns = [
            r'Question\s*#(\d+)',
            r'Question\s+(\d+)',
            r'(\d+)\.\s',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_topic(self, text: str) -> str:
        """Extract topic information from text"""
        topic_match = re.search(r'Topic\s+(\d+)', text, re.IGNORECASE)
        if topic_match:
            return f"Topic {topic_match.group(1)}"
        
        # Try to infer topic from content keywords
        gcp_services = [
            'Compute Engine', 'Cloud Storage', 'BigQuery', 'Cloud SQL',
            'Kubernetes', 'GKE', 'Cloud Functions', 'App Engine',
            'Cloud Run', 'Dataflow', 'Pub/Sub', 'Firestore'
        ]
        
        for service in gcp_services:
            if service.lower() in text.lower():
                return service
        
        return "General"
    
    def _extract_question_description(self, text: str) -> str:
        """Extract the main question description including introductory context"""
        # Handle embedded newlines - convert literal \n to actual newlines first
        # Based on debug analysis: questions contain embedded \n characters
        processed_text = text.replace('\\n', '\n')  # Convert literal \n to actual newlines
        lines = processed_text.split('\n')
        question_lines = []
        intro_lines = []
        in_question_section = False
        found_question_marker = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip community comments
            if self._is_community_comment(line):
                continue
                
            # Skip header/footer artifacts
            if re.search(r'ExamTopics|Profess.*onal|^\d+\s*$|Page \d+', line, re.IGNORECASE):
                continue
                
            # Find the question marker
            if re.search(r'Question\s*#\s*\d+', line, re.IGNORECASE):
                found_question_marker = True
                in_question_section = True
                continue
            
            # If we found question marker, start collecting
            if found_question_marker:
                # Stop at answer options (A., B., C., etc.)
                if re.match(r'^[A-F][\.\)]\s', line):
                    break
                
                # Skip community comments that might have slipped through
                if self._is_community_comment(line):
                    continue
                    
                question_lines.append(line)
            
            # Collect introductory context before question marker
            elif not found_question_marker:
                # Look for potential introductory content (case studies, company descriptions)
                # Skip topic headers and user comments
                if (not re.search(r'^Topic\s+\d+', line, re.IGNORECASE) and
                    not re.search(r'^\w+\s+\d+\s+(months?|weeks?|days?)\s+ago', line, re.IGNORECASE) and
                    len(line) > 20):  # Only substantial content
                    
                    # Check if this looks like case study introduction
                    case_study_indicators = [
                        r'\b\w+\s+is\s+a\s+(web-based\s+)?(company|organization|platform)',
                        r'For\s+this\s+question,\s+refer\s+to\s+the\s+\w+\s+case\s+study',
                        r'\w+\s+(provides|offers|operates|runs)',
                        r'case\s+study',
                        r'scenario',
                        r'company\s+background'
                    ]
                    
                    is_case_study_content = any(re.search(pattern, line, re.IGNORECASE) for pattern in case_study_indicators)
                    
                    # Include if it's case study content or substantial context
                    if is_case_study_content or len(line) > 30:
                        intro_lines.append(line)
        
        # Combine intro and question
        all_content = []
        
        # Add meaningful intro lines (like "Dress4Win is a web-based company...")
        if intro_lines:
            # Filter intro lines - keep substantial content
            meaningful_intro = []
            for intro_line in intro_lines[-5:]:  # Take last 5 lines before question
                if len(intro_line) > 20 and not re.search(r'Question Set|Topic \d+', intro_line):
                    meaningful_intro.append(intro_line)
            all_content.extend(meaningful_intro)
        
        # Add question content
        all_content.extend(question_lines)
        
        description = ' '.join(all_content).strip()
        
        # Clean up common artifacts and OCR errors
        description = re.sub(r'\s+', ' ', description)
        
        # Fix common OCR errors
        ocr_fixes = {
            r'ConKgure': 'Configure',
            r'ReconKgure': 'Reconfigure', 
            r'traOc': 'traffic',
            r'Profess"onal': 'Professional',
            r'solu"on': 'solution',
            r'applica"on': 'application',
            r'ques"on': 'question',
            r'computa"on': 'computation',
            r'authen"cation': 'authentication',
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
            r'll\s+months?\s+ago': '',  # Remove username timestamps
            r'^\s*\w+\s+\d+\s+(months?|weeks?|days?),?\s*\d*\s*(weeks?|days?)?\s+ago\s*': '',  # Clean user timestamps
        }
        
        for pattern, replacement in ocr_fixes.items():
            description = re.sub(pattern, replacement, description, flags=re.IGNORECASE)
        
        return description
    
    def _extract_answer_options(self, text: str) -> Dict[str, str]:
        """Extract answer options (A, B, C, D, E, F)"""
        options = {}
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for option patterns: A., B., C., D., etc.
            match = re.match(r'^([A-F])[\.\)]\s*(.+)', line, re.IGNORECASE)
            if match:
                option_letter = match.group(1).upper()
                option_text = match.group(2).strip()
                
                # Skip if this looks like a user response or vote
                if re.search(r'(is the answer|upvoted|months ago|weeks ago|days ago|Selected Answer)', option_text, re.IGNORECASE):
                    continue
                
                # Skip very short or clearly non-option text (but allow file paths like ~/bin)
                if len(option_text) < 2 or (len(option_text) < 5 and not re.search(r'[~/\\.]', option_text)):
                    continue
                
                # Clean up OCR errors in option text
                ocr_fixes = {
                    r'ConKgure': 'Configure',
                    r'ReconKgure': 'Reconfigure', 
                    r'traOc': 'traffic',
                    r'solu"on': 'solution',
                    r'applica"on': 'application',
                    r'ques"on': 'question'
                }
                
                for pattern, replacement in ocr_fixes.items():
                    option_text = re.sub(pattern, replacement, option_text, flags=re.IGNORECASE)
                
                # Only add if we don't already have this option or if this one is longer/better
                if option_letter not in options or len(option_text) > len(options[option_letter]):
                    options[option_letter] = option_text
        
        return options
    
    def _parse_community_responses(self, text: str) -> Dict[str, str]:
        """Parse community responses and voting information"""
        community_data = {
            'community_answer': '',
            'highly_voted': '',
            'most_recent': '',
            'latest_date': ''
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip().lower()
            
            # Look for community answer indicators
            if 'selected answer' in line or 'correct answer' in line:
                # Try to find the answer in the same line or next line
                answer_match = re.search(r'[A-F](?=\s|$|\.)', line.upper())
                if answer_match:
                    community_data['community_answer'] = answer_match.group()
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    answer_match = re.search(r'^[A-F](?=\s|$|\.)', next_line.upper())
                    if answer_match:
                        community_data['community_answer'] = answer_match.group()
            
            elif 'highly voted' in line:
                # Extract highly voted answer
                answer_match = re.search(r'[A-F](?=\s|$|\.)', line.upper())
                if answer_match:
                    community_data['highly_voted'] = answer_match.group()
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    answer_match = re.search(r'^[A-F](?=\s|$|\.)', next_line.upper())
                    if answer_match:
                        community_data['highly_voted'] = answer_match.group()
            
            elif 'most recent' in line:
                # Extract most recent answer
                answer_match = re.search(r'[A-F](?=\s|$|\.)', line.upper())
                if answer_match:
                    community_data['most_recent'] = answer_match.group()
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    answer_match = re.search(r'^[A-F](?=\s|$|\.)', next_line.upper())
                    if answer_match:
                        community_data['most_recent'] = answer_match.group()
            
            # Look for dates
            date_patterns = [
                r'(\d{1,2}\s+(?:days?|weeks?|months?|years?)\s+ago)',
                r'(\d{1,2}/\d{1,2}/\d{2,4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, line)
                if date_match:
                    community_data['latest_date'] = date_match.group(1)
                    break
        
        return community_data
    
    def _calculate_confidence(self, question: Question) -> float:
        """Calculate confidence score for the parsed question"""
        score = 0.0
        
        # Question description quality (40% weight)
        if question.description:
            if len(question.description) >= 50:
                score += 0.4
            elif len(question.description) >= 20:
                score += 0.2
        
        # Answer options completeness (30% weight)
        if len(question.options) >= 4:
            score += 0.3
        elif len(question.options) >= 2:
            score += 0.15
        
        # Community answer availability (20% weight)
        community_answers = [
            question.community_answer,
            question.highly_voted_answer,
            question.most_recent_answer
        ]
        valid_answers = [ans for ans in community_answers if ans and ans in 'ABCDEF']
        if len(valid_answers) >= 2:
            score += 0.2
        elif len(valid_answers) >= 1:
            score += 0.1
        
        # Structural consistency (10% weight)
        if question.original_number and question.topic:
            score += 0.1
        elif question.original_number or question.topic:
            score += 0.05
        
        return min(score, 1.0)
    
    def _separate_community_comments(self, text: str, question_id: str, 
                                   page_number: int, source_file: str) -> Tuple[str, List[CommunityComment]]:
        """Separate community comments from question text"""
        lines = text.split('\n')
        clean_lines = []
        comments = []
        
        for line in lines:
            if self._is_community_comment(line):
                # Extract community comment
                comment = self._extract_community_comment(
                    line, question_id, page_number, source_file
                )
                if comment:
                    comments.append(comment)
            else:
                # Keep as part of question
                clean_lines.append(line)
        
        clean_text = '\n'.join(clean_lines)
        return clean_text, comments
    
    def _is_community_comment(self, line: str) -> bool:
        """Check if line is a community comment"""
        line = line.strip()
        if not line:
            return False
        
        # First check for Unicode symbols (most reliable from debug analysis)
        if '\uf147' in line or '\uf007' in line:
            self.logger.debug(f"Community comment detected (Unicode): {line[:50]}...")
            return True
            
        # Check other community indicators
        for pattern in self.community_indicators:
            if re.search(pattern, line, re.IGNORECASE):
                self.logger.debug(f"Community comment detected: {line[:50]}...")
                return True
        return False
    
    def _extract_community_comment(self, line: str, question_id: str, 
                                 page_number: int, source_file: str) -> Optional[CommunityComment]:
        """Extract community comment data from line"""
        try:
            comment = CommunityComment()
            comment.question_id = question_id
            comment.page_number = page_number
            comment.source = source_file
            comment.content = line.strip()
            
            # Extract username and timestamp
            username_match = re.search(r'^(\s*)([A-Za-z][A-Za-z0-9_]{2,})\s+(\d+\s+(?:years?|months?|weeks?|days?),?\s*(?:\d+\s+(?:months?|weeks?|days?))?\s+ago)', line)
            if username_match:
                comment.username = username_match.group(2)
                comment.timestamp = username_match.group(3)
            
            # Extract vote type
            if re.search(r'highly voted', line, re.IGNORECASE):
                comment.vote_type = 'Highly Voted'
            elif re.search(r'most recent', line, re.IGNORECASE):
                comment.vote_type = 'Most Recent'
            elif re.search(r'selected answer', line, re.IGNORECASE):
                comment.vote_type = 'Selected Answer'
            
            # Extract vote count
            vote_match = re.search(r'upvoted\s+(\d+)\s+times?', line, re.IGNORECASE)
            if vote_match:
                comment.vote_count = int(vote_match.group(1))
            
            return comment
            
        except Exception as e:
            self.logger.error(f"Error extracting community comment: {e}")
            return None
    
    def get_community_comments(self) -> List[CommunityComment]:
        """Get all extracted community comments"""
        return self.community_comments
    
    def parse_questions_from_pages(self, question_boundaries: List[Dict]) -> List[Question]:
        """
        Parse questions from identified question boundaries
        
        Args:
            question_boundaries: List of question boundary information
            
        Returns:
            List of parsed Question objects
        """
        questions = []
        
        for boundary in question_boundaries:
            try:
                # Use the full_content if available, otherwise reconstruct from content_lines
                question_text = boundary.get('full_content', '\n'.join(boundary['content_lines']))
                
                question = self.parse_question_structure(
                    question_text,
                    boundary['start_page'],
                    boundary['source_file']
                )
                
                if question and question.confidence_score >= self.config.get("quality_control", {}).get("minimum_confidence_score", 0.3):  # Lower threshold for real data
                    questions.append(question)
                    self.logger.debug(f"Successfully parsed question: {question.unique_id}")
                else:
                    if question:
                        self.logger.warning(f"Question {question.unique_id} below confidence threshold: {question.confidence_score}")
                    else:
                        self.logger.warning(f"Failed to parse question from page {boundary['start_page']}")
            
            except Exception as e:
                self.logger.error(f"Error parsing question from page {boundary['start_page']}: {str(e)}")
                continue
        
        self.logger.info(f"Successfully parsed {len(questions)} questions from {len(question_boundaries)} boundaries")
        return questions
    
    def identify_duplicates(self, questions: List[Question]) -> List[Tuple[str, str, float]]:
        """
        Identify potential duplicate questions
        
        Args:
            questions: List of Question objects
            
        Returns:
            List of tuples (question1_id, question2_id, similarity_score)
        """
        duplicates = []
        
        for i, q1 in enumerate(questions):
            for j, q2 in enumerate(questions[i+1:], i+1):
                similarity = self._calculate_similarity(q1.description, q2.description)
                if similarity > 0.8:  # High similarity threshold
                    duplicates.append((q1.unique_id, q2.unique_id, similarity))
        
        if duplicates:
            self.logger.info(f"Identified {len(duplicates)} potential duplicate pairs")
        
        return duplicates
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity between two strings"""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0