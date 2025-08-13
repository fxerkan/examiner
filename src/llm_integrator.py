"""
LLM Integrator Module for GCP Exam Question Extractor
Handles Claude API integration for question analysis and answer determination
"""

import json
import logging
import time
import re
from typing import Dict, Optional, Tuple
import anthropic
from dataclasses import dataclass

@dataclass
class LLMResponse:
    """Data structure for LLM response"""
    correct_answer: str
    reasoning: str
    confidence: float
    analysis: str
    error: Optional[str] = None

class LLMIntegrator:
    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.client = None
        self.prompts = self._load_prompts()
        self._initialize_client()
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.requests_per_minute = self.config.get("rate_limiting", {}).get("requests_per_minute", 50)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load API configuration"""
        if config_path is None:
            config_path = "./config/api_config.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Also load from project config if API key is there
            try:
                with open("./project_config.json", 'r') as f:
                    project_config = json.load(f)
                    if "llm_integration" in project_config:
                        config["claude"].update(project_config["llm_integration"])
            except:
                pass
                
            return config
        except FileNotFoundError:
            self.logger.error(f"API config file not found: {config_path}")
            raise
    
    def _load_prompts(self) -> Dict:
        """Load prompt templates"""
        try:
            with open("./config/prompts.json", 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("Prompts file not found. Using default prompts.")
            return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict:
        """Default prompt templates"""
        return {
            "question_analysis": {
                "system_prompt": "You are a Google Cloud Professional Architect with extensive experience in GCP services, best practices, and architectural patterns. Analyze the following certification exam question and provide the correct answer with detailed reasoning.",
                "user_template": "Question: {question_text}\n\nOptions:\n{options_text}\n\nPlease provide:\n1. The correct answer (A, B, C, D, E, or F)\n2. Detailed explanation of why this answer is correct\n3. Brief explanation of why other options are incorrect\n4. Relevant GCP services or concepts involved"
            }
        }
    
    def _initialize_client(self):
        """Initialize Claude API client"""
        try:
            api_key = self.config["claude"]["api_key"]
            if not api_key or api_key == "your_claude_api_key":
                raise ValueError("Valid Claude API key not found in configuration")
            
            self.client = anthropic.Anthropic(
                api_key=api_key,
                timeout=self.config["claude"]["timeout"]
            )
            self.logger.info("Claude API client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude API client: {str(e)}")
            raise
    
    def _apply_rate_limiting(self):
        """Apply rate limiting to API requests"""
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - self.last_request_time > 60:
            self.request_count = 0
        
        # Check if we've exceeded the rate limit
        if self.request_count >= self.requests_per_minute:
            sleep_time = 60 - (current_time - self.last_request_time)
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
        
        self.request_count += 1
        self.last_request_time = current_time
    
    def analyze_question(self, question_text: str, options: Dict[str, str]) -> LLMResponse:
        """
        Analyze a question using Claude API
        
        Args:
            question_text: The question description
            options: Dictionary of answer options {A: "text", B: "text", ...}
            
        Returns:
            LLMResponse object with analysis results
        """
        if not question_text or not options:
            return LLMResponse(
                correct_answer="",
                reasoning="Invalid input: missing question or options",
                confidence=0.0,
                analysis="",
                error="Invalid input"
            )
        
        try:
            self._apply_rate_limiting()
            
            # Format the prompt
            formatted_prompt = self._format_prompt(question_text, options)
            
            # Make API request with retries
            response = self._make_api_request(formatted_prompt)
            
            if response:
                # Parse the response
                return self._parse_response(response)
            else:
                return LLMResponse(
                    correct_answer="",
                    reasoning="API request failed",
                    confidence=0.0,
                    analysis="",
                    error="API request failed"
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing question: {str(e)}")
            return LLMResponse(
                correct_answer="",
                reasoning=f"Error during analysis: {str(e)}",
                confidence=0.0,
                analysis="",
                error=str(e)
            )
    
    def _format_prompt(self, question_text: str, options: Dict[str, str]) -> str:
        """Format the prompt for Claude API"""
        # Format options text
        options_text = "\n".join([f"{key}. {value}" for key, value in options.items()])
        
        # Use the template from prompts
        template = self.prompts["question_analysis"]["user_template"]
        
        return template.format(
            question_text=question_text,
            options_text=options_text
        )
    
    def _make_api_request(self, prompt: str) -> Optional[str]:
        """Make API request to Claude with retry logic"""
        retry_attempts = self.config.get("rate_limiting", {}).get("retry_attempts", 3)
        backoff_factor = self.config.get("rate_limiting", {}).get("backoff_factor", 2)
        
        for attempt in range(retry_attempts):
            try:
                self.logger.debug(f"Making API request (attempt {attempt + 1})")
                
                response = self.client.messages.create(
                    model=self.config["claude"]["model"],
                    max_tokens=self.config["claude"]["max_tokens"],
                    temperature=self.config["claude"]["temperature"],
                    system=self.prompts["question_analysis"]["system_prompt"],
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                if response.content and response.content[0].text:
                    return response.content[0].text
                else:
                    self.logger.warning("Empty response from Claude API")
                    return None
                    
            except anthropic.RateLimitError as e:
                wait_time = (backoff_factor ** attempt) * 5
                self.logger.warning(f"Rate limit hit on attempt {attempt + 1}. Waiting {wait_time} seconds")
                time.sleep(wait_time)
                
            except anthropic.APIError as e:
                self.logger.error(f"API error on attempt {attempt + 1}: {str(e)}")
                if attempt == retry_attempts - 1:
                    raise
                time.sleep(backoff_factor ** attempt)
                
            except Exception as e:
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                if attempt == retry_attempts - 1:
                    raise
                time.sleep(backoff_factor ** attempt)
        
        return None
    
    def _parse_response(self, response_text: str) -> LLMResponse:
        """Parse Claude's response into structured data"""
        try:
            # Extract correct answer (look for single letter A-F)
            correct_answer = ""
            answer_patterns = [
                r'(?:correct answer|answer).*?([A-F])',
                r'([A-F])(?:\s*(?:is|\.)\s*(?:correct|the answer))',
                r'^([A-F])[\.\)]\s',  # Answer at start of line
                r'([A-F])(?=\s|$|\.)'  # Any isolated A-F
            ]
            
            for pattern in answer_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    correct_answer = match.group(1).upper()
                    break
            
            # Extract reasoning (look for explanation)
            reasoning = ""
            reasoning_indicators = [
                r'(?:explanation|reasoning|because|why)[\:\s]*(.*?)(?:\n\n|\n[A-Z]|\n\d+\.)',
                r'correct.*?because\s*(.*?)(?:\n\n|\n[A-Z])',
                r'([^\.]*\bGCP\b[^\.]*\.)',  # Sentences mentioning GCP
            ]
            
            for pattern in reasoning_indicators:
                matches = re.findall(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if matches:
                    reasoning = ' '.join(matches[:2])  # Take first 2 matches
                    break
            
            if not reasoning:
                # Fallback: take first substantial paragraph
                paragraphs = [p.strip() for p in response_text.split('\n\n') if len(p.strip()) > 30]
                if paragraphs:
                    reasoning = paragraphs[0]
            
            # Calculate confidence based on response quality
            confidence = self._calculate_response_confidence(response_text, correct_answer, reasoning)
            
            # Clean up reasoning
            reasoning = re.sub(r'\s+', ' ', reasoning).strip()
            reasoning = reasoning[:500]  # Limit length
            
            return LLMResponse(
                correct_answer=correct_answer,
                reasoning=reasoning,
                confidence=confidence,
                analysis=response_text[:1000],  # Keep first 1000 chars for reference
                error=None
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {str(e)}")
            return LLMResponse(
                correct_answer="",
                reasoning="Error parsing response",
                confidence=0.0,
                analysis=response_text[:500] if response_text else "",
                error=str(e)
            )
    
    def _calculate_response_confidence(self, response_text: str, correct_answer: str, reasoning: str) -> float:
        """Calculate confidence score for the LLM response"""
        score = 0.0
        
        # Valid answer provided (40% weight)
        if correct_answer and correct_answer in 'ABCDEF':
            score += 0.4
        
        # Quality reasoning provided (35% weight)
        if reasoning:
            if len(reasoning) >= 100:
                score += 0.35
            elif len(reasoning) >= 50:
                score += 0.2
        
        # Response completeness (15% weight)
        if len(response_text) >= 200:
            score += 0.15
        elif len(response_text) >= 100:
            score += 0.1
        
        # GCP-specific content (10% weight)
        gcp_terms = ['gcp', 'google cloud', 'compute engine', 'cloud storage', 
                     'bigquery', 'kubernetes', 'gke', 'cloud run', 'app engine']
        if any(term in response_text.lower() for term in gcp_terms):
            score += 0.1
        
        return min(score, 1.0)
    
    def get_expert_answer(self, question_context: Dict) -> LLMResponse:
        """
        Get expert answer for a question with full context
        
        Args:
            question_context: Dictionary containing question data
            
        Returns:
            LLMResponse with expert analysis
        """
        question_text = question_context.get('description', '')
        options = question_context.get('options', {})
        topic = question_context.get('topic', '')
        
        # Enhance prompt with topic context if available
        enhanced_prompt = f"""
Topic: {topic}

Question: {question_text}

Options:
{chr(10).join([f"{key}. {value}" for key, value in options.items()])}

As a Google Cloud Professional Architect expert, provide:
1. The correct answer (A, B, C, D, E, or F)
2. Detailed technical explanation focusing on GCP best practices
3. Why other options are incorrect
4. Related GCP services and architectural considerations
"""
        
        try:
            self._apply_rate_limiting()
            response_text = self._make_api_request(enhanced_prompt)
            
            if response_text:
                return self._parse_response(response_text)
            else:
                return LLMResponse(
                    correct_answer="",
                    reasoning="Failed to get expert analysis",
                    confidence=0.0,
                    analysis="",
                    error="API request failed"
                )
                
        except Exception as e:
            self.logger.error(f"Error getting expert answer: {str(e)}")
            return LLMResponse(
                correct_answer="",
                reasoning=f"Error: {str(e)}",
                confidence=0.0,
                analysis="",
                error=str(e)
            )
    
    def handle_api_errors(self, response: LLMResponse) -> LLMResponse:
        """Handle and potentially retry API errors"""
        if response.error:
            self.logger.warning(f"API error detected: {response.error}")
            # Could implement retry logic here if needed
        
        return response