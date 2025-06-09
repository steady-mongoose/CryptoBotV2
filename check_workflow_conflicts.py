
#!/usr/bin/env python3
"""
Workflow Conflict Checker
Prevents duplicate posts by checking for running workflows and recent activity.
"""

import sys
import argparse
from modules.workflow_manager import workflow_manager

def check_conflicts(workflow_type: str) -> bool:
    """
    Check for workflow conflicts before running.
    Returns True if conflicts exist (should cancel), False if safe to proceed.
    """
    print(f"🔍 Checking conflicts for workflow: {workflow_type}")
    
    has_conflict, reason = workflow_manager.check_workflow_conflicts(workflow_type)
    
    if has_conflict:
        print(f"❌ WORKFLOW CANCELLED: {reason}")
        print("🛡️ Duplicate post prevention activated")
        return True
    else:
        print(f"✅ No conflicts detected: {reason}")
        print(f"🚀 Safe to proceed with {workflow_type}")
        # Register that this workflow is starting
        workflow_manager.register_workflow_start(workflow_type)
        return False

def complete_workflow(workflow_type: str):
    """Mark workflow as completed."""
    workflow_manager.register_workflow_complete(workflow_type)
    print(f"✅ Workflow {workflow_type} marked as completed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check workflow conflicts")
    parser.add_argument('--type', required=True, help='Workflow type to check')
    parser.add_argument('--complete', action='store_true', help='Mark workflow as completed')
    
    args = parser.parse_args()
    
    if args.complete:
        complete_workflow(args.type)
    else:
        has_conflicts = check_conflicts(args.type)
        sys.exit(1 if has_conflicts else 0)
