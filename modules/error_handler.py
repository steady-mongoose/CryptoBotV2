
import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os

logger = logging.getLogger('CryptoBot')

class CryptoBotError(Exception):
    """Base exception for CryptoBot errors."""
    pass

class APIError(CryptoBotError):
    """API-related errors."""
    pass

class ValidationError(CryptoBotError):
    """Data validation errors."""
    pass

class WorkflowError(CryptoBotError):
    """Workflow execution errors."""
    pass

class ErrorHandler:
    """Centralized error handling and reporting."""
    
    def __init__(self):
        self.error_log_file = "error_log.json"
        self.load_error_history()
    
    def load_error_history(self) -> Dict:
        """Load error history from file."""
        try:
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load error history: {e}")
        return {"errors": [], "warnings": [], "last_updated": None}
    
    def save_error_history(self, error_data: Dict):
        """Save error to history file."""
        try:
            history = self.load_error_history()
            history["errors"].append(error_data)
            history["last_updated"] = datetime.now().isoformat()
            
            # Keep only last 100 errors
            if len(history["errors"]) > 100:
                history["errors"] = history["errors"][-100:]
            
            with open(self.error_log_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save error history: {e}")
    
    def handle_error(self, error: Exception, context: str = "", severity: str = "error") -> Dict[str, Any]:
        """Handle and log errors with context."""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "severity": severity,
            "traceback": traceback.format_exc() if severity == "error" else None
        }
        
        # Log based on severity
        if severity == "error":
            logger.error(f"❌ {context}: {error}")
        elif severity == "warning":
            logger.warning(f"⚠️ {context}: {error}")
        else:
            logger.info(f"ℹ️ {context}: {error}")
        
        # Save to history
        self.save_error_history(error_data)
        
        return error_data
    
    def validate_api_response(self, response: Any, expected_fields: list, context: str = "") -> Dict[str, Any]:
        """Validate API responses."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "context": context
        }
        
        try:
            if not response:
                validation_result["valid"] = False
                validation_result["errors"].append("Empty response received")
                return validation_result
            
            # Check for expected fields
            for field in expected_fields:
                if isinstance(response, dict) and field not in response:
                    validation_result["warnings"].append(f"Missing expected field: {field}")
                elif hasattr(response, field) and not getattr(response, field):
                    validation_result["warnings"].append(f"Empty field: {field}")
            
            # Check for common error indicators
            if isinstance(response, dict):
                if "error" in response:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"API error: {response['error']}")
                
                if "status" in response and response["status"] != "success":
                    validation_result["warnings"].append(f"Non-success status: {response['status']}")
        
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def check_system_health(self) -> Dict[str, Any]:
        """Perform system health checks."""
        health_status = {
            "healthy": True,
            "checks": {},
            "errors": [],
            "warnings": []
        }
        
        try:
            import psutil
            
            # Memory check
            memory = psutil.virtual_memory()
            health_status["checks"]["memory_percent"] = memory.percent
            if memory.percent > 90:
                health_status["healthy"] = False
                health_status["errors"].append(f"High memory usage: {memory.percent}%")
            elif memory.percent > 75:
                health_status["warnings"].append(f"Elevated memory usage: {memory.percent}%")
            
            # Disk check
            disk = psutil.disk_usage('/')
            health_status["checks"]["disk_percent"] = disk.percent
            if disk.percent > 95:
                health_status["healthy"] = False
                health_status["errors"].append(f"Low disk space: {disk.percent}% used")
            elif disk.percent > 85:
                health_status["warnings"].append(f"Disk space running low: {disk.percent}% used")
            
            # Check critical files
            critical_files = ["bot_v2.py", "modules/api_clients.py", "modules/x_thread_queue.py"]
            for file_path in critical_files:
                if not os.path.exists(file_path):
                    health_status["healthy"] = False
                    health_status["errors"].append(f"Missing critical file: {file_path}")
            
        except Exception as e:
            health_status["healthy"] = False
            health_status["errors"].append(f"Health check failed: {str(e)}")
        
        return health_status

# Global error handler instance
error_handler = ErrorHandler()
