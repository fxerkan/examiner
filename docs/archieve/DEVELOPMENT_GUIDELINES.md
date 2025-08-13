# Development Guidelines for GCP Exam Question Extractor

## Claude Code Implementation Strategy

### 1. Project Structure Setup
Create the following directory structure in your development environment:

```
gcp_exam_extractor/
├── src/
│   ├── __init__.py
│   ├── pdf_processor.py      # PDF text extraction and processing
│   ├── question_parser.py    # Question structure parsing and validation
│   ├── llm_integrator.py     # Claude API integration
│   ├── text_enhancer.py      # Text cleaning and enhancement
│   ├── output_generator.py   # Tabular output generation
│   └── main.py              # Main application controller
├── config/
│   ├── api_config.json      # Claude API configuration
│   ├── processing_config.json # Processing parameters
│   └── prompts.json         # LLM prompts templates
├── data/
│   ├── input/               # Source PDF files
│   ├── processed/           # Intermediate processed data
│   ├── output/             # Final tabular outputs
│   └── logs/               # Processing logs
├── tests/
│   ├── test_pdf_processor.py
│   ├── test_question_parser.py
│   └── sample_data/
├── requirements.txt
├── README.md
└── CLAUDE.md
```

### 2. Core Module Specifications

#### pdf_processor.py
```python
# Key Functions Needed:
- extract_text_from_pdf(file_path, page_range=None)
- split_into_pages(text_content)
- clean_pdf_artifacts(text)
- identify_question_boundaries(text)
```

#### question_parser.py
```python
# Key Functions Needed:
- parse_question_structure(text_block)
- extract_question_description_with_context(text_block)  # Must include case studies
- extract_answer_options(question_text)
- parse_community_responses(response_section)
- identify_voting_patterns(responses)
- extract_metadata(question_block)
- handle_case_study_introductions(text_block)  # Extract Dress4Win, TerramEarth, etc.
```

#### llm_integrator.py
```python
# Key Functions Needed:
- initialize_claude_client(api_key)
- analyze_question(question_text, options)
- get_expert_answer(question_context)
- format_llm_prompt(question_data)
- handle_api_errors(response)
```

### 3. Processing Workflow

#### Step 1: PDF Ingestion
```python
def process_pdf_batch(pdf_directory):
    """
    Process all PDF files in the specified directory
    - Iterate through Questions_N.pdf files
    - Extract text maintaining page references
    - Create processing checkpoints
    """
```

#### Step 2: Question Detection with Context Extraction
```python
def identify_questions(text_content, page_number):
    """
    Detect question boundaries and structure with full context
    - Look for "Question #N Topic N" patterns
    - Extract preceding case study introductions (20+ lines before question)
    - Capture company descriptions (Dress4Win, TerramEarth, Mountkirk Games)
    - Identify answer options (A, B, C, D, E, F)
    - Separate community responses from actual content
    - Track page locations
    - Clean OCR artifacts and username pollution
    """
```

#### Step 3: Content Enhancement
```python
def enhance_extracted_text(raw_text):
    """
    Clean and enhance extracted text
    - Fix OCR errors and typos
    - Reconstruct fragmented sentences
    - Standardize formatting
    - Preserve technical terminology
    """
```

#### Step 4: LLM Analysis
```python
def analyze_with_llm(question_data):
    """
    Send question to Claude API for analysis
    - Format structured prompt
    - Include GCP context
    - Request detailed reasoning
    - Handle API responses
    """
```

### 4. Data Structures

#### Question Object
```python
class Question:
    def __init__(self):
        self.unique_id = ""           # Generated: Q{page}_{number}
        self.original_number = ""     # From document
        self.description = ""         # Question text
        self.options = {}            # {A: "text", B: "text", ...}
        self.community_answer = ""    # Most common community choice
        self.highly_voted_answer = "" # Highest voted answer
        self.most_recent_answer = ""  # Latest community answer
        self.claude_answer = ""       # LLM determined answer
        self.claude_reasoning = ""    # LLM explanation
        self.latest_date = ""        # Most recent community date
        self.topic = ""              # Topic classification
        self.page_number = int       # Source page
        self.confidence_score = 0.0  # Processing confidence
        self.source = ""            # processed source pdf filename/path
```

### 5. Configuration Templates

#### api_config.json
```json
{
    "claude": {
        "api_key": "your_claude_api_key",
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 4000,
        "temperature": 0.1,
        "timeout": 30
    },
    "rate_limiting": {
        "requests_per_minute": 50,
        "retry_attempts": 3,
        "backoff_factor": 2
    }
}
```

#### processing_config.json
```json
{
    "pdf_processing": {
        "input_directory": "/Users/erkanciftci/Library/CloudStorage/Dropbox/OREDATA/65-Exams_Certifications/Professional Cloud Architect - PCA/ExamTopics - GCP Professional Cloud Architect Exam - Split",
        "file_pattern": "Questions_*.pdf",
        "chunk_size": 5,
        "overlap_pages": 1
    },
    "text_cleaning": {
        "remove_urls": true,
        "fix_line_breaks": true,
        "standardize_spacing": true,
        "preserve_code_blocks": true
    },
    "question_detection": {
        "question_patterns": ["Question #\\d+", "Topic \\d+"],
        "option_patterns": ["^[A-F]\\.", "^[A-F]\\)"],
        "minimum_question_length": 50
    }
}
```

#### prompts.json
```json
{
    "question_analysis": {
        "system_prompt": "You are a Google Cloud Professional Architect with extensive experience in GCP services, best practices, and architectural patterns. Analyze the following certification exam question and provide the correct answer with detailed reasoning.",
        "user_template": "Question: {question_text}\n\nOptions:\n{options_text}\n\nPlease provide:\n1. The correct answer (A, B, C, D, E, or F)\n2. Detailed explanation of why this answer is correct\n3. Brief explanation of why other options are incorrect\n4. Relevant GCP services or concepts involved"
    }
}
```

### 6. Error Handling Strategy

#### Critical Error Points
1. **PDF Reading Errors**: Handle corrupted or inaccessible files
2. **Text Extraction Issues**: Manage OCR errors and formatting problems
3. **API Failures**: Handle Claude API timeouts and rate limits
4. **Parsing Errors**: Gracefully handle malformed question structures
5. **Data Validation**: Ensure output quality and completeness

#### Logging Requirements
```python
import logging

# Configure comprehensive logging
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - Page:%(page)s - %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'processing.log',
            'formatter': 'detailed'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
}
```

### 7. Testing Strategy

#### Unit Tests
- Test individual PDF page processing
- Validate question parsing accuracy
- Check LLM integration reliability
- Verify output format consistency

#### Integration Tests
- End-to-end processing pipeline
- Error recovery mechanisms
- Data quality validation
- Performance benchmarks

#### Sample Test Cases
```python
def test_question_extraction():
    """Test basic question extraction functionality"""
    
def test_community_answer_parsing():
    """Test parsing of community responses and voting"""
    
def test_llm_integration():
    """Test Claude API integration and response handling"""
    
def test_output_generation():
    """Test tabular output generation and formatting"""
```

### 8. Performance Optimization

#### Processing Efficiency
- Batch PDF processing to minimize I/O
- Cache LLM responses to avoid duplicate API calls
- Implement smart resume functionality
- Use parallel processing where appropriate

#### Memory Management
- Process files in chunks to avoid memory issues
- Clean up temporary data structures
- Monitor memory usage during processing
- Implement garbage collection checkpoints

### 9. Quality Assurance Checklist

Before deploying the application, ensure:

- [ ] All PDF files can be successfully processed
- [ ] Question boundaries are correctly identified
- [ ] Community answers are accurately extracted
- [ ] LLM integration works reliably
- [ ] Output format matches specifications
- [ ] Error handling covers edge cases
- [ ] Logging provides sufficient detail
- [ ] Performance meets requirements
- [ ] Data quality is validated
- [ ] Documentation is complete

### 10. Deployment Considerations

#### Environment Setup
- Python 3.8+ required
- Install required dependencies
- Configure Claude API access
- Set up directory permissions
- Initialize logging system

#### Runtime Monitoring
- Track processing progress
- Monitor API usage and costs
- Watch for processing errors
- Validate output quality continuously
- Maintain processing statistics

This comprehensive development guide provides the foundation for building a robust, reliable, and maintainable GCP exam question extraction and analysis system.
