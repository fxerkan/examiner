# 🚀 How to Run GCP Exam Question Extractor

## 📋 **Quick Start Guide**

### 1. **Setup Environment**
```bash
# Navigate to project directory
cd /Users/erkanciftci/repo_local/examtopics_extractor

# Activate virtual environment
source venv/bin/activate

# Verify installation
./venv/bin/python --version
```

### 2. **Extract Questions from PDFs**
```bash
# Run the robust question parser (recommended)
./venv/bin/python src/robust_question_parser.py

# Alternative: Run main pipeline
./venv/bin/python -c "
import sys
sys.path.append('src')
from robust_question_parser import main
main()
"
```

**Expected Output:**
```
🔧 Robust GCP Exam Question Extractor
==================================================
🚀 Starting robust extraction from 13 PDF files
🔍 Processing PDF: Questions_1.pdf
✅ Parsed question Q1_1: 4 options, confidence 80.00%
...
📊 ROBUST EXTRACTION SUMMARY
==================================================
Clean Questions: 48
Community Comments: 46
Average Confidence: 78.75%
Output File: data/output/clean_questions_web_data.json
```

### 3. **View Results in Web UI**
```bash
# Start simple HTTP server for web UI
cd web_ui
python -m http.server 8080

# OR use Python 3
python3 -m http.server 8080
```

**Access Web UI:**
- Open browser: http://localhost:8080
- Click on `enhanced_ui.html` for full-featured interface

## 🎯 **Advanced Usage**

### **Option 1: Process Specific PDF Files**
```bash
# Modify the input directory in robust_question_parser.py
# Line ~466: change input_dir parameter
./venv/bin/python src/robust_question_parser.py
```

### **Option 2: Custom Processing**
```python
# Custom Python script
from src.robust_question_parser import RobustQuestionParser

parser = RobustQuestionParser()
questions, comments = parser.process_all_pdfs("./data/input")
output_file = parser.export_clean_data(questions, comments)
print(f"Exported to: {output_file}")
```

### **Option 3: Integration with Main Pipeline**
```bash
# Run complete pipeline (PDF → Questions → Claude AI → Web UI)
cd src
../venv/bin/python main.py
```

## 📁 **File Structure Overview**

```
examtopics_extractor/
├── data/
│   ├── input/           # Place PDF files here
│   │   ├── Questions_1.pdf
│   │   ├── Questions_2.pdf
│   │   └── ...
│   └── output/          # Generated results
│       ├── clean_questions_web_data.json
│       └── validation_reports/
├── src/                 # Core application
│   ├── robust_question_parser.py  # Main extractor
│   ├── main.py         # Full pipeline
│   └── ...
├── web_ui/              # Web interface
│   ├── enhanced_ui.html # Advanced UI
│   └── index.html       # Basic UI
└── venv/               # Python environment
```

## 🔍 **Web UI Features**

### **Enhanced UI (Recommended)**
- **📊 Advanced Filtering**: Search by question text, answer options, confidence
- **🔧 Edit Mode**: Modify questions and answers directly
- **💬 Community Comments**: View community discussions in modal popups
- **📈 Confidence Scoring**: Visual indicators for question quality
- **🎯 Smart Search**: Real-time filtering across all content

### **Basic UI**
- Simple question browsing
- Basic search functionality
- Export capabilities

## 🛠 **Troubleshooting**

### **Common Issues & Solutions**

#### **1. Virtual Environment Issues**
```bash
# If venv activation fails, recreate it
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install pdfplumber
```

#### **2. No Questions Extracted**
```bash
# Check PDF files in input directory
ls -la data/input/

# Verify PDF files are readable
./venv/bin/python -c "
import pdfplumber
with pdfplumber.open('data/input/Questions_1.pdf') as pdf:
    print(f'Pages: {len(pdf.pages)}')
    print(f'Sample text: {pdf.pages[0].extract_text()[:100]}')
"
```

#### **3. Web UI Not Loading**
```bash
# Check if files exist
ls -la web_ui/

# Use different port if 8080 is busy
python -m http.server 8081
```

#### **4. Import Errors**
```bash
# Run from project root with PYTHONPATH
PYTHONPATH=. ./venv/bin/python src/robust_question_parser.py
```

## 📊 **Output Data Structure**

The extractor generates `clean_questions_web_data.json` with this structure:

```json
{
  "metadata": {
    "generated_at": "2025-08-12T11:23:31",
    "total_questions": 48,
    "version": "3.0-robust-extraction"
  },
  "questions": [
    {
      "id": "Q1_1",
      "number": "1", 
      "description": "Your company has decided to make...",
      "options": {
        "A": "Configure a new load balancer...",
        "B": "ReConfigure old clients...",
        "C": "Have the old API forward...",
        "D": "Use separate backend pools..."
      },
      "answers": {
        "community": "",
        "highly_voted": "",
        "most_recent": "",
        "claude": ""
      },
      "metadata": {
        "confidence": 0.8,
        "page": 1,
        "source": "Questions_1.pdf"
      }
    }
  ],
  "community_comments": [...]
}
```

## 🎯 **Next Steps for Analysis**

### **1. Add More PDF Files**
```bash
# Copy new PDF files to input directory
cp /path/to/new/Questions_*.pdf data/input/

# Re-run extraction
./venv/bin/python src/robust_question_parser.py
```

### **2. Integrate Claude AI Analysis**
```bash
# Add Claude API key to config
# Run full pipeline with AI analysis
./venv/bin/python src/main.py
```

### **3. Export Analysis Results**
- CSV format: Available through web UI
- Custom reports: Modify `output_generator.py`
- Integration: Use JSON output for other tools

## 🚀 **Performance Optimization**

- **Batch Processing**: Process multiple PDFs in parallel
- **Incremental Updates**: Only process new/changed files
- **Memory Management**: Process large files in chunks
- **Caching**: Store processed results for faster re-runs

## 📞 **Support**

For issues or enhancements:
1. Check troubleshooting section above
2. Review `FINAL_VALIDATION_REPORT.md` for quality metrics
3. Examine log files in `logs/` directory
4. Use debug mode: Add `logging.DEBUG` to see detailed processing