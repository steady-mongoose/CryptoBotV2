
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psutil

logger = logging.getLogger('CryptoBot')

WORKFLOW_STATE_FILE = "workflow_state.json"

class WorkflowManager:
    def __init__(self):
        self.state_file = WORKFLOW_STATE_FILE
        self.conflict_check_window = timedelta(minutes=15)  # Prevent duplicates within 15 min
        
    def load_workflow_state(self) -> Dict:
        """Load current workflow state."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading workflow state: {e}")
        return {}
    
    def save_workflow_state(self, state: Dict):
        """Save workflow state."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving workflow state: {e}")
    
    def check_workflow_conflicts(self, workflow_type: str) -> tuple[bool, str]:
        """
        Check if workflow would cause duplicate posts.
        Returns: (has_conflict, reason)
        """
        state = self.load_workflow_state()
        current_time = datetime.now()
        
        # Check for recent runs of same type
        last_run_key = f"last_{workflow_type}_run"
        if last_run_key in state:
            try:
                last_run = datetime.fromisoformat(state[last_run_key])
                time_since = current_time - last_run
                
                if time_since < self.conflict_check_window:
                    return True, f"Duplicate prevention: {workflow_type} ran {time_since.total_seconds():.0f}s ago"
            except:
                pass
        
        # Check for conflicting X posting workflows
        x_posting_types = ['post_to_x', 'post_to_both', 'post_x_streams']
        if workflow_type in x_posting_types:
            for other_type in x_posting_types:
                if other_type != workflow_type:
                    other_key = f"last_{other_type}_run"
                    if other_key in state:
                        try:
                            other_run = datetime.fromisoformat(state[other_key])
                            time_since = current_time - other_run
                            
                            if time_since < timedelta(minutes=10):  # Stricter for X posts
                                return True, f"X posting conflict: {other_type} ran {time_since.total_seconds():.0f}s ago"
                        except:
                            pass
        
        # Check for running bot processes
        if self.is_bot_process_running():
            return True, "Bot process already running - would cause duplicate posts"
        
        return False, "No conflicts detected"
    
    def register_workflow_start(self, workflow_type: str):
        """Register that a workflow has started."""
        state = self.load_workflow_state()
        state[f"last_{workflow_type}_run"] = datetime.now().isoformat()
        state[f"{workflow_type}_status"] = "running"
        self.save_workflow_state(state)
        
    def register_workflow_complete(self, workflow_type: str):
        """Register that a workflow has completed."""
        state = self.load_workflow_state()
        state[f"{workflow_type}_status"] = "completed"
        self.save_workflow_state(state)
    
    def is_bot_process_running(self) -> bool:
        """Check if bot process is already running."""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 1:
                        if 'bot_v2.py' in ' '.join(cmdline) and proc.info['pid'] != os.getpid():
                            return True
                except:
                    continue
            return False
        except Exception as e:
            logger.error(f"Error checking bot processes: {e}")
            return False

# Global instance
workflow_manager = WorkflowManager()
