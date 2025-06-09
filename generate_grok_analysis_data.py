
#!/usr/bin/env python3
"""
Grok Analysis Data Generator
Comprehensive data export for AI analysis of the crypto bot project.
"""

import os
import json
import logging
import sqlite3
from datetime import datetime
import subprocess
import sys
from pathlib import Path

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def gather_project_structure():
    """Get complete project structure."""
    project_structure = {}
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if not file.startswith('.') and not file.endswith('.pyc'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    project_structure[file_path] = {
                        'type': 'text',
                        'size': len(content),
                        'content': content,
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    }
                except Exception as e:
                    project_structure[file_path] = {
                        'type': 'binary',
                        'size': os.path.getsize(file_path),
                        'error': str(e),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    }
    
    return project_structure

def gather_database_data():
    """Extract all database information."""
    database_data = {}
    
    try:
        # Check if database exists
        if os.path.exists('crypto_bot.db'):
            conn = sqlite3.connect('crypto_bot.db')
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            database_data['tables'] = {}
            for table in tables:
                table_name = table[0]
                try:
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    
                    database_data['tables'][table_name] = {
                        'columns': columns,
                        'row_count': len(rows),
                        'data': rows[:100]  # Limit to first 100 rows
                    }
                except Exception as e:
                    database_data['tables'][table_name] = {'error': str(e)}
            
            conn.close()
        else:
            database_data['error'] = 'Database file not found'
            
    except Exception as e:
        database_data['error'] = str(e)
    
    return database_data

def gather_log_files():
    """Collect all log files and their contents."""
    log_data = {}
    
    # Common log file patterns
    log_patterns = ['*.log', '*.json', '*_log*', 'error_*', 'workflow_*']
    
    for pattern in log_patterns:
        for file_path in Path('.').glob(pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    log_data[str(file_path)] = {
                        'size': len(content),
                        'content': content,
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                except Exception as e:
                    log_data[str(file_path)] = {'error': str(e)}
    
    return log_data

def gather_system_info():
    """Collect system and environment information."""
    system_info = {}
    
    try:
        # Python version and packages
        system_info['python_version'] = sys.version
        
        # Try to get installed packages
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                                  capture_output=True, text=True, timeout=30)
            system_info['installed_packages'] = result.stdout
        except Exception as e:
            system_info['packages_error'] = str(e)
        
        # Environment variables (safe ones only)
        safe_env_vars = ['PATH', 'PYTHONPATH', 'HOME', 'USER', 'REPL_SLUG', 'REPL_OWNER']
        system_info['environment'] = {var: os.getenv(var, 'Not set') for var in safe_env_vars}
        
        # Disk usage
        try:
            statvfs = os.statvfs('.')
            system_info['disk_usage'] = {
                'total_space': statvfs.f_frsize * statvfs.f_blocks,
                'free_space': statvfs.f_frsize * statvfs.f_available,
                'used_space': statvfs.f_frsize * (statvfs.f_blocks - statvfs.f_available)
            }
        except Exception as e:
            system_info['disk_error'] = str(e)
            
    except Exception as e:
        system_info['error'] = str(e)
    
    return system_info

def gather_workflow_data():
    """Extract workflow configurations and states."""
    workflow_data = {}
    
    try:
        # Read .replit file
        if os.path.exists('.replit'):
            with open('.replit', 'r') as f:
                workflow_data['replit_config'] = f.read()
        
        # Read workflow state
        if os.path.exists('workflow_state.json'):
            with open('workflow_state.json', 'r') as f:
                workflow_data['workflow_state'] = json.load(f)
        
        # Check for any other workflow-related files
        for file_path in Path('.').glob('*workflow*'):
            if file_path.is_file():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        workflow_data[str(file_path)] = f.read()
                except Exception as e:
                    workflow_data[f'{file_path}_error'] = str(e)
                    
    except Exception as e:
        workflow_data['error'] = str(e)
    
    return workflow_data

def gather_api_status():
    """Check API configurations and status."""
    api_status = {}
    
    try:
        # Import modules to check their status
        sys.path.append('.')
        
        # Check API clients
        try:
            from modules.api_clients import get_x_client_with_failover, get_discord_webhook_url
            
            # Test X API (without posting)
            try:
                client, account_num = get_x_client_with_failover(posting_only=True)
                api_status['x_api'] = {
                    'available': bool(client),
                    'account_number': account_num if client else None
                }
            except Exception as e:
                api_status['x_api'] = {'error': str(e)}
            
            # Test Discord webhook
            try:
                webhook_url = get_discord_webhook_url()
                api_status['discord'] = {
                    'configured': bool(webhook_url),
                    'has_url': bool(webhook_url)
                }
            except Exception as e:
                api_status['discord'] = {'error': str(e)}
                
        except Exception as e:
            api_status['api_clients_error'] = str(e)
        
        # Check queue status
        try:
            from modules.x_thread_queue import get_x_queue_status
            api_status['queue_status'] = get_x_queue_status()
        except Exception as e:
            api_status['queue_error'] = str(e)
            
    except Exception as e:
        api_status['error'] = str(e)
    
    return api_status

def gather_recent_exports():
    """Find and include recent export files."""
    exports = {}
    
    # Look for export files
    export_patterns = ['*export*.json', '*thread*.json', 'x_thread_export_*', 'direct_post_*']
    
    for pattern in export_patterns:
        for file_path in Path('.').glob(pattern):
            if file_path.is_file():
                try:
                    with open(file_path, 'r') as f:
                        exports[str(file_path)] = json.load(f)
                except Exception as e:
                    exports[f'{file_path}_error'] = str(e)
    
    return exports

def main():
    """Generate comprehensive Grok analysis data."""
    print("🔍 GENERATING GROK ANALYSIS DATA")
    print("=" * 50)
    
    timestamp = get_timestamp()
    
    # Gather all data
    print("📁 Collecting project structure...")
    project_structure = gather_project_structure()
    
    print("🗄️ Extracting database data...")
    database_data = gather_database_data()
    
    print("📋 Gathering log files...")
    log_data = gather_log_files()
    
    print("🖥️ Collecting system information...")
    system_info = gather_system_info()
    
    print("⚙️ Gathering workflow data...")
    workflow_data = gather_workflow_data()
    
    print("🔌 Checking API status...")
    api_status = gather_api_status()
    
    print("📤 Finding recent exports...")
    exports = gather_recent_exports()
    
    # Compile comprehensive data
    grok_analysis_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'project_name': 'crypto_bot_v2',
            'analysis_type': 'comprehensive_project_export',
            'export_version': '1.0'
        },
        'project_structure': project_structure,
        'database_data': database_data,
        'log_files': log_data,
        'system_info': system_info,
        'workflow_data': workflow_data,
        'api_status': api_status,
        'recent_exports': exports,
        'summary': {
            'total_files': len(project_structure),
            'total_logs': len(log_data),
            'database_tables': len(database_data.get('tables', {})),
            'workflow_configs': len(workflow_data),
            'api_endpoints': len(api_status)
        }
    }
    
    # Save to file
    output_filename = f"grok_analysis_data_{timestamp}.json"
    
    print(f"💾 Saving to {output_filename}...")
    with open(output_filename, 'w') as f:
        json.dump(grok_analysis_data, f, indent=2, default=str)
    
    # Create human-readable summary
    summary_filename = f"grok_analysis_summary_{timestamp}.txt"
    
    print(f"📄 Creating summary in {summary_filename}...")
    with open(summary_filename, 'w') as f:
        f.write("CRYPTO BOT V2 - GROK ANALYSIS DATA SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("PROJECT OVERVIEW:\n")
        f.write(f"- Total Files: {len(project_structure)}\n")
        f.write(f"- Log Files: {len(log_data)}\n")
        f.write(f"- Database Tables: {len(database_data.get('tables', {}))}\n")
        f.write(f"- Workflow Configs: {len(workflow_data)}\n")
        f.write(f"- Recent Exports: {len(exports)}\n\n")
        
        f.write("KEY FILES:\n")
        key_files = ['bot_v2.py', 'modules/x_thread_queue.py', 'modules/api_clients.py', '.replit']
        for file in key_files:
            if file in project_structure:
                f.write(f"- {file} ({project_structure[file]['size']} bytes)\n")
        
        f.write("\nAPI STATUS:\n")
        if 'x_api' in api_status:
            f.write(f"- X API: {'Available' if api_status['x_api'].get('available') else 'Not Available'}\n")
        if 'discord' in api_status:
            f.write(f"- Discord: {'Configured' if api_status['discord'].get('configured') else 'Not Configured'}\n")
        if 'queue_status' in api_status:
            queue = api_status['queue_status']
            f.write(f"- Queue: {queue.get('queue_size', 0)} pending, Worker: {queue.get('worker_running', False)}\n")
        
        f.write("\nRECENT ACTIVITY:\n")
        for log_file, log_info in log_data.items():
            if 'modified' in log_info:
                f.write(f"- {log_file}: Modified {log_info['modified']}\n")
    
    print("\n" + "=" * 50)
    print("✅ GROK ANALYSIS DATA GENERATED SUCCESSFULLY")
    print("=" * 50)
    print(f"📁 Main Data File: {output_filename}")
    print(f"📄 Summary File: {summary_filename}")
    print(f"📊 Total Data Size: {os.path.getsize(output_filename) / 1024 / 1024:.2f} MB")
    print("\n🚀 Ready for Grok Analysis!")
    print("Upload both files to Grok for comprehensive project analysis.")

if __name__ == "__main__":
    main()
