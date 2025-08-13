"""
Basic functionality tests for GCP Exam Question Extractor
Tests core modules with simple test cases
"""

import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pdf_processor import PDFProcessor, PageContent
from question_parser import QuestionParser, Question
from text_enhancer import TextEnhancer
from output_generator import OutputGenerator
from error_handler import ErrorHandler

class TestBasicFunctionality(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_config_path = None  # Use default configs
        
    def test_pdf_processor_initialization(self):
        """Test PDF processor can be initialized"""
        try:
            processor = PDFProcessor(self.test_config_path)
            self.assertIsNotNone(processor)
            self.assertIsNotNone(processor.config)
        except Exception as e:
            self.fail(f"PDFProcessor initialization failed: {str(e)}")
    
    def test_question_parser_initialization(self):
        """Test question parser can be initialized"""
        try:
            parser = QuestionParser(self.test_config_path)
            self.assertIsNotNone(parser)
            self.assertIsNotNone(parser.config)
        except Exception as e:
            self.fail(f"QuestionParser initialization failed: {str(e)}")
    
    def test_text_enhancer_initialization(self):
        """Test text enhancer can be initialized"""
        try:
            enhancer = TextEnhancer(self.test_config_path)
            self.assertIsNotNone(enhancer)
            self.assertIsNotNone(enhancer.config)
        except Exception as e:
            self.fail(f"TextEnhancer initialization failed: {str(e)}")
    
    def test_output_generator_initialization(self):
        """Test output generator can be initialized"""
        try:
            generator = OutputGenerator(self.test_config_path)
            self.assertIsNotNone(generator)
            self.assertIsNotNone(generator.config)
        except Exception as e:
            self.fail(f"OutputGenerator initialization failed: {str(e)}")
    
    def test_error_handler_initialization(self):
        """Test error handler can be initialized"""
        try:
            handler = ErrorHandler(self.test_config_path)
            self.assertIsNotNone(handler)
            self.assertIsNotNone(handler.config)
        except Exception as e:
            self.fail(f"ErrorHandler initialization failed: {str(e)}")
    
    def test_text_enhancement_basic(self):
        """Test basic text enhancement functionality"""
        enhancer = TextEnhancer(self.test_config_path)
        
        # Test basic text cleaning
        test_text = "This   is  a   test   with   excessive   spacing."
        enhanced = enhancer.enhance_extracted_text(test_text)
        
        self.assertNotEqual(test_text, enhanced)
        self.assertLess(enhanced.count('   '), test_text.count('   '))
    
    def test_question_parsing_basic(self):
        """Test basic question parsing functionality"""
        parser = QuestionParser(self.test_config_path)
        
        # Test sample question text
        sample_question = """
        Question #1 Topic 1
        
        What is the best practice for deploying applications on Google Cloud Platform?
        
        A. Use Compute Engine instances
        B. Use App Engine for all applications
        C. Use Cloud Run for containerized apps
        D. Use GKE for everything
        
        Selected Answer: C
        Highly Voted: C
        Most Recent: C
        """
        
        question = parser.parse_question_structure(sample_question, 1, "test.pdf")
        
        self.assertIsNotNone(question)
        self.assertTrue(len(question.description) > 0)
        self.assertTrue(len(question.options) > 0)
        self.assertEqual(question.community_answer, "C")
    
    def test_page_content_creation(self):
        """Test PageContent data structure"""
        page = PageContent(
            page_number=1,
            text="Sample text content",
            source_file="test.pdf",
            raw_text="Raw sample text"
        )
        
        self.assertEqual(page.page_number, 1)
        self.assertEqual(page.text, "Sample text content")
        self.assertEqual(page.source_file, "test.pdf")
        self.assertEqual(page.raw_text, "Raw sample text")
    
    def test_question_creation(self):
        """Test Question data structure"""
        question = Question()
        
        # Test default values
        self.assertEqual(question.unique_id, "")
        self.assertEqual(question.confidence_score, 0.0)
        self.assertEqual(question.page_number, 0)
        self.assertIsInstance(question.options, dict)
        
        # Test setting values
        question.unique_id = "Q1_1"
        question.description = "Test question"
        question.options = {"A": "Option A", "B": "Option B"}
        
        self.assertEqual(question.unique_id, "Q1_1")
        self.assertEqual(question.description, "Test question")
        self.assertEqual(len(question.options), 2)
    
    def test_error_handling_basic(self):
        """Test basic error handling"""
        handler = ErrorHandler(self.test_config_path)
        
        # Test error handling
        test_error = Exception("Test error message")
        error_info = handler.handle_error(test_error, "test_context", "ERROR", True)
        
        self.assertIsNotNone(error_info)
        self.assertEqual(error_info.error_message, "Test error message")
        self.assertEqual(error_info.context, "test_context")
        self.assertEqual(error_info.severity, "ERROR")
        self.assertTrue(error_info.recoverable)
    
    def test_confidence_score_calculation(self):
        """Test confidence score calculation"""
        parser = QuestionParser(self.test_config_path)
        
        # Create a well-formed question
        question = Question()
        question.description = "This is a well-formed question with sufficient length for testing confidence scoring"
        question.options = {"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}
        question.community_answer = "A"
        question.highly_voted_answer = "A"
        question.original_number = "1"
        question.topic = "Test Topic"
        
        confidence = parser._calculate_confidence(question)
        
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        
        # A well-formed question should have high confidence
        self.assertGreater(confidence, 0.7)

if __name__ == '__main__':
    unittest.main()