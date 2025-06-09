
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psutil
import sqlite3

logger = logging.getLogger('CryptoBot')

WORKFLOW_STATE_FILE = "workflow_state.json"

class WorkflowManager:
    """Manage workflow states and prevent conflicts."""
    
    def __init__(self):
        self.state_file = WORKFLOW_STATE_FILE
        self.load_state()
    
    def load_state(self) -> Dict:
        """Load workflow state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading workflow state: {e}")
        return {}
    
    def save_state(self, state: Dict):
        """Save workflow state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving workflow state: {e}")
    
    def is_workflow_running(self, workflow_type: str) -> bool:
        """Check if a workflow is currently running."""
        state = self.load_state()
        workflow_data = state.get(workflow_type, {})
        
        if not workflow_data.get('running', False):
            return False
        
        # Check if process is actually running
        pid = workflow_data.get('pid')
        if pid and psutil.pid_exists(pid):
            return True
        
        # Clean up stale state
        self.mark_workflow_completed(workflow_type)
        return False
    
    def start_workflow(self, workflow_type: str) -> bool:
        """Mark a workflow as started."""
        if self.is_workflow_running(workflow_type):
            return False
        
        state = self.load_state()
        state[workflow_type] = {
            'running': True,
            'started_at': datetime.now().isoformat(),
            'pid': os.getpid()
        }
        self.save_state(state)
        return True
    
    def mark_workflow_completed(self, workflow_type: str):
        """Mark a workflow as completed."""
        state = self.load_state()
        if workflow_type in state:
            state[workflow_type] = {
                'running': False,
                'completed_at': datetime.now().isoformat()
            }
            self.save_state(state)
    
    def check_conflicts(self, workflow_type: str) -> Optional[str]:
        """Check for workflow conflicts."""
        conflicting_workflows = {
            'post_to_x': ['post_to_discord', 'test_mode'],
            'post_to_discord': ['post_to_x'],
            'test_mode': ['post_to_x', 'post_to_discord']
        }
        
        conflicts = conflicting_workflows.get(workflow_type, [])
        
        for conflict in conflicts:
            if self.is_workflow_running(conflict):
                return f"Conflict with running workflow: {conflict}"
        
        return None
    
    def check_workflow_conflicts(self, workflow_type: str) -> tuple:
        """Check for workflow conflicts and return (has_conflict, reason)."""
        try:
            # Validate workflow type exists
            valid_workflows = ['post_to_x', 'post_to_discord', 'test_mode', 'content_verification', 'queue_check']
            if workflow_type not in valid_workflows:
                return True, f"Invalid workflow type: {workflow_type}"
            
            # Check if workflow is already running
            if self.is_workflow_running(workflow_type):
                return True, f"Workflow {workflow_type} is already running"
            
            # Check for conflicting workflows
            conflict_reason = self.check_conflicts(workflow_type)
            if conflict_reason:
                return True, conflict_reason
            
            # Cross-reference with database state if available
            try:
                self._validate_with_database(workflow_type)
            except Exception as db_error:
                logger.warning(f"Database validation failed for {workflow_type}: {db_error}")
            
            # Check system resources
            if not self._check_system_resources():
                return True, "Insufficient system resources"
            
            return False, f"No conflicts found for {workflow_type}"
            
        except Exception as e:
            logger.error(f"Error checking workflow conflicts: {e}")
            return True, f"Error during conflict check: {e}"
    
    def register_workflow_start(self, workflow_type: str) -> bool:
        """Register that a workflow is starting."""
        return self.start_workflow(workflow_type)
    
    def register_workflow_complete(self, workflow_type: str):
        """Register that a workflow has completed."""
        self.mark_workflow_completed(workflow_type)
    
    def _validate_with_database(self, workflow_type: str):
        """Cross-reference workflow state with database if available."""
        try:
            # Check if database file exists and is accessible
            db_file = "crypto_bot.db"
            if os.path.exists(db_file):
                with sqlite3.connect(db_file) as conn:
                    cursor = conn.cursor()
                    # Check recent workflow history
                    cursor.execute('''
                        SELECT COUNT(*) FROM workflow_history 
                        WHERE workflow_type = ? AND timestamp > datetime('now', '-5 minutes')
                    ''', (workflow_type,))
                    recent_runs = cursor.fetchone()[0]
                    
                    if recent_runs > 3:
                        raise Exception(f"Too many recent runs of {workflow_type}")
        except sqlite3.Error as e:
            logger.warning(f"Database validation error: {e}")
        except Exception as e:
            raise e
    
    def _check_system_resources(self) -> bool:
        """Check if system has sufficient resources."""
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning("High memory usage detected")
                return False
            
            # Check disk space
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                logger.warning("Low disk space detected")
                return False
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                logger.warning("High CPU usage detected")
                return False
            
            return True
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return True  # Allow execution if check fails
    
    def validate_workflow_dependencies(self, workflow_type: str) -> Dict:
        """Validate all dependencies for a workflow type."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check required files based on workflow type
            required_files = {
                'post_to_x': ['bot_v2.py', 'modules/api_clients.py', 'modules/x_thread_queue.py'],
                'post_to_discord': ['bot_v2.py', 'modules/api_clients.py'],
                'content_verification': ['modules/content_verification.py'],
                'queue_check': ['check_queue_status.py']
            }
            
            workflow_files = required_files.get(workflow_type, [])
            for file_path in workflow_files:
                if not os.path.exists(file_path):
                    validation_results['valid'] = False
                    validation_results['errors'].append(f"Missing required file: {file_path}")
            
            # Check for configuration files
            config_files = ['.replit', 'requirements.txt']
            for config_file in config_files:
                if not os.path.exists(config_file):
                    validation_results['warnings'].append(f"Missing config file: {config_file}")
            
            # Validate modules can be imported
            if workflow_type in ['post_to_x', 'post_to_discord']:
                try:
                    import modules.api_clients
                    import modules.database
                except ImportError as e:
                    validation_results['valid'] = False
                    validation_results['errors'].append(f"Module import error: {e}")
            
        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation error: {e}")
        
        return validation_results
    
    def reset_all_workflows(self):
        """Reset all workflow states."""
        self.save_state({})
        logger.info("All workflow states reset")

# Global workflow manager instance
workflow_manager = WorkflowManager()
