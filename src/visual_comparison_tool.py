#!/usr/bin/env python3
"""
Visual Comparison Tool for GCP Exam Question Extractor
Creates side-by-side comparison between original PDF and extracted data
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Dict
import pdfplumber
from datetime import datetime

def create_html_comparison(questions_data: Dict, pdf_dir: str = "./data/input") -> str:
    """Create HTML comparison showing PDF vs extracted data"""
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF vs Extracted Data - Visual Comparison</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #4285f4, #34a853);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        
        .comparison-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .pdf-section, .extracted-section {{
            padding: 20px;
        }}
        
        .pdf-section {{
            background: #fff3cd;
            border-right: 2px solid #ffc107;
        }}
        
        .extracted-section {{
            background: #d1ecf1;
        }}
        
        .section-title {{
            font-size: 1.2rem;
            font-weight: bold;
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 5px;
        }}
        
        .pdf-title {{
            background: #ffc107;
            color: #212529;
        }}
        
        .extracted-title {{
            background: #17a2b8;
            color: white;
        }}
        
        .question-meta {{
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 10px;
            padding: 5px 10px;
            background: rgba(0,0,0,0.05);
            border-radius: 5px;
        }}
        
        .content {{
            font-family: monospace;
            font-size: 0.9rem;
            line-height: 1.4;
            white-space: pre-wrap;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 5px;
            background: white;
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .issues-panel {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 5px;
            padding: 15px;
            margin-top: 15px;
        }}
        
        .issue-critical {{
            color: #721c24;
            font-weight: bold;
        }}
        
        .issue-major {{
            color: #856404;
        }}
        
        .issue-minor {{
            color: #155724;
        }}
        
        .navigation {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-height: 70vh;
            overflow-y: auto;
            min-width: 200px;
        }}
        
        .nav-item {{
            display: block;
            padding: 8px 12px;
            text-decoration: none;
            color: #333;
            border-radius: 5px;
            margin-bottom: 5px;
            font-size: 0.9rem;
        }}
        
        .nav-item:hover {{
            background: #e9ecef;
        }}
        
        .nav-item.critical {{
            border-left: 4px solid #dc3545;
        }}
        
        .nav-item.major {{
            border-left: 4px solid #ffc107;
        }}
        
        .nav-item.good {{
            border-left: 4px solid #28a745;
        }}
        
        @media (max-width: 768px) {{
            .comparison-container {{
                grid-template-columns: 1fr;
            }}
            
            .navigation {{
                position: relative;
                width: 100%;
                margin-bottom: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 PDF vs Extracted Data - Visual Comparison</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="navigation">
        <h3>📍 Navigation</h3>
"""
    
    # Load PDF content for comparison
    pdf_content_cache = {}
    pdf_dir = Path(pdf_dir)
    
    for pdf_file in pdf_dir.glob("Questions_*.pdf"):
        try:
            with pdfplumber.open(pdf_file) as pdf:
                pdf_content_cache[pdf_file.name] = {}
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text(layout=True) or page.extract_text()
                    if text:
                        pdf_content_cache[pdf_file.name][page_num] = text
        except Exception as e:
            print(f"Error loading {pdf_file.name}: {e}")
    
    # Generate navigation and content
    questions = questions_data.get('questions', [])
    
    for i, question in enumerate(questions[:20]):  # Limit to first 20 for performance
        question_id = question.get('id', f'Q{i}')
        source_file = question.get('source', question.get('metadata', {}).get('source', ''))
        page_num = question.get('page', question.get('metadata', {}).get('page', 0))
        
        # Determine issue severity for navigation
        description = question.get('description', '')
        has_community_pollution = any(term in description.lower() for term in 
                                    ['upvoted', 'highly voted', 'most recent', 'ago'])
        has_ocr_errors = any(error in description for error in 
                           ['ConKgure', 'ReconKgure', 'traOc', 'solu"on'])
        
        if has_community_pollution:
            nav_class = 'critical'
        elif has_ocr_errors or len(question.get('options', {})) < 4:
            nav_class = 'major'
        else:
            nav_class = 'good'
        
        html_content += f'        <a href="#{question_id}" class="nav-item {nav_class}">{question_id} - Page {page_num}</a>\n'
    
    html_content += """    </div>

"""
    
    # Generate comparison content
    for i, question in enumerate(questions[:20]):  # Limit to first 20
        question_id = question.get('id', f'Q{i}')
        source_file = question.get('source', question.get('metadata', {}).get('source', ''))
        page_num = question.get('page', question.get('metadata', {}).get('page', 0))
        
        # Get PDF content
        pdf_text = ""
        if source_file in pdf_content_cache and page_num in pdf_content_cache[source_file]:
            pdf_text = pdf_content_cache[source_file][page_num]
        
        # Get extracted content
        extracted_description = question.get('description', 'No description')
        extracted_options = question.get('options', {})
        
        # Identify issues
        issues = []
        description = question.get('description', '')
        
        if 'upvoted' in description.lower():
            issues.append(("CRITICAL", "Community comment 'upvoted' found in question text"))
        if 'highly voted' in description.lower():
            issues.append(("CRITICAL", "Community comment 'Highly Voted' found in question text"))
        if any(error in description for error in ['ConKgure', 'ReconKgure', 'traOc']):
            issues.append(("MAJOR", "OCR errors detected in question text"))
        if len(extracted_options) < 4:
            issues.append(("MAJOR", f"Only {len(extracted_options)} answer options found (expected 4-6)"))
        if len(description) < 50:
            issues.append(("CRITICAL", "Question description too short - possible truncation"))
        
        # Format options for display
        options_text = ""
        for letter, text in extracted_options.items():
            options_text += f"{letter}. {text}\n"
        
        html_content += f"""    <div class="comparison-container" id="{question_id}">
        <div class="pdf-section">
            <div class="section-title pdf-title">📄 Original PDF Content</div>
            <div class="question-meta">Source: {source_file} | Page: {page_num}</div>
            <div class="content">{pdf_text[:2000] if pdf_text else 'PDF content not available'}</div>
        </div>
        
        <div class="extracted-section">
            <div class="section-title extracted-title">🔄 Extracted Data</div>
            <div class="question-meta">Question ID: {question_id} | Confidence: {question.get('confidence', question.get('metadata', {}).get('confidence', 0)):.1%}</div>
            
            <div style="margin-bottom: 15px;">
                <strong>Question:</strong>
                <div class="content" style="max-height: 200px;">{extracted_description}</div>
            </div>
            
            <div>
                <strong>Options:</strong>
                <div class="content" style="max-height: 200px;">{options_text if options_text else 'No options extracted'}</div>
            </div>
            
            {f'''
            <div class="issues-panel">
                <strong>🚨 Issues Detected:</strong>
                {chr(10).join([f'<div class="issue-{issue[0].lower()}">{issue[0]}: {issue[1]}</div>' for issue in issues])}
            </div>
            ''' if issues else ''}
        </div>
    </div>
    
"""
    
    html_content += """    <div style="text-align: center; margin-top: 40px; padding: 20px; background: white; border-radius: 10px;">
        <h3>📊 Summary</h3>
        <p>This comparison shows the first 20 questions for detailed analysis.</p>
        <p>Use the navigation panel to jump to specific questions.</p>
        <p><strong>Color Coding:</strong> 🔴 Critical Issues | 🟡 Major Issues | 🟢 Good Quality</p>
    </div>
    
</body>
</html>"""
    
    return html_content

def main():
    """Generate visual comparison HTML"""
    print("🔍 Creating Visual Comparison Tool")
    print("=" * 50)
    
    # Load questions data
    questions_file = Path("./data/output/questions_web_data.json")
    
    if not questions_file.exists():
        print(f"❌ Questions data file not found: {questions_file}")
        return False
    
    try:
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        print("📄 Generating HTML comparison...")
        html_content = create_html_comparison(questions_data)
        
        # Save HTML file
        output_dir = Path("./data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = output_dir / f"visual_comparison_{timestamp}.html"
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ Visual comparison generated: {html_file}")
        print(f"🌐 Open in browser: file://{html_file.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)