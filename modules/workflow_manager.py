
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psutil

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
    
    def reset_all_workflows(self):
        """Reset all workflow states."""
        self.save_state({})
        logger.info("All workflow states reset")

# Global workflow manager instance
workflow_manager = WorkflowManager()
