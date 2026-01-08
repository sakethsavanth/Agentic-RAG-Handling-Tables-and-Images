"""
Logging Utilities
Simple logger that writes to both console and file
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class TeeLogger:
    """
    Simple logger that writes to both console and file simultaneously
    Like the Unix 'tee' command
    """
    
    def __init__(self, log_folder: str = "query results", log_name: Optional[str] = None):
        """
        Initialize TeeLogger
        
        Args:
            log_folder: Folder to store log files
            log_name: Optional specific name for log file. If None, uses timestamp
        """
        # Create log folder if it doesn't exist
        self.log_folder = Path(log_folder)
        self.log_folder.mkdir(exist_ok=True)
        
        # Generate log filename with timestamp
        if log_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_name = f"log_{timestamp}.txt"
        
        self.log_file = self.log_folder / log_name
        
        # Open file for writing
        self.file = open(self.log_file, 'w', encoding='utf-8')
        
        # Save original stdout
        self.original_stdout = sys.stdout
        
        print(f"📝 Logging to: {self.log_file}")
    
    def write(self, message):
        """Write to both console and file"""
        self.original_stdout.write(message)
        self.file.write(message)
        self.file.flush()  # Ensure immediate write
    
    def flush(self):
        """Flush both outputs"""
        self.original_stdout.flush()
        self.file.flush()
    
    def close(self):
        """Close the log file and restore stdout"""
        if hasattr(self, 'file') and self.file and not self.file.closed:
            self.file.close()
            print(f"✅ Log saved to: {self.log_file}")
    
    def __enter__(self):
        """Context manager entry - redirect stdout"""
        sys.stdout = self
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - restore stdout"""
        sys.stdout = self.original_stdout
        self.close()


def get_log_filename(prefix: str = "log", query: Optional[str] = None, max_length: int = 40) -> str:
    """
    Generate a timestamped log filename
    
    Args:
        prefix: Prefix for the log file
        query: Optional query string to include in filename
        max_length: Maximum length for query part of filename
    
    Returns:
        Safe filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if query:
        # Sanitize query for filename
        safe_query = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in query)
        safe_query = safe_query.strip().replace(' ', '_')
        
        # Truncate if too long
        if len(safe_query) > max_length:
            safe_query = safe_query[:max_length]
        
        return f"{prefix}_{timestamp}_{safe_query}.txt"
    else:
        return f"{prefix}_{timestamp}.txt"
