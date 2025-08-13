# ExaMiner

A comprehensive solution for extracting, parsing, and analyzing certification exam questions, answers and comments provided by community as PDF documents with LLM-powered analysis and turn into an interactive web interface.

## 🚀 Features

### Core Processing
- **PDF Processing**: Extract text from multiple PDF files with intelligent question boundary detection
- **Question Parsing**: Parse question structures, answer options, and community responses  
- **LLM Analysis**: Real-time Claude AI analysis for expert-level answer determination
- **Text Enhancement**: Advanced OCR error correction and text cleaning
- **Auto-increment Numbering**: Unique primary key system for all questions
- **Multiple Output Formats**: CSV, Markdown Tables, JSON Data, Clean JSON format for Web UI

### Interactive Web UI
- **🔍 Smart Search & Filtering**: Search across all content with multiple filter options
- **📝 Answer Marking**: Mark your answers with persistent storage across sessions
- **✨ Answer Highlighting**: Show/hide correct answers with visual indicators
- **📊 Exam Evaluation**: Comprehensive scoring system with 70% GCP passing threshold
- **📈 Detailed Analytics**: Wrong answer review, skipped questions tracking
- **✏️ Question Editing**: Edit questions, answers, and mark correct solutions
- **📄 PDF Upload**: Interactive upload interface with progress tracking
- **⚠️ Quality Warnings**: Detailed extraction warnings with clickable navigation

![ExaMiner](assets/examiner.png)

## 📁 Project Structure

```
examtopics_extractor/
├── src/                          # Core application modules
│   ├── main.py                   # Main application controller
│   ├── pdf_processor.py          # PDF text extraction and processing
│   ├── question_parser.py        # Question structure parsing
│   ├── llm_integrator.py         # Claude API integration
│   ├── text_enhancer.py          # Text cleaning and enhancement
│   ├── output_generator.py       # Output generation (CSV/MD/JSON)
│   └── error_handler.py          # Error handling and logging
├── config/                       # Configuration files
│   ├── api_config.json          # Claude API configuration
│   ├── processing_config.json   # Processing parameters
│   └── prompts.json            # LLM prompt templates
├── data/
│   ├── input/                   # Source PDF files
│   ├── output/                  # Generated output files
│   └── processed/               # Intermediate processed data
├── web_ui/                      # Interactive web interface
│   ├── index.html              # Main web UI page
│   ├── styles.css              # CSS styling
│   └── script.js               # JavaScript functionality
├── logs/                        # Application logs
├── tests/                       # Test files
└── demo_output/                 # Demo results
```

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   cd examtopics_extractor
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Claude API**:
   - Open `config/api_config.json`
   - Add your Claude API key
   ```json
   {
     "claude": {
       "api_key": "your-claude-api-key-here"
     }
   }
   ```

## 🚀 Quick Start

### Method 1: Web UI Upload (Recommended)

1. **Start the web interface**:
   ```bash
   cd web_ui
   python -m http.server 9000
   ```

2. **Open browser**: http://localhost:9000

3. **Upload PDFs**: 
   - Click "📄 Upload PDFs" button
   - Select your PDF files (supports multiple files)
   - Click "🚀 Start Processing" 
   - Wait for processing to complete

### Method 2: Manual Processing

1. **Place PDF files** in `data/input/` directory:
   ```
   data/input/
   ├── Questions_1.pdf
   ├── Questions_2.pdf
   └── Questions_3.pdf
   ```

2. **Run the extractor**:
   ```bash
   source venv/bin/activate
   python src/robust_question_parser.py
   ```

3. **Start web UI**:
   ```bash
   cd web_ui
   python -m http.server 9000
   ```

## 💡 Usage Guide

### Web Interface Features

#### 🔍 **Search & Filter**
- **Search**: Search across questions, answers, and comments
- **Filters**: Question number, topic, source file, page, confidence score
- **Results**: Shows 25 questions per page with pagination

#### 📝 **Answer Marking** 
- Click answer options to mark your selections
- Answers are automatically saved (localStorage)
- Multi-select questions supported
- Persistent across browser sessions

#### ✨ **Answer Highlighting**
- Toggle "Highlight Answers" to show correct answers
- Green background = Correct answer
- Blue background = Your marked answer  
- Red background = Wrong answer (when highlighted)

#### 📊 **Exam Evaluation**
- Click "🎯 Evaluate Answers" for detailed scoring
- Shows overall pass/fail status (70% threshold)
- Click score indicators to filter question types:
  - ✅ **Correct Answers**: Questions you got right
  - ❌ **Wrong Answers**: Review incorrect responses  
  - ⚠️ **Skipped Questions**: Questions you haven't answered
  - 🔵 **Answered Questions**: All questions with your responses

#### ✏️ **Question Editing**
- Click "✏️ Edit" on any question
- Edit question text and answer options
- Mark correct answers with checkboxes
- Changes saved to JSON file

#### ⚠️ **Quality Warnings**
- Click "🚨 Warnings" to view extraction issues
- Detailed information with clickable navigation
- Shows parsing problems and raw context
- "Go to Question" links for quick navigation

#### 📄 **PDF Upload**
- Drag & drop or browse for PDF files
- Real-time upload progress
- Automatic processing and analysis
- Results integrated immediately
   

## ⚙️ Configuration

### Main Configuration (`project_config.json`)

```json
{
  "paths": {
    "input_directory": "./data/input",
    "output_directory": "./data/output"
  },
  "pdf_processing": {
    "file_pattern": "Questions_*.pdf",
    "batch_size": 3
  },
  "llm_integration": {
    "model": "claude-4-sonnet-20250219",
    "temperature": 0.1,
    "max_tokens": 4000
  }
}
```

### Advanced Options

- **Processing Configuration**: `config/processing_config.json`
- **LLM Prompts**: `config/prompts.json`  
- **API Settings**: `config/api_config.json`

## 🎯 Output Formats

### 1. Markdown Table
```markdown
| Question No | Question Description | Answer Options | Community Answer | Claude Answer | Topic | Page Number | Source |
|-------------|---------------------|----------------|------------------|---------------|--------|-------------|---------|
| 1 | Your company wants to migrate... | A: Rehost; B: Refactor... | A | B | Topic 1 | 12 | Questions_1.pdf |
```

### 2. CSV Format
```csv
Question No,Question Description,Answer Options,Community Answer,Claude Answer,Topic,Page Number,Source
1,"Your company wants to migrate...","A: Rehost; B: Refactor...",A,B,Topic 1,12,Questions_1.pdf
```

### 3. JSON Format
```json
{
  "metadata": {
    "generated_at": "2025-08-11T18:54:05",
    "total_questions": 150
  },
  "questions": [
    {
      "id": "Q1_1",
      "description": "Your company wants to migrate...",
      "options": {"A": "Rehost", "B": "Refactor"},
      "answers": {
        "community": "A",
        "claude": "B"
      }
    }
  ]
}
```

## 🔧 Command Line Usage

```bash
# Basic usage
python src/main.py

# Custom input directory
python src/main.py --input /path/to/pdfs

# Generate specific formats
python src/main.py --output-formats csv json

# Limit questions (for testing)
python src/main.py --max-questions 10

# Skip LLM analysis
python src/main.py --no-llm

# Custom configuration
python src/main.py --config /path/to/config.json
```

## 📊 Quality Assurance

The extractor includes comprehensive quality control:

- **Confidence Scoring**: Each question gets a confidence score based on completeness
- **Duplicate Detection**: Identifies potential duplicate questions
- **Error Tracking**: Comprehensive logging and error reporting
- **Data Validation**: Input validation and structure checking

### Sample Quality Metrics

```
📊 Processing Summary:
- Total Questions: 150
- High Confidence (≥0.8): 142 (94.7%)
- Medium Confidence (0.5-0.8): 6 (4.0%)
- Low Confidence (<0.5): 2 (1.3%)
- Claude Analysis Success: 148 (98.7%)
- Potential Duplicates: 3 pairs identified
```

## 🧪 Testing

```bash
# Run basic project tests
python test_simple.py

# Run comprehensive demo
python demo.py

# Check specific module
python -c "from src.question_parser import QuestionParser; print('✅ Import successful')"
```

## 🐛 Troubleshooting

### Common Issues

1. **PDF Processing Errors**:
   - Ensure PDF files are not password-protected
   - Check file permissions
   - Verify PDF files are text-based (not scanned images)

2. **Claude API Issues**:
   - Verify API key in `config/api_config.json`
   - Check rate limits and quotas
   - Ensure internet connection

3. **Web UI Not Loading**:
   - Ensure `data/output/questions_web_data.json` exists
   - Check browser console for JavaScript errors
   - Verify local server is running

### Logging

Check logs in `logs/examtopics_processor.log` for detailed error information:

```bash
tail -f logs/examtopics_processor.log
```

## 🎯 Example Output

The system processes questions like this:

**Input (from PDF)**:
```
Question #1 Topic 1

Your company wants to migrate a large, monolithic application to Google Cloud Platform...

A. Rehost (Lift and Shift) the entire application to Compute Engine
B. Refactor the application into microservices and deploy on GKE
C. Rebuild the application as a serverless solution using Cloud Functions
D. Replace with SaaS solutions wherever possible

Selected Answer: A
Highly Voted: A  
Most Recent: B
```

**Output (Structured)**:
- ✅ **Question ID**: Q1_1
- 📝 **Description**: Clean, enhanced question text
- 🔤 **Options**: A, B, C, D with full text
- 👥 **Community**: A (Highly Voted: A, Most Recent: B)  
- 🤖 **Claude AI**: B (with detailed reasoning)
- 🎯 **Confidence**: 0.95 (High)
- 📍 **Metadata**: Topic 1, Page 12, Questions_1.pdf


## 📜 License

This project is provided as-is for educational and professional development purposes.

## 🙏 Acknowledgments

- Claude Code
- ExamTopics https://www.examtopics.com

---

**Developed with ❤️ and 🤖 (Claude Code) 🚀**