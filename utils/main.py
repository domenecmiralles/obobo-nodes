import argparse
import asyncio
import logging
import sys
import time
import uuid
import subprocess
import os
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
import requests
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from device import get_gpu_info
    from database import get_s3_client
    from comfyui import queue_claimed_jobs, jobs_in_comfyui_queue, check_completed_jobs_and_get_outputs, upload_completed_jobs, unload_models_and_empty_memory
    logger.info("🎬 Successfully imported ComfyUI utilities")
except ImportError as e:
    logger.error(f"🎬 Failed to import ComfyUI utilities: {e}")
    # Fallback imports for development/testing
    def get_gpu_info():
        logger.warning("🎬 Using fallback get_gpu_info()")
        return []
    def get_s3_client():
        logger.warning("🎬 Using fallback get_s3_client()")
        return None
    def queue_claimed_jobs(*args):
        logger.warning("🎬 Using fallback queue_claimed_jobs()")
        return []
    def jobs_in_comfyui_queue(*args):
        logger.warning("🎬 Using fallback jobs_in_comfyui_queue()")
        return 0
    def check_completed_jobs_and_get_outputs(*args):
        logger.warning("🎬 Using fallback check_completed_jobs_and_get_outputs()")
        return []
    def upload_completed_jobs(*args):
        logger.warning("🎬 Using fallback upload_completed_jobs()")
        return []
    def unload_models_and_empty_memory(*args):
        logger.warning("🎬 Using fallback unload_models_and_empty_memory()")
        pass


class ComfyUIWorker:
    def __init__(self, api_url: str, secret_id: Optional[str] = None, comfyui_server: str = "http://127.0.0.1:8188"):
        self.api_url = api_url.rstrip("/")
        self.secret_id = secret_id or str(uuid.uuid4())
        self.worker_id = f"comfyui-{self.secret_id}"
        self.registered = False
        self.gpus = get_gpu_info()
        self.comfyui_server = comfyui_server
        self.s3_client = get_s3_client()
        self.comfyui_output_path = "ComfyUI/output"
        self.last_workflow_url = None
        self.batch_wait_time = 15
        self.running = False
        self.task = None

    def register(self) -> bool:
        """Register worker with the API"""
        try:
            response = requests.post(
                f"{self.api_url}/v1/worker/register/{self.worker_id}",
                json={"gpus": [g.model_dump() for g in self.gpus]},
                timeout=10
            )
            response.raise_for_status()
            self.registered = True
            logger.info(f"Successfully registered worker {self.worker_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register worker: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to API"""
        try:
            response = requests.post(
                f"{self.api_url}/v1/worker/heartbeat/{self.worker_id}",
                timeout=5
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False

    def unregister(self) -> bool:
        """Unregister worker from API"""
        try:
            response = requests.delete(
                f"{self.api_url}/v1/worker/{self.worker_id}",
                timeout=10
            )
            response.raise_for_status()
            self.registered = False
            logger.info(f"Successfully unregistered worker {self.worker_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister worker: {e}")
            return False

    def get_next_batch(self) -> Optional[Dict[str, Any]]:
        """Get next batch from API"""
        try:
            response = requests.get(
                f"{self.api_url}/v1/inference/batch/{self.worker_id}",
                timeout=10
            )
            # if status is 204, return None
            if response.status_code == 204:
                return None
            else:
                return response.json()
        except Exception as e:
            logger.error(f"Error getting next batch: {e}")
            self.registered = False
            return None

    async def process_batch(self, batch: Dict[str, Any]) -> bool:
        """Process a batch of work using ComfyUI"""
        max_batch_processing_time = 3600
        start_time = time.time()
        
        try:
            logger.info(f"🎬 Starting batch processing for {len(batch['generations'])} generations")
            logger.info(f"🎬 Workflow URL: {batch['workflow_url']}")
            
            # Unload models if workflow changed
            if self.last_workflow_url != batch["workflow_url"]:
                logger.info(f"🎬 Workflow changed, unloading models. Old: {self.last_workflow_url}, New: {batch['workflow_url']}")
                unload_models_and_empty_memory(self.comfyui_server)
                self.last_workflow_url = batch["workflow_url"]
            else:
                logger.info("🎬 Same workflow as before, keeping models loaded")
            
            # Queue jobs in ComfyUI
            logger.info("🎬 Queueing jobs in ComfyUI...")
            queued_jobs = queue_claimed_jobs(
                batch["generations"],
                self.comfyui_server,
                self.api_url,
            )
            
            logger.info(f"🎬 Successfully queued {len(queued_jobs)} jobs in ComfyUI")
            
            if len(queued_jobs) == 0:
                logger.error("🎬 No jobs were successfully queued - check ComfyUI logs")
                return False
            
            # Log the queued jobs for debugging
            for i, job in enumerate(queued_jobs):
                logger.info(f"🎬 Queued job {i+1}: ID={job.job['_id']}, prompt_id={job.prompt_id}")
            
            previous_jobs_in_queue = 0
            loop_count = 0
            
            while self.running:
                loop_count += 1
                jobs_in_queue = jobs_in_comfyui_queue(self.comfyui_server)
                
                if loop_count % 10 == 0:  # Log every 10 iterations to avoid spam
                    logger.info(f"🎬 Loop {loop_count}: {jobs_in_queue} jobs in ComfyUI queue, {len(queued_jobs)} jobs tracking")
                
                if jobs_in_queue - previous_jobs_in_queue < 0 or jobs_in_queue == 0:
                    logger.info("🎬 Jobs completed or queue decreased, checking for outputs...")
                    # Check for completed jobs and upload them
                    before_count = len(queued_jobs)
                    queued_jobs = check_completed_jobs_and_get_outputs(
                        queued_jobs, self.comfyui_output_path, self.comfyui_server, self.api_url
                    )
                    queued_jobs = upload_completed_jobs(
                        queued_jobs,
                        self.api_url,
                        "movies",
                        self.s3_client,
                        "obobo-media-production",
                    )
                    after_count = len(queued_jobs)
                    
                    if before_count != after_count:
                        logger.info(f"🎬 Processed {before_count - after_count} completed jobs, {after_count} remaining")
                    
                    if len(queued_jobs) == 0:
                        logger.info("🎬 All jobs completed successfully!")
                        break
                
                previous_jobs_in_queue = jobs_in_queue
                
                # Check for timeout
                if time.time() - start_time > max_batch_processing_time:
                    logger.error(f"🎬 Batch processing timed out after {max_batch_processing_time} seconds")
                    unload_models_and_empty_memory(self.comfyui_server)
                    return False

                # Wait if jobs are still in queue
                if jobs_in_queue > 0:
                    await asyncio.sleep(5)
                elif not queued_jobs:
                    break

                await asyncio.sleep(1)  # Prevent tight loop
            
            await asyncio.sleep(5)
            logger.info("🎬 Batch processing completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"🎬 Error processing batch: {e}")
            logger.error(f"🎬 Exception details: {traceback.format_exc()}")
            return False

    async def run_worker(self):
        """Main worker loop"""
        logger.info("🎬 Starting worker main loop...")
        self.running = True
        loop_iteration = 0
        
        while self.running:
            try:
                loop_iteration += 1
                logger.info(f"🎬 Worker loop iteration {loop_iteration}")
                
                # Register if not registered
                if not self.registered and not self.register():
                    logger.error("🎬 Failed to register worker, retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                # Send heartbeat
                if not self.send_heartbeat():
                    logger.error("🎬 Failed to send heartbeat, attempting to re-register...")
                    self.registered = False
                    continue

                # Get and process next batch
                logger.info("🎬 Checking for available batches...")
                batch = self.get_next_batch()
                if batch:
                    logger.info(f"🎬 Received batch data: {batch}")
                    logger.info(f"🎬 Processing batch with {len(batch['generations'])} generations")
                    batch_result = await self.process_batch(batch)
                    logger.info(f"🎬 Batch processing result: {batch_result}")
                else:
                    logger.info(f"🎬 No batches available, waiting {self.batch_wait_time} seconds...")
                    await asyncio.sleep(self.batch_wait_time)

            except Exception as e:
                logger.error(f"🎬 Error in worker loop iteration {loop_iteration}: {e}")
                logger.error(f"🎬 Worker loop exception details: {traceback.format_exc()}")
                self.registered = False
                await asyncio.sleep(self.batch_wait_time)

    def start_worker(self, skip_comfyui_check: bool = False) -> Dict[str, Any]:
        """Start the worker in the background"""
        try:
            if self.running:
                return {"success": False, "message": "Worker is already running"}
            
            # Test connection to ComfyUI (skip if running as extension)
            if not skip_comfyui_check:
                try:
                    logger.info(f"Testing connection to ComfyUI at {self.comfyui_server}")
                    response = requests.get(f"{self.comfyui_server}/system_stats", timeout=10)
                    if response.status_code != 200:
                        return {"success": False, "message": f"ComfyUI server returned status {response.status_code}"}
                    logger.info("ComfyUI connection test successful")
                except requests.exceptions.Timeout:
                    return {"success": False, "message": "ComfyUI server connection timed out - server may be busy"}
                except requests.exceptions.ConnectionError:
                    return {"success": False, "message": "Cannot connect to ComfyUI server - make sure it's running"}
                except Exception as e:
                    return {"success": False, "message": f"ComfyUI connection error: {str(e)}"}
            else:
                logger.info("Skipping ComfyUI connection test (running as extension)")
            
            # Register worker
            if not self.register():
                return {"success": False, "message": "Failed to register worker with API"}
            
            # Start worker task
            logger.info("🎬 Creating async worker task...")
            self.task = asyncio.create_task(self.run_worker())
            logger.info(f"🎬 Worker task created: {self.task}")
            
            result = {
                "success": True, 
                "secret_id": str(self.secret_id),
                "worker_id": str(self.worker_id),
                "message": "Worker started successfully"
            }
            
            logger.info(f"Worker start result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to start worker: {e}")
            error_result = {"success": False, "message": f"Failed to start worker: {str(e)}"}
            logger.info(f"Worker start error result: {error_result}")
            return error_result

    def stop_worker(self) -> Dict[str, Any]:
        """Stop the worker"""
        try:
            self.running = False
            
            if self.task:
                self.task.cancel()
                self.task = None
            
            if self.registered:
                self.unregister()
            
            result = {"success": True, "message": "Worker stopped successfully"}
            logger.info(f"Worker stop result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to stop worker: {e}")
            error_result = {"success": False, "message": f"Failed to stop worker: {str(e)}"}
            logger.info(f"Worker stop error result: {error_result}")
            return error_result

    def get_status(self) -> Dict[str, Any]:
        """Get worker status"""
        status = {
            "running": bool(self.running),
            "registered": bool(self.registered),
            "worker_id": str(self.worker_id),
            "secret_id": str(self.secret_id),
            "api_url": str(self.api_url),
            "comfyui_server": str(self.comfyui_server)
        }
        logger.info(f"Worker status: {status}")
        return status


# Global worker instance
_worker_instance = None

def get_worker_instance(api_url: str = "https://inference.obobo.net", secret_id: Optional[str] = None) -> ComfyUIWorker:
    """Get or create the global worker instance"""
    global _worker_instance
    if _worker_instance is None or _worker_instance.api_url != api_url:
        _worker_instance = ComfyUIWorker(api_url, secret_id)
    return _worker_instance

def start_worker(api_url: str = "https://inference.obobo.net", skip_comfyui_check: bool = True) -> Dict[str, Any]:
    """Start the worker"""
    worker = get_worker_instance(api_url)
    return worker.start_worker(skip_comfyui_check=skip_comfyui_check)

def stop_worker() -> Dict[str, Any]:
    """Stop the worker"""
    global _worker_instance
    if _worker_instance:
        return _worker_instance.stop_worker()
    return {"success": True, "message": "No worker was running"}

def get_worker_status() -> Dict[str, Any]:
    """Get worker status"""
    global _worker_instance
    if _worker_instance:
        return _worker_instance.get_status()
    status = {"running": False, "registered": False}
    logger.info(f"Global worker status (no instance): {status}")
    return status

def main():
    """CLI interface for testing"""
    parser = argparse.ArgumentParser(description="Obobo ComfyUI Worker")
    parser.add_argument(
        "--api-url",
        default="https://inference.obobo.net",
        help="URL of the inference API",
    )
    parser.add_argument(
        "--secret-id",
        help="Secret ID for the worker",
    )
    parser.add_argument(
        "--comfyui-server",
        default="http://127.0.0.1:8188",
        help="ComfyUI server URL",
    )
    parser.add_argument(
        "--action",
        choices=["start", "stop", "status"],
        default="start",
        help="Action to perform"
    )

    args = parser.parse_args()

    if args.action == "start":
        worker = ComfyUIWorker(args.api_url, args.secret_id, args.comfyui_server)
        # For CLI usage, we do want to check ComfyUI connection
        result = worker.start_worker(skip_comfyui_check=False)
        print(json.dumps(result, indent=2))
        
        if result["success"]:
            try:
                asyncio.run(worker.run_worker())
            except KeyboardInterrupt:
                worker.stop_worker()
                print("Worker stopped")
                
    elif args.action == "stop":
        result = stop_worker()
        print(json.dumps(result, indent=2))
        
    elif args.action == "status":
        result = get_worker_status()
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 