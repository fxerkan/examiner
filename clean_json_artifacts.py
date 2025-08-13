#!/usr/bin/env python3
"""
Script to clean hexadecimal character artifacts from JSON data
"""

import json
import re
import os

def clean_unicode_artifacts(text):
    """Clean Unicode artifacts from text"""
    if not isinstance(text, str):
        return text
    
    # Remove specific problematic Unicode characters
    text = text.replace('\uf147', '').replace('\uf007', '').replace('\uf0c9', '')
    text = text.replace('\u2588', '').replace('\u2590', '').replace('\u2591', '')
    
    # Remove other Unicode symbols in private use areas
    text = re.sub(r'[\uf000-\uf8ff]', '', text)
    
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text

def clean_json_recursively(obj):
    """Recursively clean all strings in a JSON object"""
    if isinstance(obj, dict):
        return {key: clean_json_recursively(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_recursively(item) for item in obj]
    elif isinstance(obj, str):
        return clean_unicode_artifacts(obj)
    else:
        return obj

def main():
    input_file = '/Users/erkanciftci/repo_local/examtopics_extractor/web_ui/questions_web_data.json'
    backup_file = input_file + '.backup'
    
    # Create backup
    if os.path.exists(input_file):
        with open(input_file, 'r', encoding='utf-8') as f:
            with open(backup_file, 'w', encoding='utf-8') as b:
                b.write(f.read())
        print(f"✅ Backup created: {backup_file}")
    
    # Read and clean the JSON
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("🔧 Cleaning Unicode artifacts...")
        cleaned_data = clean_json_recursively(data)
        
        # Write the cleaned data back
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        print("✅ JSON file cleaned successfully!")
        print(f"📁 Original backed up as: {backup_file}")
        print(f"📄 Cleaned file: {input_file}")
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        if os.path.exists(backup_file):
            print("🔄 Restoring from backup...")
            with open(backup_file, 'r', encoding='utf-8') as b:
                with open(input_file, 'w', encoding='utf-8') as f:
                    f.write(b.read())

if __name__ == "__main__":
    main()