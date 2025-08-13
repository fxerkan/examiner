#!/usr/bin/env python3
"""
Simple API server for handling question data updates
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

class QuestionAPIHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path.startswith('/api/questions'):
            self.serve_questions()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests for updating questions"""
        if self.path.startswith('/api/questions/update'):
            self.update_question()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def serve_questions(self):
        """Serve the questions JSON file"""
        try:
            with open('questions_web_data.json', 'r', encoding='utf-8') as f:
                data = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(data.encode('utf-8'))
            
        except FileNotFoundError:
            self.send_error(404, "Questions data file not found")
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")
    
    def update_question(self):
        """Update a question in the JSON file"""
        try:
            # Read the request data
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            # Load existing data
            with open('questions_web_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Find and update the question
            question_id = update_data.get('id')
            if not question_id:
                self.send_error(400, "Missing question ID")
                return
            
            updated = False
            for i, question in enumerate(data.get('questions', [])):
                if question.get('id') == question_id:
                    # Update question fields
                    if 'number' in update_data:
                        question['number'] = update_data['number']
                    if 'description' in update_data:
                        question['description'] = update_data['description']
                    if 'options' in update_data:
                        question['options'] = update_data['options']
                    if 'metadata' in update_data:
                        question['metadata'].update(update_data['metadata'])
                    
                    updated = True
                    break
            
            if not updated:
                self.send_error(404, "Question not found")
                return
            
            # Save updated data
            with open('questions_web_data.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Also update the main data file
            main_data_path = '../data/output/clean_questions_web_data.json'
            if os.path.exists(main_data_path):
                with open(main_data_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True, 
                'message': 'Question updated successfully'
            }).encode('utf-8'))
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON data")
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def start_api_server(port=9002):
    """Start the API server"""
    server = HTTPServer(('localhost', port), QuestionAPIHandler)
    print(f"🚀 Question API server starting on http://localhost:{port}")
    print("📝 Available endpoints:")
    print("  GET  /api/questions - Get all questions")
    print("  POST /api/questions/update - Update a question")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped")
        server.shutdown()

if __name__ == '__main__':
    # Change to web_ui directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    start_api_server()