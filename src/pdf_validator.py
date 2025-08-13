#!/usr/bin/env python3
"""
PDF Validation Tool for GCP Exam Question Extractor
Validates extracted questions against original PDF files for consistency
"""

import sys
import os
import json
import logging
import re
import difflib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import pdfplumber
from datetime import datetime

@dataclass
class ValidationIssue:
    """Represents a validation issue found during PDF comparison"""
    question_id: str
    issue_type: str  # 'missing_text', 'ocr_error', 'community_pollution', 'wrong_options', 'boundary_error'
    severity: str    # 'critical', 'major', 'minor'
    description: str
    expected: str = ""
    actual: str = ""
    page_number: int = 0
    confidence: float = 0.0

@dataclass
class ValidationReport:
    """Complete validation report"""
    total_questions: int = 0
    validated_questions: int = 0
    issues: List[ValidationIssue] = field(default_factory=list)
    accuracy_score: float = 0.0
    completeness_score: float = 0.0
    quality_score: float = 0.0
    timestamp: str = ""
    
    def get_critical_issues(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == 'critical']
    
    def get_major_issues(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == 'major']

class PDFValidator:
    def __init__(self, input_dir: str = "./data/input", output_file: str = None):
        self.input_dir = Path(input_dir)
        self.output_file = output_file
        self.setup_logging()
        
        # Validation patterns and rules
        self.setup_validation_patterns()
        
        self.validation_report = ValidationReport()
        self.pdf_cache = {}  # Cache extracted PDF content
        
    def setup_logging(self):
        """Setup logging for validation"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_validation_patterns(self):
        """Setup patterns for validation checks"""
        
        # OCR error patterns to detect
        self.ocr_error_patterns = [
            r'ConKgure',  # Configure
            r'ReconKgure',  # Reconfigure
            r'traOc',  # traffic
            r'solu"on',  # solution
            r'applica"on',  # application
            r'ques"on',  # question
            r'informa"on',  # information
            r'migra"on',  # migration
            r'Data\^ow',  # Dataflow
            r'\^at\s+Kles',  # flat files
            r'modiKed',  # modified
            r'deKne',  # define
            r'Knd',  # find
            r'Profess"onal',  # Professional
        ]
        
        # Community comment indicators (should NOT appear in clean questions)
        self.community_indicators = [
            r'\b(upvoted|voted)\s+\d+\s+times?',
            r'\b\w+\s+(Highly\s+Voted|Most\s+Recent)',
            r'\b\d+\s+(years?|months?|weeks?|days?),?\s*(\d+\s+(months?|weeks?|days?))?\s+ago',
            r'^[A-Za-z][A-Za-z0-9_]{2,}\s+(Highly\s+Voted|Most\s+Recent|\d+\s+(years?|months?|weeks?|days?)\s+ago)',
        ]
        
        # Question structure patterns
        self.question_patterns = [
            r'Question\s*#?\s*(\d+)',
            r'^\d+\.\s+',  # Numbered questions
            r'Question\s+(\d+)',
        ]
        
        # Answer option patterns
        self.answer_option_patterns = [
            r'^([A-F])\.\s*(.+)$',
            r'^([A-F])\)\s*(.+)$',
            r'^([A-F])\s*:\s*(.+)$',
        ]
    
    def validate_extracted_questions(self, questions_data: Dict) -> ValidationReport:
        """
        Main validation method - validates all extracted questions
        
        Args:
            questions_data: Extracted questions data from JSON
            
        Returns:
            ValidationReport with all identified issues
        """
        self.logger.info("🔍 Starting comprehensive PDF validation")
        
        questions = questions_data.get('questions', [])
        self.validation_report.total_questions = len(questions)
        self.validation_report.timestamp = datetime.now().isoformat()
        
        # Load PDF content into cache for faster processing
        self._load_pdf_cache()
        
        for question in questions:
            self.logger.info(f"Validating question {question.get('id', 'Unknown')}")
            self._validate_single_question(question)
            self.validation_report.validated_questions += 1
        
        # Calculate overall scores
        self._calculate_scores()
        
        self.logger.info(f"✅ Validation complete: {len(self.validation_report.issues)} issues found")
        return self.validation_report
    
    def _load_pdf_cache(self):
        """Load all PDF files into memory cache for faster processing"""
        self.logger.info("📚 Loading PDF files into cache...")
        
        pdf_files = list(self.input_dir.glob("Questions_*.pdf"))
        
        for pdf_file in pdf_files:
            try:
                self.logger.info(f"  Loading {pdf_file.name}")
                
                with pdfplumber.open(pdf_file) as pdf:
                    pdf_content = {}
                    
                    for page_num, page in enumerate(pdf.pages, 1):
                        # Extract text with multiple strategies
                        strategies = [
                            ('default', page.extract_text()),
                            ('layout', page.extract_text(layout=True)),
                            ('x_tolerance_0', page.extract_text(x_tolerance=0)),
                            ('y_tolerance_0', page.extract_text(y_tolerance=0)),
                        ]
                        
                        page_content = {}
                        for strategy_name, text in strategies:
                            if text:
                                page_content[strategy_name] = text
                        
                        pdf_content[page_num] = page_content
                    
                    self.pdf_cache[pdf_file.name] = pdf_content
                    
            except Exception as e:
                self.logger.error(f"❌ Error loading {pdf_file.name}: {e}")
    
    def _validate_single_question(self, question: Dict):
        """Validate a single extracted question against PDF source"""
        question_id = question.get('id', 'Unknown')
        source_file = question.get('source', question.get('metadata', {}).get('source'))
        page_number = question.get('page', question.get('metadata', {}).get('page', 0))
        
        if not source_file or not page_number:
            self._add_issue(question_id, 'missing_metadata', 'critical',
                          f"Missing source file or page number information")
            return
        
        # Get PDF content for this page
        pdf_content = self._get_page_content(source_file, page_number)
        if not pdf_content:
            self._add_issue(question_id, 'pdf_access_error', 'critical',
                          f"Cannot access PDF content for {source_file} page {page_number}")
            return
        
        # Validate different aspects
        self._validate_question_text(question, pdf_content, question_id)
        self._validate_answer_options(question, pdf_content, question_id)
        self._validate_community_separation(question, question_id)
        self._validate_ocr_quality(question, question_id)
        self._validate_completeness(question, pdf_content, question_id)
    
    def _get_page_content(self, source_file: str, page_number: int) -> Dict:
        """Get cached PDF content for specific page"""
        if source_file not in self.pdf_cache:
            return {}
        
        return self.pdf_cache[source_file].get(page_number, {})
    
    def _validate_question_text(self, question: Dict, pdf_content: Dict, question_id: str):
        """Validate question text accuracy against PDF"""
        extracted_description = question.get('description', '')
        
        if not extracted_description or len(extracted_description) < 20:
            self._add_issue(question_id, 'missing_text', 'critical',
                          "Question description is missing or too short",
                          expected="Complete question text", actual=extracted_description)
            return
        
        # Check against multiple extraction strategies
        best_match_score = 0
        best_strategy = None
        
        for strategy_name, pdf_text in pdf_content.items():
            if pdf_text:
                # Clean both texts for comparison
                clean_extracted = self._clean_text_for_comparison(extracted_description)
                clean_pdf = self._clean_text_for_comparison(pdf_text)
                
                # Calculate similarity
                similarity = self._calculate_text_similarity(clean_extracted, clean_pdf)
                
                if similarity > best_match_score:
                    best_match_score = similarity
                    best_strategy = strategy_name
        
        # Determine if similarity is acceptable
        if best_match_score < 0.7:  # Less than 70% similarity
            self._add_issue(question_id, 'text_accuracy', 'major',
                          f"Low text similarity ({best_match_score:.2%}) with PDF source",
                          confidence=best_match_score)
        elif best_match_score < 0.9:  # Less than 90% similarity
            self._add_issue(question_id, 'text_accuracy', 'minor',
                          f"Moderate text similarity ({best_match_score:.2%}) with PDF source",
                          confidence=best_match_score)
    
    def _validate_answer_options(self, question: Dict, pdf_content: Dict, question_id: str):
        """Validate answer options completeness and accuracy"""
        options = question.get('options', {})
        
        if len(options) < 2:
            self._add_issue(question_id, 'missing_options', 'critical',
                          f"Too few answer options: {len(options)} (minimum 2 expected)")
            return
        
        if len(options) < 4:
            self._add_issue(question_id, 'incomplete_options', 'major',
                          f"Incomplete answer options: {len(options)} (typically 4-6 expected)")
        
        # Check for OCR errors in options
        for letter, option_text in options.items():
            if not option_text or len(option_text) < 3:
                self._add_issue(question_id, 'empty_option', 'major',
                              f"Option {letter} is empty or too short: '{option_text}'")
        
        # Look for options in PDF content
        options_found_in_pdf = 0
        for strategy_name, pdf_text in pdf_content.items():
            if pdf_text:
                for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                    pattern = f"^\\s*{letter}[.):]"
                    if re.search(pattern, pdf_text, re.MULTILINE):
                        options_found_in_pdf += 1
                        break  # Count each letter only once across strategies
        
        expected_options = max(options_found_in_pdf, 4)  # Expect at least what we found or 4
        if len(options) < expected_options * 0.8:  # Allow some tolerance
            self._add_issue(question_id, 'missing_options', 'major',
                          f"Missing answer options: found {len(options)}, expected ~{expected_options}")
    
    def _validate_community_separation(self, question: Dict, question_id: str):
        """Validate that community comments are properly separated"""
        description = question.get('description', '')
        
        # Check for community comment pollution
        for pattern in self.community_indicators:
            if re.search(pattern, description, re.IGNORECASE):
                self._add_issue(question_id, 'community_pollution', 'critical',
                              f"Community comment text found in question description: '{re.search(pattern, description, re.IGNORECASE).group()}'")
        
        # Check for username patterns in description
        username_patterns = [
            r'\b[A-Za-z][A-Za-z0-9_]{2,}\s+(Highly\s+Voted|Most\s+Recent)',
            r'\b[A-Za-z][A-Za-z0-9_]{2,}\s+\d+\s+(years?|months?|weeks?|days?)\s+ago',
        ]
        
        for pattern in username_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                self._add_issue(question_id, 'community_pollution', 'critical',
                              f"Username/community text in question: '{match}'")
    
    def _validate_ocr_quality(self, question: Dict, question_id: str):
        """Validate OCR quality and detect common errors"""
        texts_to_check = [
            question.get('description', ''),
            question.get('introductory_info', ''),
        ]
        
        # Add option texts
        options = question.get('options', {})
        texts_to_check.extend(options.values())
        
        for text in texts_to_check:
            if not text:
                continue
                
            for pattern in self.ocr_error_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    self._add_issue(question_id, 'ocr_error', 'minor',
                                  f"OCR error detected: '{match}' - likely needs correction")
    
    def _validate_completeness(self, question: Dict, pdf_content: Dict, question_id: str):
        """Validate question completeness"""
        
        # Check if question appears to be truncated
        description = question.get('description', '')
        
        if description and not description.rstrip().endswith(('?', '.', ':', ')')):
            self._add_issue(question_id, 'truncated_text', 'major',
                          f"Question may be truncated - ends with: '{description[-20:]}'")
        
        # Check for missing introductory info (case studies)
        pdf_text = pdf_content.get('default', '')
        case_study_indicators = [
            r'For this question, refer to the .+ case study',
            r'.+ is a .+ company',
            r'Company Overview',
            r'Solution Concept',
            r'Business Requirements',
            r'Technical Requirements',
        ]
        
        has_case_study_in_pdf = any(re.search(pattern, pdf_text, re.IGNORECASE) for pattern in case_study_indicators)
        has_intro_info = bool(question.get('introductory_info', '').strip())
        
        if has_case_study_in_pdf and not has_intro_info:
            self._add_issue(question_id, 'missing_intro', 'major',
                          "Case study information detected in PDF but not extracted")
    
    def _clean_text_for_comparison(self, text: str) -> str:
        """Clean text for accurate comparison"""
        if not text:
            return ""
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common artifacts
        cleaned = re.sub(r'ExamTopics.*?Professional', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'Page\s+\d+', '', cleaned)
        
        # Normalize OCR variations
        ocr_normalizations = {
            r'ConKgure': 'Configure',
            r'ReconKgure': 'Reconfigure',
            r'traOc': 'traffic',
            r'solu"on': 'solution',
            r'applica"on': 'application',
            r'ques"on': 'question',
            r'Data\^ow': 'Dataflow',
            r'\^at\s+Kles': 'flat files',
        }
        
        for pattern, replacement in ocr_normalizations.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        # Use difflib for sequence comparison
        matcher = difflib.SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()
    
    def _add_issue(self, question_id: str, issue_type: str, severity: str, 
                   description: str, expected: str = "", actual: str = "",
                   page_number: int = 0, confidence: float = 0.0):
        """Add a validation issue to the report"""
        issue = ValidationIssue(
            question_id=question_id,
            issue_type=issue_type,
            severity=severity,
            description=description,
            expected=expected,
            actual=actual,
            page_number=page_number,
            confidence=confidence
        )
        self.validation_report.issues.append(issue)
    
    def _calculate_scores(self):
        """Calculate overall validation scores"""
        if self.validation_report.total_questions == 0:
            return
        
        critical_issues = len(self.validation_report.get_critical_issues())
        major_issues = len(self.validation_report.get_major_issues())
        minor_issues = len([i for i in self.validation_report.issues if i.severity == 'minor'])
        
        # Calculate accuracy score (based on text similarity and OCR errors)
        text_accuracy_issues = len([i for i in self.validation_report.issues if i.issue_type == 'text_accuracy'])
        ocr_issues = len([i for i in self.validation_report.issues if i.issue_type == 'ocr_error'])
        
        self.validation_report.accuracy_score = max(0, 1 - (text_accuracy_issues + ocr_issues * 0.1) / self.validation_report.total_questions)
        
        # Calculate completeness score (based on missing content)
        completeness_issues = len([i for i in self.validation_report.issues 
                                 if i.issue_type in ['missing_text', 'missing_options', 'truncated_text']])
        self.validation_report.completeness_score = max(0, 1 - completeness_issues / self.validation_report.total_questions)
        
        # Calculate overall quality score
        # Critical issues have high weight, major issues medium weight, minor issues low weight
        quality_penalty = (critical_issues * 0.3 + major_issues * 0.1 + minor_issues * 0.02)
        self.validation_report.quality_score = max(0, 1 - quality_penalty / self.validation_report.total_questions)
    
    def generate_validation_report(self, output_file: str = None) -> str:
        """Generate detailed validation report"""
        if output_file is None:
            output_dir = Path("./data/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"validation_report_{timestamp}.md"
        
        report_content = self._generate_markdown_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        self.logger.info(f"📊 Validation report generated: {output_file}")
        return str(output_file)
    
    def _generate_markdown_report(self) -> str:
        """Generate markdown content for validation report"""
        report = self.validation_report
        
        content = f"""# PDF Validation Report
**Generated**: {report.timestamp}

## Summary
- **Total Questions**: {report.total_questions}
- **Questions Validated**: {report.validated_questions}
- **Issues Found**: {len(report.issues)}

### Quality Scores
- **Accuracy Score**: {report.accuracy_score:.2%}
- **Completeness Score**: {report.completeness_score:.2%}
- **Overall Quality Score**: {report.quality_score:.2%}

### Issues Breakdown
- **Critical Issues**: {len(report.get_critical_issues())} 🔴
- **Major Issues**: {len(report.get_major_issues())} 🟡
- **Minor Issues**: {len([i for i in report.issues if i.severity == 'minor'])} 🟢

---

## Critical Issues 🔴

"""
        
        critical_issues = report.get_critical_issues()
        if critical_issues:
            for issue in critical_issues:
                content += f"""### {issue.question_id} - {issue.issue_type}
**Description**: {issue.description}
"""
                if issue.expected:
                    content += f"**Expected**: {issue.expected[:200]}...\n"
                if issue.actual:
                    content += f"**Actual**: {issue.actual[:200]}...\n"
                content += "\n"
        else:
            content += "No critical issues found! ✅\n\n"
        
        content += """---

## Major Issues 🟡

"""
        
        major_issues = report.get_major_issues()
        if major_issues:
            for issue in major_issues:
                content += f"""### {issue.question_id} - {issue.issue_type}
**Description**: {issue.description}
"""
                if issue.confidence:
                    content += f"**Confidence**: {issue.confidence:.2%}\n"
                content += "\n"
        else:
            content += "No major issues found! ✅\n\n"
        
        content += """---

## Recommendations

Based on the validation results, here are the recommended actions:

"""
        
        if report.quality_score < 0.7:
            content += "🔥 **URGENT**: Quality score is below 70%. Immediate action required:\n"
            content += "- Review and fix all critical issues\n"
            content += "- Implement better OCR error correction\n"
            content += "- Improve community comment separation\n\n"
        
        if report.accuracy_score < 0.8:
            content += "⚠️ **HIGH PRIORITY**: Accuracy issues detected:\n"
            content += "- Review PDF extraction strategies\n"
            content += "- Implement better text cleaning algorithms\n"
            content += "- Validate question boundaries\n\n"
        
        if report.completeness_score < 0.9:
            content += "📝 **MEDIUM PRIORITY**: Completeness issues:\n"
            content += "- Check for missing answer options\n"
            content += "- Ensure all question text is captured\n"
            content += "- Review case study information extraction\n\n"
        
        content += """---

## Next Steps

1. **Address Critical Issues**: Fix all critical issues immediately
2. **Review Extraction Logic**: Examine question parsing algorithms
3. **Improve OCR Correction**: Implement comprehensive OCR error fixing
4. **Validate Results**: Re-run extraction and validation after fixes
5. **Manual Review**: Conduct manual spot-checks on high-risk questions

---

*Report generated by GCP Exam Question Extractor Validation Tool*
"""
        
        return content

def main():
    """Main validation entry point"""
    print("🔍 GCP Exam Question Extractor - PDF Validation Tool")
    print("=" * 60)
    
    # Load extracted questions data
    questions_file = Path("./data/output/questions_web_data.json")
    
    if not questions_file.exists():
        print(f"❌ Error: Questions data file not found: {questions_file}")
        print("Please run the extraction process first to generate questions data.")
        return False
    
    try:
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        # Initialize validator
        validator = PDFValidator()
        
        # Run validation
        report = validator.validate_extracted_questions(questions_data)
        
        # Generate report
        report_file = validator.generate_validation_report()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Questions Validated: {report.validated_questions}")
        print(f"Issues Found: {len(report.issues)}")
        print(f"Quality Score: {report.quality_score:.2%}")
        print(f"Accuracy Score: {report.accuracy_score:.2%}")
        print(f"Completeness Score: {report.completeness_score:.2%}")
        print(f"\nDetailed Report: {report_file}")
        
        if report.quality_score < 0.7:
            print("\n🔥 URGENT: Quality score below 70% - immediate action required!")
            return False
        elif report.quality_score < 0.9:
            print("\n⚠️  WARNING: Quality issues detected - review recommended")
            return True
        else:
            print("\n✅ GOOD: Quality score above 90%")
            return True
            
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)