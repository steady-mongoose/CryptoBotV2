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

    try:
        # Import error handler
        from modules.error_handler import error_handler

        # System health check
        health_status = error_handler.check_system_health()
        if not health_status["healthy"]:
            print(f"❌ WORKFLOW CANCELLED: System health check failed")
            for error in health_status["errors"]:
                print(f"   💥 {error}")
            return True

        # Show health warnings
        for warning in health_status["warnings"]:
            print(f"⚠️  System warning: {warning}")

        # Comprehensive validation
        validation_results = workflow_manager.validate_workflow_dependencies(workflow_type)

        if not validation_results['valid']:
            print(f"❌ WORKFLOW CANCELLED: Dependency validation failed")
            for error in validation_results['errors']:
                print(f"   • {error}")
                error_handler.handle_error(
                    ValidationError(error), 
                    f"Workflow {workflow_type} dependency check"
                )
            return True

        # Show warnings but don't block execution
        for warning in validation_results['warnings']:
            print(f"⚠️  Warning: {warning}")

        # Check for conflicts
        has_conflict, reason = workflow_manager.check_workflow_conflicts(workflow_type)

        if has_conflict:
            print(f"❌ WORKFLOW CANCELLED: {reason}")
            print("🛡️ Conflict prevention activated")
            error_handler.handle_error(
                WorkflowError(reason), 
                f"Workflow {workflow_type} conflict check",
                "warning"
            )
            return True
        else:
            print(f"✅ No conflicts detected: {reason}")
            print(f"🚀 Safe to proceed with {workflow_type}")
            print(f"💚 System health: {'Healthy' if health_status['healthy'] else 'Issues detected'}")

            # Register that this workflow is starting
            success = workflow_manager.register_workflow_start(workflow_type)
            if not success:
                print(f"⚠️  Warning: Could not register workflow start")
                error_handler.handle_error(
                    WorkflowError("Failed to register workflow start"),
                    f"Workflow {workflow_type} registration",
                    "warning"
                )

            return False

    except Exception as e:
        print(f"❌ CONFLICT CHECK FAILED: {e}")
        print("🚫 Cancelling workflow due to check failure")
        logger.error(f"Workflow conflict check error: {e}")

        # Handle with error handler
        try:
            from modules.error_handler import error_handler
            error_handler.handle_error(e, f"Workflow {workflow_type} conflict check")
        except:
            pass  # Error handler itself failed

        return True

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