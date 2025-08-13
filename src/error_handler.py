"""
Error Handler Module for GCP Exam Question Extractor
Provides comprehensive error handling, logging, and recovery mechanisms
"""

import logging
import json
import traceback
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from functools import wraps
from dataclasses import dataclass

@dataclass
class ErrorInfo:
    """Error information structure"""
    timestamp: str
    error_type: str
    error_message: str
    context: str
    traceback: str
    severity: str
    recoverable: bool

class ErrorHandler:
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.error_log = []
        self.setup_logging()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        if config_path is None:
            config_path = "./project_config.json"
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Default error handling configuration"""
        return {
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "examtopics_processor.log",
                "max_file_size_mb": 100,
                "backup_count": 5
            },
            "error_handling": {
                "max_retries": 3,
                "retry_delay": 2,
                "save_error_reports": True,
                "email_critical_errors": False
            }
        }
    
    def setup_logging(self):
        """Setup comprehensive logging system"""
        log_config = self.config.get("logging", {})
        
        # Create logs directory
        logs_dir = Path("./logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Setup root logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_config.get("level", "INFO")))
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            logs_dir / log_config.get("file", "examtopics_processor.log"),
            maxBytes=log_config.get("max_file_size_mb", 100) * 1024 * 1024,
            backupCount=log_config.get("backup_count", 5)
        )
        file_handler.setFormatter(logging.Formatter(
            log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            "%(levelname)s - %(name)s - %(message)s"
        ))
        
        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Error handling system initialized")
    
    def handle_error(self, error: Exception, context: str = "", severity: str = "ERROR", 
                    recoverable: bool = True) -> ErrorInfo:
        """
        Handle and log errors with context
        
        Args:
            error: Exception object
            context: Context where error occurred
            severity: Error severity level
            recoverable: Whether the error is recoverable
            
        Returns:
            ErrorInfo object with error details
        """
        error_info = ErrorInfo(
            timestamp=datetime.now().isoformat(),
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            traceback=traceback.format_exc(),
            severity=severity,
            recoverable=recoverable
        )
        
        # Log the error
        log_message = f"Error in {context}: {error_info.error_message}"
        
        if severity == "CRITICAL":
            self.logger.critical(log_message)
        elif severity == "ERROR":
            self.logger.error(log_message)
        elif severity == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Store error for reporting
        self.error_log.append(error_info)
        
        # Save error report if configured
        if self.config.get("error_handling", {}).get("save_error_reports", True):
            self._save_error_report(error_info)
        
        return error_info
    
    def _save_error_report(self, error_info: ErrorInfo):
        """Save detailed error report to file"""
        try:
            error_reports_dir = Path("./logs/error_reports")
            error_reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = error_reports_dir / f"error_report_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump({
                    "timestamp": error_info.timestamp,
                    "error_type": error_info.error_type,
                    "error_message": error_info.error_message,
                    "context": error_info.context,
                    "traceback": error_info.traceback,
                    "severity": error_info.severity,
                    "recoverable": error_info.recoverable,
                    "system_info": self._get_system_info()
                }, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save error report: {str(e)}")
    
    def _get_system_info(self) -> Dict:
        """Get system information for error reports"""
        import platform
        import psutil
        
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage('/').percent
        }
    
    def retry_on_failure(self, max_retries: int = None, delay: float = None):
        """
        Decorator for retrying failed operations
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
        """
        if max_retries is None:
            max_retries = self.config.get("error_handling", {}).get("max_retries", 3)
        if delay is None:
            delay = self.config.get("error_handling", {}).get("retry_delay", 2)
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        if attempt < max_retries:
                            context = f"{func.__name__} (attempt {attempt + 1}/{max_retries + 1})"
                            self.handle_error(e, context, "WARNING", True)
                            
                            import time
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff
                        else:
                            context = f"{func.__name__} (final attempt failed)"
                            self.handle_error(e, context, "ERROR", False)
                
                raise last_exception
            
            return wrapper
        return decorator
    
    def validate_input(self, data: Any, expected_type: type, field_name: str = "input") -> bool:
        """
        Validate input data types and structures
        
        Args:
            data: Data to validate
            expected_type: Expected data type
            field_name: Name of the field being validated
            
        Returns:
            True if validation passes
        """
        try:
            if not isinstance(data, expected_type):
                raise TypeError(f"{field_name} must be of type {expected_type.__name__}, got {type(data).__name__}")
            
            return True
            
        except Exception as e:
            self.handle_error(e, f"Input validation for {field_name}", "ERROR", False)
            return False
    
    def validate_file_path(self, file_path: str, must_exist: bool = True) -> bool:
        """
        Validate file path
        
        Args:
            file_path: Path to validate
            must_exist: Whether file must exist
            
        Returns:
            True if validation passes
        """
        try:
            if not file_path:
                raise ValueError("File path cannot be empty")
            
            path = Path(file_path)
            
            if must_exist and not path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if must_exist and not path.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            
            return True
            
        except Exception as e:
            self.handle_error(e, f"File path validation for {file_path}", "ERROR", False)
            return False
    
    def safe_json_load(self, file_path: str) -> Optional[Dict]:
        """
        Safely load JSON file with error handling
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Loaded JSON data or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.handle_error(FileNotFoundError(f"JSON file not found: {file_path}"), 
                            "JSON loading", "WARNING", True)
        except json.JSONDecodeError as e:
            self.handle_error(e, f"JSON decode error in {file_path}", "ERROR", True)
        except Exception as e:
            self.handle_error(e, f"Unexpected error loading JSON: {file_path}", "ERROR", True)
        
        return None
    
    def safe_json_save(self, data: Dict, file_path: str) -> bool:
        """
        Safely save JSON file with error handling
        
        Args:
            data: Data to save
            file_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            self.handle_error(e, f"Error saving JSON to {file_path}", "ERROR", True)
            return False
    
    def check_disk_space(self, required_mb: float = 100) -> bool:
        """
        Check if sufficient disk space is available
        
        Args:
            required_mb: Required space in MB
            
        Returns:
            True if sufficient space available
        """
        try:
            import psutil
            free_space_mb = psutil.disk_usage('.').free / (1024 * 1024)
            
            if free_space_mb < required_mb:
                error_msg = f"Insufficient disk space: {free_space_mb:.1f}MB available, {required_mb}MB required"
                self.handle_error(Exception(error_msg), "Disk space check", "WARNING", True)
                return False
            
            return True
            
        except Exception as e:
            self.handle_error(e, "Disk space check", "WARNING", True)
            return True  # Assume OK if check fails
    
    def check_memory_usage(self, max_memory_percent: float = 80.0) -> bool:
        """
        Check current memory usage
        
        Args:
            max_memory_percent: Maximum acceptable memory usage percentage
            
        Returns:
            True if memory usage is acceptable
        """
        try:
            import psutil
            memory_percent = psutil.virtual_memory().percent
            
            if memory_percent > max_memory_percent:
                warning_msg = f"High memory usage: {memory_percent:.1f}% (threshold: {max_memory_percent}%)"
                self.handle_error(Exception(warning_msg), "Memory usage check", "WARNING", True)
                return False
            
            return True
            
        except Exception as e:
            self.handle_error(e, "Memory usage check", "WARNING", True)
            return True  # Assume OK if check fails
    
    def generate_error_summary(self) -> Dict:
        """
        Generate summary of all errors encountered
        
        Returns:
            Dictionary with error statistics and details
        """
        if not self.error_log:
            return {"total_errors": 0, "error_summary": "No errors recorded"}
        
        # Group errors by type
        error_by_type = {}
        error_by_severity = {}
        
        for error in self.error_log:
            error_by_type[error.error_type] = error_by_type.get(error.error_type, 0) + 1
            error_by_severity[error.severity] = error_by_severity.get(error.severity, 0) + 1
        
        return {
            "total_errors": len(self.error_log),
            "error_by_type": error_by_type,
            "error_by_severity": error_by_severity,
            "recoverable_errors": sum(1 for e in self.error_log if e.recoverable),
            "critical_errors": sum(1 for e in self.error_log if e.severity == "CRITICAL"),
            "recent_errors": [
                {
                    "timestamp": e.timestamp,
                    "type": e.error_type,
                    "message": e.error_message,
                    "context": e.context,
                    "severity": e.severity
                }
                for e in self.error_log[-5:]  # Last 5 errors
            ]
        }
    
    def save_error_summary(self, output_file: str = None) -> str:
        """
        Save error summary to file
        
        Args:
            output_file: Output file path
            
        Returns:
            Path to saved summary file
        """
        if output_file is None:
            logs_dir = Path("./logs")
            logs_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = logs_dir / f"error_summary_{timestamp}.json"
        
        summary = self.generate_error_summary()
        
        if self.safe_json_save(summary, str(output_file)):
            self.logger.info(f"Error summary saved to: {output_file}")
            return str(output_file)
        else:
            return ""