import argparse
import asyncio
import logging
import sys
import time
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from utils.device import get_gpu_info
from utils.database import get_s3_client
from utils.comfyui import queue_claimed_jobs, jobs_in_comfyui_queue, check_completed_jobs_and_get_outputs, upload_completed_jobs, unload_models_and_empty_memory

# example usage for local develpopment
# CUDA_VISIBLE_DEVICES=0 python worker/main.py --api-url http://localhost:8001 --comfyui_server http://127.0.0.1:8188 --worker_id test-worker --batch "{}"
# CUDA_VISIBLE_DEVICES=0 python worker/main.py --api-url https://inference.obobo.net --comfyui_server http://127.0.0.1:8188 --worker_id test-worker --batch "{}"

COMFYUI_PATH = "../../.."

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, api_url: str, worker_id: str, batch: Optional[str] = None, comfyui_server: Optional[str] = None, idle_timeout: int = 300, shutdown_machine: bool = False, instance_id: Optional[str] = None, tunnel_url: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.worker_id = worker_id
        self.registered = False
        self.gpus = get_gpu_info()
        self.batch = batch
        self.comfyui_server = comfyui_server
        # Tunnel URL is provided by the parent script
        self.tunnel_url = tunnel_url
        self.s3_client = get_s3_client()
        self.comfyui_output_path = f"{COMFYUI_PATH}/output"
        self.last_workflow_url = None
        self.batch_wait_time = 15
        # Add auto-shutdown tracking
        self.last_job_time = time.time()
        self.max_idle_time = idle_timeout  # Use provided timeout
        self.should_shutdown = False
        self.shutdown_machine = shutdown_machine
        self.instance_id = instance_id

    def test_comfyui_connectivity(self) -> bool:
        """Test if ComfyUI is responding and ready"""
        try:
            # Use the /prompt endpoint which returns queue info - this is a real ComfyUI endpoint
            response = requests.get(f"{self.comfyui_server}/prompt", timeout=5)
            if response.status_code == 200:
                # Check if the response has the expected structure
                data = response.json()
                return "exec_info" in data
            return False
        except Exception as e:
            logger.debug(f"ComfyUI not ready yet: {e}")
            return False

    def register(self) -> bool:
        """Register worker with the API"""
        try:
            # First, ensure ComfyUI is ready
            logger.info("Checking ComfyUI connectivity before registration...")
            if not self.test_comfyui_connectivity():
                logger.info("ComfyUI not ready yet, will retry registration later")
                return False

            # Log tunnel URL if provided
            if self.tunnel_url:
                logger.info(f"Using tunnel URL: {self.tunnel_url}")
            else:
                logger.info("No tunnel URL provided")
        
            import re
            port_match = re.search(r':(\d+)', self.comfyui_server)
            comfyui_port = int(port_match.group(1)) if port_match else 8188
            
            logger.info("ComfyUI is ready, registering worker...")
            if self.instance_id:
                logger.info(f"Registering worker with instance ID: {self.instance_id}")
            response = requests.post(
                f"{self.api_url}/v1/worker/register/{self.worker_id}",
                json={
                    "gpus": [g.model_dump() for g in self.gpus],
                    "port_address": str(comfyui_port),
                    "tunnel_url": self.tunnel_url,
                    "instance_id": self.instance_id,
                    
                    },
            )
            response.raise_for_status()
            self.registered = True
            
            if self.tunnel_url:
                logger.info(f"Successfully registered and activated worker {self.worker_id} with tunnel: {self.tunnel_url}")
            else:
                logger.info(f"Successfully registered and activated worker {self.worker_id}")
            return True
                
        except Exception as e:
            logger.error(f"Failed to register worker: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to API to indicate worker is still alive"""
        try:
            response = requests.post(f"{self.api_url}/v1/worker/heartbeat/{self.worker_id}")
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False

    def unregister(self) -> bool:
        """Unregister worker from API"""
        try:
            response = requests.delete(f"{self.api_url}/v1/worker/{self.worker_id}")
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
                f"{self.api_url}/v1/inference/batch/{self.worker_id}"
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
        """
        Process a batch of work.
        This is a dummy implementation - replace with actual processing logic.
        """
        max_batch_processing_time = 3600
        start_time = time.time()
        last_heartbeat_time = time.time()
        heartbeat_interval = 30  # Send heartbeat every 30 seconds during processing
        
        if self.last_workflow_url != batch["workflow_url"]:
            unload_models_and_empty_memory(self.comfyui_server)
            self.last_workflow_url = batch["workflow_url"]
        queued_jobs = queue_claimed_jobs(
                batch["generations"],
                self.comfyui_server,
                self.api_url,
            )
        previous_jobs_in_queue = 0
        while True:
            current_time = time.time()
            
            # Send heartbeat periodically during processing
            if current_time - last_heartbeat_time >= heartbeat_interval:
                if not self.send_heartbeat():
                    logger.warning("Failed to send heartbeat during batch processing, but continuing...")
                last_heartbeat_time = current_time
            
            jobs_in_queue = jobs_in_comfyui_queue(self.comfyui_server)
            if jobs_in_queue - previous_jobs_in_queue < 0 or jobs_in_queue == 0:
                # if jobs in queue is less than previous jobs in queue, upload the completed jobs
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
                if len(queued_jobs) == 0:
                    break
            previous_jobs_in_queue = jobs_in_queue
            if time.time() - start_time > max_batch_processing_time:
                logger.error(f"Batch processing timed out after {max_batch_processing_time} seconds")
                # unload models and empty memory
                unload_models_and_empty_memory(self.comfyui_server)
                return False

            # if any jobs in the comfyui queue, wait
            if jobs_in_queue > 0:
                await asyncio.sleep(5)
            elif not queued_jobs:
                break

            await asyncio.sleep(1)  # Add a small delay to prevent tight loop
        await asyncio.sleep(5) 
        # unload_models_and_empty_memory(self.comfyui_server)
        # await asyncio.sleep(10) 
        return True





    async def run_single_batch(self):
        """Process a single specified batch and exit"""
        if not self.batch:
            logger.error(f"No batch ID provided for single batch mode")
            return

        try:
            # Register worker (includes readiness check and activation)
            if not self.register():
                logger.error(f"Failed to register worker in single batch mode")
                return

            # TODO: Implement actual batch fetching and processing
            logger.info(f"Processing single batch {len(self.batch)}")
            await asyncio.sleep(5)  # Simulate work
            logger.info(f"Completed single batch {len(self.batch)}")
        except Exception as e:
            logger.error(f"Error in single batch mode: {e}")
        finally:
            if self.registered:
                self.unregister()

    async def run_continuous(self):
        """Run in continuous mode, polling for batches"""
        shutdown_info = " (EC2 instance will be terminated)" if self.shutdown_machine else ""
        logger.info(f"Worker will auto-shutdown after {self.max_idle_time} seconds without jobs{shutdown_info}")
        
        while True:
            try:
                
                # Check if we should shutdown due to inactivity
                current_time = time.time()
                idle_time = current_time - self.last_job_time
                
                if idle_time > self.max_idle_time:
                    logger.info(f"No jobs received for {idle_time:.1f} seconds (>{self.max_idle_time}s). Initiating auto-shutdown...")
                    self.should_shutdown = True
                    break
                
                # Register (which includes readiness check and marking as active)
                if not self.registered and not self.register():
                    logger.error(f"Failed to register worker, retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                # Send heartbeat
                if not self.send_heartbeat():
                    logger.error(
                        f"Failed to send heartbeat, attempting to re-register..."
                    )
                    self.registered = False
                    continue

                # Get and process next batch
                batch = self.get_next_batch()
                if batch:
                    
                    # Reset idle timer when we get a job
                    self.last_job_time = time.time()
                    logger.info(f"Received batch data: {batch}")
                    logger.info(f"Processing batch with {len(batch['generations'])} generations")
                    await self.process_batch(batch)
                    # Reset idle timer after completing the batch processing
                    self.last_job_time = time.time() 
                else:
                    
                    # Log idle status every minute when no jobs
                    if int(idle_time) % 60 == 0 and int(idle_time) > 0:
                        remaining_time = self.max_idle_time - idle_time
                        logger.info(f"No jobs for {int(idle_time)}s. Will auto-shutdown in {int(remaining_time)}s if no jobs received.")
                    
                    logger.info(f"No batches available, waiting {self.batch_wait_time} seconds...")
                    await asyncio.sleep(self.batch_wait_time)

            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
                self.registered = False
                await asyncio.sleep(self.batch_wait_time)

    
    def signal_shutdown_to_parent(self):
        """Signal to parent process that we're shutting down due to inactivity"""
        try:
            # Create a flag file that run_workers.sh can check
            import os
            flag_file = f"/tmp/worker_shutdown_{self.worker_id}.flag"
            shutdown_type = "SHUTDOWN_MACHINE" if self.shutdown_machine else "SHUTDOWN_PROCESSES"
            
            # Ensure /tmp is writable and create the flag file
            os.makedirs("/tmp", exist_ok=True)
            with open(flag_file, 'w') as f:
                f.write(f"AUTO_SHUTDOWN_IDLE:{shutdown_type}:{time.time()}")
                f.flush()  # Ensure data is written immediately
                os.fsync(f.fileno())  # Force write to disk
            
            # Set readable permissions
            os.chmod(flag_file, 0o644)
            
            logger.info(f"Created shutdown flag: {flag_file} (type: {shutdown_type})")
            
            # Verify the file was created
            if os.path.exists(flag_file):
                logger.info(f"Flag file verified: {flag_file}")
                with open(flag_file, 'r') as f:
                    content = f.read()
                    logger.info(f"Flag file contents: {content}")
            else:
                logger.error(f"Flag file was not created: {flag_file}")
                
        except Exception as e:
            logger.error(f"Failed to create shutdown flag: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def run(self):
        """Main worker run loop"""
        try:
            if self.batch and self.batch != "{}":
                await self.run_single_batch()
            else:
                await self.run_continuous()
            
            # Check if shutdown was due to inactivity
            if self.should_shutdown:
                logger.info("Shutdown initiated due to inactivity. Signaling parent process...")
                self.signal_shutdown_to_parent()
                
        except KeyboardInterrupt:
            logger.info(f"Received shutdown signal")
        finally:
            if self.registered:
                self.unregister()
            
            if self.should_shutdown:
                logger.info("Worker auto-shutdown complete due to inactivity")
            else:
                logger.info("Worker shutdown complete")


def main():
    parser = argparse.ArgumentParser(description="Montecristo Inference Worker")
    parser.add_argument(
        "--api-url",
        required=False,
        default="inference.obobo.net",
        help="URL of the inference API",
    )
    parser.add_argument("--worker_id", required=True, help="Unique worker ID")
    parser.add_argument(
        "--comfyui_server",
        required=False,
        help="ComfyUI server URL",
        default="http://127.0.0.1:8188",
    )
    parser.add_argument("--batch", default=None, help="Optional batch ID for single batch mode")
    parser.add_argument("--idle_timeout", type=int, default=300, help="Maximum idle time in seconds before auto-shutdown (default: 300 = 5 minutes)")
    parser.add_argument("--shutdown_machine", action="store_true", help="Enable automatic EC2 instance termination after worker auto-shutdown")
    parser.add_argument("--instance_id", required=True, help="Instance ID for the worker")
    parser.add_argument("--tunnel_url", default=None, help="Tunnel URL provided by parent script")

    args = parser.parse_args()

    print(
        f"(ง •̀_•́)ง Starting worker with WORKER_ID {args.worker_id} and COMFYUI_SERVER {args.comfyui_server} and getting batches from API: {args.api_url}"
    )
    if args.instance_id:
        print(f"Instance ID: {args.instance_id}")
    if args.tunnel_url:
        print(f"Tunnel URL: {args.tunnel_url}")
    else:
        print("No tunnel URL provided")

    worker = Worker(
        api_url=args.api_url, 
        worker_id=args.worker_id, 
        batch=args.batch, 
        comfyui_server=args.comfyui_server, 
        idle_timeout=args.idle_timeout,
        shutdown_machine=args.shutdown_machine,
        instance_id=args.instance_id,
        tunnel_url=args.tunnel_url,
    )

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.unregister()
        logger.info(f"Worker shutdown complete")


if __name__ == "__main__":
    main()
