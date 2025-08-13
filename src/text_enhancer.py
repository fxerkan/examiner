"""
Text Enhancer Module for GCP Exam Question Extractor
Handles text cleaning, OCR error correction, and readability improvements
"""

import re
import logging
from typing import Dict, List, Optional
import json

class TextEnhancer:
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self._init_correction_rules()
    
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
            "text_enhancement": {
                "fix_ocr_errors": True,
                "correct_grammar": True,
                "standardize_formatting": True,
                "preserve_technical_terms": True,
                "handle_page_breaks": True
            }
        }
    
    def _init_correction_rules(self):
        """Initialize text correction rules"""
        # Common OCR errors and corrections
        self.ocr_corrections = {
            # Letter confusions
            r'\b0(?=\w)': 'O',  # 0 -> O at word start
            r'\b1(?=\w)': 'l',  # 1 -> l at word start
            r'\b5(?=\w)': 'S',  # 5 -> S at word start
            r'(?<=\w)0\b': 'o',  # 0 -> o at word end
            r'(?<=\w)1\b': 'l',  # 1 -> l at word end
            
            # Common technical term fixes
            r'\bC1oud\b': 'Cloud',
            r'\bCompu te\b': 'Compute',
            r'\bB1gQuery\b': 'BigQuery',
            r'\bKubernet es\b': 'Kubernetes',
            r'\bGoogl e\b': 'Google',
            r'\bnetw0rk\b': 'network',
            r'\bser vice\b': 'service',
            r'\bapp1ication\b': 'application',
            
            # Spacing issues
            r'\s+(?=[.,;:])': '',  # Remove space before punctuation
            r'([.,;:])\s*(?=\w)': r'\1 ',  # Ensure space after punctuation
            r'(\w)\s*\n\s*(\w)': r'\1 \2',  # Fix broken words across lines
        }
        
        # GCP-specific terms that should be preserved
        self.technical_terms = {
            'GCP', 'Google Cloud Platform', 'Compute Engine', 'Cloud Storage',
            'BigQuery', 'Cloud SQL', 'Kubernetes', 'GKE', 'Cloud Run',
            'App Engine', 'Cloud Functions', 'Dataflow', 'Pub/Sub',
            'Firestore', 'Bigtable', 'Cloud Spanner', 'IAM', 'VPC',
            'Cloud Load Balancer', 'Cloud CDN', 'Cloud DNS', 'Cloud Armor'
        }
        
        # Common grammar patterns
        self.grammar_fixes = {
            r'\ba\s+(?=[aeiouAEIOU])': 'an ',  # a -> an before vowels
            r'\ban\s+(?=[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])': 'a ',  # an -> a before consonants
            r'(?<=\w)\s*,\s*and\s*': ', and ',  # Fix comma spacing in lists
            r'(?<=\w)\s*;\s*': '; ',  # Fix semicolon spacing
        }
    
    def enhance_extracted_text(self, raw_text: str) -> str:
        """
        Main text enhancement function
        
        Args:
            raw_text: Raw extracted text from PDF
            
        Returns:
            Enhanced and cleaned text
        """
        if not raw_text:
            return ""
        
        enhanced_text = raw_text
        
        # Apply enhancements based on config
        config = self.config.get("text_enhancement", {})
        
        if config.get("handle_page_breaks", True):
            enhanced_text = self._handle_page_breaks(enhanced_text)
        
        if config.get("fix_ocr_errors", True):
            enhanced_text = self._fix_ocr_errors(enhanced_text)
        
        if config.get("standardize_formatting", True):
            enhanced_text = self._standardize_formatting(enhanced_text)
        
        if config.get("correct_grammar", True):
            enhanced_text = self._apply_grammar_fixes(enhanced_text)
        
        if config.get("preserve_technical_terms", True):
            enhanced_text = self._preserve_technical_terms(enhanced_text)
        
        # Final cleanup
        enhanced_text = self._final_cleanup(enhanced_text)
        
        return enhanced_text
    
    def _handle_page_breaks(self, text: str) -> str:
        """Handle text that spans across pages"""
        # Fix hyphenated words broken across lines
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Fix sentences broken across lines (word ends with lowercase, next starts with lowercase)
        text = re.sub(r'(\w[a-z])\s*\n\s*([a-z]\w)', r'\1 \2', text)
        
        # Fix list items broken across pages
        text = re.sub(r'([A-F]\.)\s*\n\s*([A-Z])', r'\1 \2', text)
        
        return text
    
    def _fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors"""
        for pattern, replacement in self.ocr_corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _standardize_formatting(self, text: str) -> str:
        """Standardize text formatting"""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        
        # Fix bullet points and list formatting
        text = re.sub(r'^[\*\-\+]\s*', '• ', text, flags=re.MULTILINE)
        
        # Standardize question/answer formatting
        text = re.sub(r'(?i)question\s*#?\s*(\d+)', r'Question #\1', text)
        text = re.sub(r'(?i)topic\s*(\d+)', r'Topic \1', text)
        
        # Fix option formatting (A., B., etc.)
        for letter in 'ABCDEF':
            text = re.sub(rf'(?i)^{letter.lower()}[\.\)]\s*', f'{letter}. ', text, flags=re.MULTILINE)
        
        return text
    
    def _apply_grammar_fixes(self, text: str) -> str:
        """Apply basic grammar corrections"""
        for pattern, replacement in self.grammar_fixes.items():
            text = re.sub(pattern, replacement, text)
        
        # Fix capitalization after periods
        text = re.sub(r'(\.\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
        
        return text
    
    def _preserve_technical_terms(self, text: str) -> str:
        """Ensure technical terms are properly capitalized"""
        for term in self.technical_terms:
            # Create case-insensitive pattern
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            text = pattern.sub(term, text)
        
        return text
    
    def _final_cleanup(self, text: str) -> str:
        """Final text cleanup"""
        # Remove excessive punctuation
        text = re.sub(r'[.]{3,}', '...', text)
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Clean up spacing around punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        text = re.sub(r'([.,;:!?])\s+', r'\1 ', text)
        
        # Remove trailing whitespace from lines
        text = '\n'.join(line.rstrip() for line in text.split('\n'))
        
        # Ensure text ends with proper punctuation if it's a sentence
        text = text.strip()
        if text and text[-1] not in '.!?':
            if len(text) > 20:  # Only add period for substantial text
                text += '.'
        
        return text
    
    def enhance_question_text(self, question_text: str) -> str:
        """
        Specifically enhance question text
        
        Args:
            question_text: Raw question text
            
        Returns:
            Enhanced question text
        """
        if not question_text:
            return ""
        
        enhanced = question_text
        
        # Remove question numbering if at the start
        enhanced = re.sub(r'^(?:Question\s*#?\d+\.?\s*)', '', enhanced, flags=re.IGNORECASE).strip()
        
        # Ensure question ends with proper punctuation
        if enhanced and enhanced[-1] not in '?!.':
            enhanced += '?'
        
        # Apply general enhancement
        enhanced = self.enhance_extracted_text(enhanced)
        
        return enhanced
    
    def enhance_answer_option(self, option_text: str) -> str:
        """
        Enhance individual answer option text
        
        Args:
            option_text: Raw answer option text
            
        Returns:
            Enhanced option text
        """
        if not option_text:
            return ""
        
        enhanced = option_text.strip()
        
        # Remove option letter if present at start
        enhanced = re.sub(r'^[A-F][\.\)]\s*', '', enhanced).strip()
        
        # Ensure first letter is capitalized
        if enhanced:
            enhanced = enhanced[0].upper() + enhanced[1:] if len(enhanced) > 1 else enhanced.upper()
        
        # Apply general enhancement
        enhanced = self.enhance_extracted_text(enhanced)
        
        return enhanced
    
    def detect_and_fix_encoding_issues(self, text: str) -> str:
        """
        Detect and fix common text encoding issues
        
        Args:
            text: Text that may have encoding issues
            
        Returns:
            Text with encoding issues fixed
        """
        if not text:
            return ""
        
        # Common encoding fixes
        encoding_fixes = {
            'â€™': "'",      # Right single quotation mark
            'â€œ': '"',      # Left double quotation mark
            'â€': '"',       # Right double quotation mark
            'â€"': '—',      # Em dash
            'â€"': '–',      # En dash
            'Â': ' ',        # Non-breaking space
            'Ã¡': 'á',       # á with encoding issue
            'Ã©': 'é',       # é with encoding issue
            'Ã­': 'í',       # í with encoding issue
            'Ã³': 'ó',       # ó with encoding issue
            'Ãº': 'ú',       # ú with encoding issue
        }
        
        for bad_char, good_char in encoding_fixes.items():
            text = text.replace(bad_char, good_char)
        
        return text
    
    def validate_enhanced_text(self, original: str, enhanced: str) -> Dict[str, any]:
        """
        Validate that text enhancement didn't break the content
        
        Args:
            original: Original text before enhancement
            enhanced: Enhanced text
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'issues': [],
            'length_change': len(enhanced) - len(original),
            'word_count_change': len(enhanced.split()) - len(original.split())
        }
        
        # Check for excessive length change (might indicate over-processing)
        if abs(validation['length_change']) > len(original) * 0.3:
            validation['valid'] = False
            validation['issues'].append('Excessive length change detected')
        
        # Check if essential content is preserved (look for numbers, key terms)
        original_numbers = set(re.findall(r'\d+', original))
        enhanced_numbers = set(re.findall(r'\d+', enhanced))
        
        if original_numbers != enhanced_numbers:
            validation['issues'].append('Numbers may have been altered')
        
        # Check for preserved technical terms
        original_terms = set()
        enhanced_terms = set()
        for term in self.technical_terms:
            if term.lower() in original.lower():
                original_terms.add(term)
            if term in enhanced:
                enhanced_terms.add(term)
        
        if original_terms and not enhanced_terms:
            validation['issues'].append('Technical terms may have been lost')
        
        return validation