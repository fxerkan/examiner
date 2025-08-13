"""
Output Generator Module for GCP Exam Question Extractor
Handles tabular output generation in CSV and Markdown formats
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from .question_parser import Question, CommunityComment

class OutputGenerator:
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
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
            "paths": {
                "output_directory": "./data/output"
            },
            "output_format": {
                "file_type": "md",
                "delimiter": "|",
                "include_headers": True,
                "columns": [
                    "Question No", "Question Description", "Answer Options",
                    "Community Answer", "Highly Voted Answer", "Most Recent Answer",
                    "Claude Answer", "Latest Date", "Topic", "Page Number", "Source"
                ]
            }
        }
    
    def generate_markdown_output(self, questions: List[Question], output_file: str = None) -> str:
        """
        Generate Markdown table output
        
        Args:
            questions: List of Question objects
            output_file: Output file path (optional)
            
        Returns:
            Path to generated file
        """
        if not questions:
            self.logger.warning("No questions provided for output generation")
            return ""
        
        if output_file is None:
            output_dir = Path(self.config["paths"]["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"gcp_exam_questions_{timestamp}.md"
        
        try:
            columns = self.config["output_format"]["columns"]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header
                f.write("# GCP Professional Cloud Architect Exam Questions\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Questions: {len(questions)}\n\n")
                
                # Write table header
                header_row = " | ".join(columns)
                f.write(f"| {header_row} |\n")
                
                # Write separator row
                separator = " | ".join(["---"] * len(columns))
                f.write(f"| {separator} |\n")
                
                # Write data rows
                for question in questions:
                    row_data = self._format_question_for_output(question)
                    formatted_row = " | ".join([self._escape_markdown(str(value)) for value in row_data])
                    f.write(f"| {formatted_row} |\n")
                
                # Write statistics
                self._write_statistics(f, questions)
            
            self.logger.info(f"Markdown output generated: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error generating Markdown output: {str(e)}")
            raise
    
    def generate_csv_output(self, questions: List[Question], output_file: str = None) -> str:
        """
        Generate CSV output
        
        Args:
            questions: List of Question objects
            output_file: Output file path (optional)
            
        Returns:
            Path to generated file
        """
        if not questions:
            self.logger.warning("No questions provided for CSV generation")
            return ""
        
        if output_file is None:
            output_dir = Path(self.config["paths"]["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"gcp_exam_questions_{timestamp}.csv"
        
        try:
            columns = self.config["output_format"]["columns"]
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(columns)
                
                # Write data rows
                for question in questions:
                    row_data = self._format_question_for_output(question)
                    writer.writerow(row_data)
            
            self.logger.info(f"CSV output generated: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error generating CSV output: {str(e)}")
            raise
    
    def generate_json_output(self, questions: List[Question], output_file: str = None) -> str:
        """
        Generate JSON output for programmatic access
        
        Args:
            questions: List of Question objects
            output_file: Output file path (optional)
            
        Returns:
            Path to generated file
        """
        if not questions:
            self.logger.warning("No questions provided for JSON generation")
            return ""
        
        if output_file is None:
            output_dir = Path(self.config["paths"]["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"gcp_exam_questions_{timestamp}.json"
        
        try:
            # Convert questions to dictionaries
            questions_data = []
            for question in questions:
                question_dict = {
                    "unique_id": question.unique_id,
                    "original_number": question.original_number,
                    "description": question.description,
                    "options": question.options,
                    "community_answer": question.community_answer,
                    "highly_voted_answer": question.highly_voted_answer,
                    "most_recent_answer": question.most_recent_answer,
                    "claude_answer": question.claude_answer,
                    "claude_reasoning": question.claude_reasoning,
                    "latest_date": question.latest_date,
                    "topic": question.topic,
                    "page_number": question.page_number,
                    "confidence_score": question.confidence_score,
                    "source": question.source,
                    "source_pdf_path": getattr(question, 'source_pdf_path', ''),
                    "introductory_info": getattr(question, 'introductory_info', ''),
                    "has_claude_answer": getattr(question, 'has_claude_answer', False)
                }
                questions_data.append(question_dict)
            
            # Create output structure
            output_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_questions": len(questions),
                    "source_files": list(set([q.source for q in questions])),
                    "topics": list(set([q.topic for q in questions if q.topic])),
                    "confidence_stats": self._calculate_confidence_stats(questions)
                },
                "questions": questions_data
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"JSON output generated: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error generating JSON output: {str(e)}")
            raise
    
    def _format_question_for_output(self, question: Question) -> List[str]:
        """
        Format a Question object for tabular output
        
        Args:
            question: Question object
            
        Returns:
            List of formatted values matching the output columns
        """
        # Format answer options as a string
        options_str = "; ".join([f"{key}: {value}" for key, value in question.options.items()])
        
        return [
            question.original_number or question.unique_id,
            self._truncate_text(question.description, 200),
            self._truncate_text(options_str, 300),
            question.community_answer,
            question.highly_voted_answer,
            question.most_recent_answer,
            question.claude_answer,
            question.latest_date,
            question.topic,
            str(question.page_number),
            question.source
        ]
    
    def _escape_markdown(self, text: str) -> str:
        """Escape markdown special characters"""
        if not text:
            return ""
        
        # Escape pipe characters and other markdown special chars
        text = text.replace("|", "\\|")
        text = text.replace("*", "\\*")
        text = text.replace("_", "\\_")
        text = text.replace("`", "\\`")
        text = text.replace("#", "\\#")
        
        return text
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length"""
        if not text:
            return ""
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length-3] + "..."
    
    def _write_statistics(self, file_handle, questions: List[Question]):
        """Write statistics section to markdown file"""
        file_handle.write("\n## Statistics\n\n")
        
        # Basic counts
        total_questions = len(questions)
        file_handle.write(f"- **Total Questions**: {total_questions}\n")
        
        # Source file distribution
        source_counts = {}
        for question in questions:
            source = question.source
            source_counts[source] = source_counts.get(source, 0) + 1
        
        file_handle.write("- **Questions per Source**:\n")
        for source, count in sorted(source_counts.items()):
            file_handle.write(f"  - {source}: {count} questions\n")
        
        # Topic distribution
        topic_counts = {}
        for question in questions:
            topic = question.topic or "Unknown"
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        file_handle.write("- **Questions per Topic**:\n")
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
            file_handle.write(f"  - {topic}: {count} questions\n")
        
        # Answer availability
        community_answers = sum(1 for q in questions if q.community_answer)
        claude_answers = sum(1 for q in questions if q.claude_answer)
        
        file_handle.write(f"- **Community Answers Available**: {community_answers} ({community_answers/total_questions*100:.1f}%)\n")
        file_handle.write(f"- **Claude Answers Available**: {claude_answers} ({claude_answers/total_questions*100:.1f}%)\n")
        
        # Confidence score distribution
        if questions:
            avg_confidence = sum(q.confidence_score for q in questions) / len(questions)
            high_confidence = sum(1 for q in questions if q.confidence_score >= 0.8)
            file_handle.write(f"- **Average Confidence Score**: {avg_confidence:.2f}\n")
            file_handle.write(f"- **High Confidence Questions (≥0.8)**: {high_confidence} ({high_confidence/total_questions*100:.1f}%)\n")
    
    def _calculate_confidence_stats(self, questions: List[Question]) -> Dict:
        """Calculate confidence score statistics"""
        if not questions:
            return {}
        
        scores = [q.confidence_score for q in questions]
        return {
            "average": sum(scores) / len(scores),
            "minimum": min(scores),
            "maximum": max(scores),
            "high_confidence_count": sum(1 for score in scores if score >= 0.8),
            "medium_confidence_count": sum(1 for score in scores if 0.5 <= score < 0.8),
            "low_confidence_count": sum(1 for score in scores if score < 0.5)
        }
    
    def generate_summary_report(self, questions: List[Question], output_file: str = None) -> str:
        """
        Generate a summary report of the extraction process
        
        Args:
            questions: List of Question objects
            output_file: Output file path (optional)
            
        Returns:
            Path to generated report file
        """
        if output_file is None:
            output_dir = Path(self.config["paths"]["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"extraction_summary_{timestamp}.md"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# GCP Exam Question Extraction Summary\n\n")
                f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Overview
                f.write("## Overview\n\n")
                f.write(f"- Total questions processed: {len(questions)}\n")
                
                # Quality metrics
                confidence_stats = self._calculate_confidence_stats(questions)
                f.write("## Quality Metrics\n\n")
                f.write(f"- Average confidence score: {confidence_stats.get('average', 0):.2f}\n")
                f.write(f"- High confidence questions (≥0.8): {confidence_stats.get('high_confidence_count', 0)}\n")
                f.write(f"- Medium confidence questions (0.5-0.8): {confidence_stats.get('medium_confidence_count', 0)}\n")
                f.write(f"- Low confidence questions (<0.5): {confidence_stats.get('low_confidence_count', 0)}\n\n")
                
                # Data completeness
                f.write("## Data Completeness\n\n")
                total = len(questions)
                
                descriptions = sum(1 for q in questions if q.description)
                options = sum(1 for q in questions if q.options)
                community_answers = sum(1 for q in questions if q.community_answer)
                claude_answers = sum(1 for q in questions if q.claude_answer)
                
                f.write(f"- Questions with descriptions: {descriptions}/{total} ({descriptions/total*100:.1f}%)\n")
                f.write(f"- Questions with options: {options}/{total} ({options/total*100:.1f}%)\n")
                f.write(f"- Questions with community answers: {community_answers}/{total} ({community_answers/total*100:.1f}%)\n")
                f.write(f"- Questions with Claude answers: {claude_answers}/{total} ({claude_answers/total*100:.1f}%)\n\n")
                
                # Recommendations
                f.write("## Recommendations\n\n")
                low_confidence = confidence_stats.get('low_confidence_count', 0)
                if low_confidence > 0:
                    f.write(f"- Review {low_confidence} low confidence questions for manual validation\n")
                
                missing_claude = total - claude_answers
                if missing_claude > 0:
                    f.write(f"- Consider reprocessing {missing_claude} questions missing Claude analysis\n")
                
                if community_answers < total * 0.8:
                    f.write("- Community answer extraction could be improved - review parsing logic\n")
            
            self.logger.info(f"Summary report generated: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {str(e)}")
            raise
    
    def export_for_web_ui(self, questions: List[Question], output_file: str = None) -> str:
        """
        Export data in format optimized for web UI consumption
        
        Args:
            questions: List of Question objects
            output_file: Output file path (optional)
            
        Returns:
            Path to generated file
        """
        if output_file is None:
            output_dir = Path(self.config["paths"]["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "questions_web_data.json"
        
        try:
            # Format for easy web consumption
            web_data = {
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_questions": len(questions),
                    "version": "1.0"
                },
                "filters": {
                    "topics": sorted(list(set([q.topic for q in questions if q.topic]))),
                    "sources": sorted(list(set([q.source for q in questions]))),
                    "answer_options": ["A", "B", "C", "D", "E", "F"]
                },
                "questions": []
            }
            
            for question in questions:
                web_question = {
                    "id": question.unique_id,
                    "number": question.original_number,
                    "description": question.description,
                    "options": question.options,
                    "answers": {
                        "community": question.community_answer,
                        "highly_voted": question.highly_voted_answer,
                        "most_recent": question.most_recent_answer,
                        "claude": question.claude_answer
                    },
                    "claude_reasoning": question.claude_reasoning,
                    "metadata": {
                        "topic": question.topic,
                        "page": question.page_number,
                        "source": question.source,
                        "date": question.latest_date,
                        "confidence": question.confidence_score
                    }
                }
                web_data["questions"].append(web_question)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(web_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Web UI data exported: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error exporting web UI data: {str(e)}")
            raise