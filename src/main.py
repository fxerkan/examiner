"""
Main Application Controller for GCP Exam Question Extractor
Orchestrates the entire extraction, processing, and output generation pipeline
"""

import logging
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse

from pdf_processor import PDFProcessor, PageContent
from question_parser import QuestionParser, Question, CommunityComment
from llm_integrator import LLMIntegrator, LLMResponse
from text_enhancer import TextEnhancer
from output_generator import OutputGenerator

class ExamQuestionExtractor:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "./project_config.json"
        self.config = self._load_config()
        self._setup_logging()
        
        # Initialize modules
        self.pdf_processor = PDFProcessor(config_path)
        self.question_parser = QuestionParser(config_path)
        self.text_enhancer = TextEnhancer(config_path)
        self.llm_integrator = LLMIntegrator()
        self.output_generator = OutputGenerator(config_path)
        
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self) -> Dict:
        """Load application configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup application logging"""
        log_config = self.config.get("logging", {})
        
        log_format = log_config.get("format", 
                                   "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        log_level = log_config.get("level", "INFO")
        log_file = log_config.get("file", "examtopics_processor.log")
        
        # Create logs directory
        Path("./logs").mkdir(exist_ok=True)
        log_path = Path("./logs") / log_file
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def extract_and_process(self, input_directory: str = None, 
                           max_questions: int = None,
                           use_llm: bool = True) -> List[Question]:
        """
        Main processing pipeline
        
        Args:
            input_directory: Directory containing PDF files
            max_questions: Maximum number of questions to process (for testing)
            use_llm: Whether to use LLM analysis
            
        Returns:
            List of processed Question objects
        """
        start_time = time.time()
        self.logger.info("Starting GCP Exam Question extraction process")
        
        try:
            # Step 1: Extract text from PDFs
            self.logger.info("Step 1: Extracting text from PDF files")
            pages = self.pdf_processor.process_pdf_batch(input_directory)
            
            if not pages:
                self.logger.error("No pages extracted from PDF files")
                return []
            
            self.logger.info(f"Extracted {len(pages)} pages from PDF files")
            
            # Step 2: Identify question boundaries
            self.logger.info("Step 2: Identifying question boundaries")
            question_boundaries = self.pdf_processor.identify_question_boundaries(pages)
            
            if not question_boundaries:
                self.logger.error("No question boundaries identified")
                return []
            
            self.logger.info(f"Identified {len(question_boundaries)} question boundaries")
            
            # Step 3: Parse questions
            self.logger.info("Step 3: Parsing question structures")
            questions = self.question_parser.parse_questions_from_pages(question_boundaries)
            
            if not questions:
                self.logger.error("No questions successfully parsed")
                return []
            
            self.logger.info(f"Successfully parsed {len(questions)} questions")
            
            # Limit questions for testing if specified
            if max_questions and max_questions < len(questions):
                questions = questions[:max_questions]
                self.logger.info(f"Limited to {max_questions} questions for processing")
            
            # Step 4: Enhance text
            self.logger.info("Step 4: Enhancing extracted text")
            for question in questions:
                if question.description:
                    question.description = self.text_enhancer.enhance_question_text(question.description)
                
                # Enhance answer options
                enhanced_options = {}
                for key, value in question.options.items():
                    enhanced_options[key] = self.text_enhancer.enhance_answer_option(value)
                question.options = enhanced_options
            
            # Step 5: LLM Analysis (if enabled)
            if use_llm:
                self.logger.info("Step 5: Performing LLM analysis")
                questions = self._perform_llm_analysis(questions)
            else:
                self.logger.info("Step 5: Skipping LLM analysis (disabled)")
            
            # Step 6: Identify duplicates
            self.logger.info("Step 6: Identifying potential duplicates")
            duplicates = self.question_parser.identify_duplicates(questions)
            if duplicates:
                self.logger.warning(f"Found {len(duplicates)} potential duplicate pairs")
            
            processing_time = time.time() - start_time
            self.logger.info(f"Processing completed in {processing_time:.2f} seconds")
            self.logger.info(f"Final result: {len(questions)} questions processed successfully")
            
            return questions
            
        except Exception as e:
            self.logger.error(f"Error in extraction process: {str(e)}")
            raise
    
    def _perform_llm_analysis(self, questions: List[Question]) -> List[Question]:
        """
        Perform LLM analysis on questions
        
        Args:
            questions: List of Question objects
            
        Returns:
            Updated questions with LLM analysis
        """
        total_questions = len(questions)
        processed_count = 0
        failed_count = 0
        
        self.logger.info(f"Starting LLM analysis for {total_questions} questions")
        
        for i, question in enumerate(questions, 1):
            try:
                if not question.description or not question.options:
                    self.logger.warning(f"Skipping question {question.unique_id}: missing description or options")
                    failed_count += 1
                    continue
                
                self.logger.debug(f"Analyzing question {i}/{total_questions}: {question.unique_id}")
                
                # Perform LLM analysis
                response = self.llm_integrator.analyze_question(
                    question.description, 
                    question.options
                )
                
                if response and not response.error:
                    question.claude_answer = response.correct_answer
                    question.claude_reasoning = response.reasoning
                    processed_count += 1
                    
                    self.logger.debug(f"LLM analysis successful for {question.unique_id}: {response.correct_answer}")
                else:
                    self.logger.warning(f"LLM analysis failed for {question.unique_id}: {response.error if response else 'No response'}")
                    failed_count += 1
                
                # Progress update every 10 questions
                if i % 10 == 0:
                    self.logger.info(f"LLM Analysis progress: {i}/{total_questions} ({i/total_questions*100:.1f}%)")
                
            except Exception as e:
                self.logger.error(f"Error analyzing question {question.unique_id}: {str(e)}")
                failed_count += 1
                continue
        
        self.logger.info(f"LLM analysis completed: {processed_count} successful, {failed_count} failed")
        return questions
    
    def generate_outputs(self, questions: List[Question], output_formats: List[str] = None, community_comments: List[CommunityComment] = None) -> Dict[str, str]:
        """
        Generate output files in specified formats
        
        Args:
            questions: List of Question objects
            output_formats: List of output formats ('csv', 'md', 'json', 'web')
            community_comments: List of CommunityComment objects
            
        Returns:
            Dictionary mapping format to output file path
        """
        if not questions:
            self.logger.warning("No questions provided for output generation")
            return {}
        
        if output_formats is None:
            output_formats = ['md', 'csv', 'json', 'web']
        
        output_files = {}
        
        try:
            for format_type in output_formats:
                self.logger.info(f"Generating {format_type.upper()} output")
                
                if format_type == 'csv':
                    output_files['csv'] = self.output_generator.generate_csv_output(questions)
                elif format_type == 'md':
                    output_files['md'] = self.output_generator.generate_markdown_output(questions)
                elif format_type == 'json':
                    output_files['json'] = self.output_generator.generate_json_output(questions)
                elif format_type == 'web':
                    output_files['web'] = self.output_generator.export_for_web_ui(questions, community_comments)
                else:
                    self.logger.warning(f"Unknown output format: {format_type}")
            
            # Generate summary report
            output_files['summary'] = self.output_generator.generate_summary_report(questions)
            
            self.logger.info(f"Output generation completed. Files generated: {list(output_files.keys())}")
            return output_files
            
        except Exception as e:
            self.logger.error(f"Error generating outputs: {str(e)}")
            raise
    
    def run_full_pipeline(self, input_directory: str = None,
                         output_formats: List[str] = None,
                         max_questions: int = None,
                         use_llm: bool = True) -> Dict[str, str]:
        """
        Run the complete extraction pipeline
        
        Args:
            input_directory: Directory containing PDF files
            output_formats: List of output formats to generate
            max_questions: Maximum questions to process (for testing)
            use_llm: Whether to use LLM analysis
            
        Returns:
            Dictionary of generated output files
        """
        try:
            # Extract and process questions
            questions = self.extract_and_process(
                input_directory=input_directory,
                max_questions=max_questions,
                use_llm=use_llm
            )
            
            if not questions:
                self.logger.error("No questions processed successfully")
                return {}
            
            # Get community comments from parser
            community_comments = self.question_parser.get_community_comments()
            
            # Generate outputs
            output_files = self.generate_outputs(questions, output_formats, community_comments)
            
            # Final summary
            self.logger.info("=" * 50)
            self.logger.info("PROCESSING COMPLETE")
            self.logger.info("=" * 50)
            self.logger.info(f"Questions processed: {len(questions)}")
            community_comments = self.question_parser.get_community_comments()
            self.logger.info(f"Community comments extracted: {len(community_comments)}")
            self.logger.info(f"Output files generated: {len(output_files)}")
            
            for format_type, file_path in output_files.items():
                self.logger.info(f"  {format_type.upper()}: {file_path}")
            
            return output_files
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            raise

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="GCP Exam Question Extractor")
    parser.add_argument("--input", "-i", help="Input directory containing PDF files")
    parser.add_argument("--output-formats", "-f", nargs="+", 
                       choices=["csv", "md", "json", "web"],
                       default=["md", "csv", "json", "web"],
                       help="Output formats to generate")
    parser.add_argument("--max-questions", "-m", type=int,
                       help="Maximum number of questions to process (for testing)")
    parser.add_argument("--no-llm", action="store_true",
                       help="Skip LLM analysis")
    parser.add_argument("--config", "-c", help="Configuration file path")
    
    args = parser.parse_args()
    
    try:
        # Initialize extractor
        extractor = ExamQuestionExtractor(config_path=args.config)
        
        # Run pipeline
        output_files = extractor.run_full_pipeline(
            input_directory=args.input,
            output_formats=args.output_formats,
            max_questions=args.max_questions,
            use_llm=not args.no_llm
        )
        
        print("\nProcessing completed successfully!")
        print(f"Generated {len(output_files)} output files:")
        for format_type, file_path in output_files.items():
            print(f"  {format_type.upper()}: {file_path}")
    
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()