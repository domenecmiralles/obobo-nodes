"""
Worker Manager for persistent worker state and process management
"""

import json
import logging
import os
import subprocess
import sys
import socket
from pathlib import Path
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class WorkerManager:
    def __init__(self, worker_dir: str, api_url: Optional[str] = None):
        self.worker_dir = Path(worker_dir)
        self.state_file = self.worker_dir / "worker_state.json"
        self.log_dir = self.worker_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Load worker state from file
        state = self._load_state()
        was_empty_state = not state or 'worker_id' not in state
        
        self.worker_id = state.get('worker_id', self._get_consistent_worker_id())
        self.user_id = state.get('user_id')
        
        # Save state if we generated a new worker_id
        if was_empty_state:
            self._save_state()
        
        # Store API URL for future use
        self.api_url = api_url
        
        # Sync with API if URL is provided to get latest user_id
        if self.api_url:
            self._sync_user_id_from_api()
    
    def _get_consistent_worker_id(self) -> str:
        """Generate a consistent worker ID based on hostname and ComfyUI port"""
        hostname = socket.gethostname()
        return f"comfyui-{hostname}-8188"
    
    def _load_state(self) -> Dict[str, Any]:
        """Load worker state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load worker state: {e}")
        return {}
    
    def _save_state(self):
        """Save worker state to file"""
        try:
            state = {'worker_id': self.worker_id}
            if self.user_id:
                state['user_id'] = self.user_id
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save worker state: {e}")
    
    def _get_worker_status_from_api(self, worker_id: str, api_url: str) -> Optional[Dict[str, Any]]:
        """Get worker status from API endpoint"""
        try:
            import requests
            response = requests.get(f"{api_url}/v1/worker/{worker_id}")
            response.raise_for_status()
            api_data = response.json()
            logger.info(f"Successfully fetched worker {worker_id} status from API")
            return api_data
        except Exception as e:
            logger.error(f"Failed to get worker {worker_id} status from API: {e}")
            return None
    
    def _sync_user_id_from_api(self):
        """Sync user_id from API if available"""
        if not self.api_url:
            return
            
        api_data = self._get_worker_status_from_api(self.worker_id, self.api_url)
        if api_data and 'user_id' in api_data:
            new_user_id = api_data.get('user_id')
            if new_user_id != self.user_id:
                self.user_id = new_user_id
                self._save_state()
                logger.info(f"Updated user_id from API: {self.user_id}")
    
    def _register_worker_in_api(self, worker_id: str, api_url: str) -> bool:
        """Register/reactivate worker in the API"""
        try:
            import requests
            from utils.device import get_gpu_info
            
            gpus = get_gpu_info()
            
            response = requests.post(
                f"{api_url}/v1/worker/register/{worker_id}",
                json={"gpus": [g.model_dump() for g in gpus]}
            )
            response.raise_for_status()
            logger.info(f"Successfully registered worker {worker_id} in API")
            return True
        except Exception as e:
            logger.error(f"Failed to register worker {worker_id} in API: {e}")
            return False
    
    def start_worker(self, api_url: str) -> Dict[str, Any]:
        """Start the single worker"""
        
        # Store API URL for future use
        self.api_url = api_url
        
        # Sync user_id from API before starting
        self._sync_user_id_from_api()
        
        # Check current worker status from API
        api_data = self._get_worker_status_from_api(self.worker_id, api_url)
        if api_data and api_data.get('status') == 'active':
            return {
                'success': False,
                'message': 'Worker is already active according to API',
                'worker_id': self.worker_id
            }
        
        # Prepare log files
        log_file = self.log_dir / f"{self.worker_id}.log"
        error_log_file = self.log_dir / f"{self.worker_id}_error.log"
        
        # Command to start the worker
        cmd = [
            sys.executable, "main.py",
            "--api-url", api_url,
            "--worker_id", self.worker_id,
            "--comfyui_server", "http://127.0.0.1:8188",
            "--batch", "{}"
        ]
        
        # Environment setup
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.worker_dir.parent.parent.parent.parent)
        
        try:
            # Start the worker process
            with open(log_file, 'a') as log_f, open(error_log_file, 'a') as err_f:
                process = subprocess.Popen(
                    cmd,
                    cwd=str(self.worker_dir),
                    stdout=log_f,
                    stderr=err_f,
                    env=env,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
            
            # Register worker in API
            api_success = self._register_worker_in_api(self.worker_id, api_url)
            
            logger.info(f"Started worker {self.worker_id} with PID {process.pid}")
            
            return {
                'success': True,
                'message': 'Worker started successfully',
                'worker_id': self.worker_id,
                'pid': process.pid,
                'api_registered': api_success
            }
                
        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}")
            return {
                'success': False,
                'message': f'Failed to start worker: {str(e)}',
                'worker_id': self.worker_id
            }
    
    def stop_worker(self) -> Dict[str, Any]:
        """Stop the single worker via API"""
        if not self.api_url:
            return {'success': False, 'message': 'No API URL configured'}
        
        # Deactivate worker via API
        api_success = self._deactivate_worker_in_api(self.worker_id, self.api_url)
        
        if api_success:
            return {
                'success': True,
                'message': f'Worker {self.worker_id} stopped via API',
                'worker_id': self.worker_id
            }
        else:
            return {
                'success': False,
                'message': f'Failed to stop worker {self.worker_id} via API',
                'worker_id': self.worker_id
            }
    
    def _deactivate_worker_in_api(self, worker_id: str, api_url: str) -> bool:
        """Deactivate worker using the DELETE endpoint"""
        try:
            import requests
            response = requests.delete(f"{api_url}/v1/worker/{worker_id}")
            response.raise_for_status()
            logger.info(f"Successfully deactivated worker {worker_id} in API")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate worker {worker_id} in API: {e}")
            return False
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get status of the single worker from API"""
        if not self.api_url:
            return {
                'success': False,
                'message': 'No API URL configured',
                'total_workers': 0,
                'active_workers': 0,
                'workers': {}
            }
        
        api_data = self._get_worker_status_from_api(self.worker_id, self.api_url)
        
        if api_data:
            status = api_data.get('status', 'inactive')
            is_active = status == 'active'
            
            # Update local user_id if it's in the API response
            if 'user_id' in api_data and api_data['user_id'] != self.user_id:
                self.user_id = api_data['user_id']
                self._save_state()
            
            return {
                'success': True,
                'total_workers': 1,
                'active_workers': 1 if is_active else 0,
                'workers': {self.worker_id: api_data}
            }
        else:
            return {
                'success': False,
                'message': 'Failed to get worker status from API',
                'total_workers': 1,
                'active_workers': 0,
                'workers': {self.worker_id: {'worker_id': self.worker_id, 'status': 'unknown'}}
            }
    
    def get_worker_logs(self, worker_id: str, lines: int = 50) -> Dict[str, Any]:
        """Get recent logs for the worker from local files"""
        if worker_id != self.worker_id:
            return {
                'success': False,
                'message': f'Worker {worker_id} not found'
            }
        
        log_file = self.log_dir / f"{worker_id}.log"
        error_log_file = self.log_dir / f"{worker_id}_error.log"
        
        logs = {}
        
        # Read stdout log
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    log_lines = f.readlines()
                    logs['stdout'] = ''.join(log_lines[-lines:])
            except Exception as e:
                logs['stdout'] = f"Error reading log: {e}"
        else:
            logs['stdout'] = "Log file not found"
        
        # Read stderr log
        if error_log_file.exists():
            try:
                with open(error_log_file, 'r') as f:
                    error_lines = f.readlines()
                    logs['stderr'] = ''.join(error_lines[-lines:])
            except Exception as e:
                logs['stderr'] = f"Error reading error log: {e}"
        else:
            logs['stderr'] = "Error log file not found"
        
        return {
            'success': True,
            'worker_id': worker_id,
            'logs': logs
        } 