import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from utils.device import get_gpu_info
# from utils.database import get_s3_client
from utils.comfyui import queue_claimed_jobs, jobs_in_comfyui_queue, check_completed_jobs_and_get_outputs, upload_completed_jobs, unload_models_and_empty_memory
from oboboready.data.models import GenerationBatch

# Path to ComfyUI root directory (3 levels up from worker/)
COMFYUI_PATH = "../../.."

# example usage for local develpopment
# CUDA_VISIBLE_DEVICES=0 python worker/main.py --api-url http://localhost:8001 --comfyui_server http://127.0.0.1:8188 --worker_id test-worker --batch "{}"
# CUDA_VISIBLE_DEVICES=0 python worker/main.py --api-url https://inference.obobo.net --comfyui_server http://127.0.0.1:8188 --worker_id test-worker --batch "{}"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, api_url: str, worker_id: str, batch: Optional[str] = None, comfyui_server: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.worker_id = worker_id
        self.registered = False
        self.gpus = get_gpu_info()
        self.batch = batch
        self.comfyui_server = comfyui_server
        # self.s3_client = get_s3_client()
        self.comfyui_output_path = f"{COMFYUI_PATH}/output"
        self.last_workflow_url = None
        self.batch_wait_time = 15
    

    def register(self) -> bool:
        """Register worker with the API"""
        try:
            response = requests.post(
                f"{self.api_url}/v1/worker/register/{self.worker_id}",
                json={"gpus": [g.model_dump() for g in self.gpus]},
            )
            response.raise_for_status()
            self.registered = True
            logger.info(f"Successfully registered worker {self.worker_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register worker: {e}")
            return False

    def send_heartbeat(self) -> bool:
        return True
        # """Send heartbeat to API"""
        # try:
        #     response = requests.post(
        #         f"{self.api_url}/v1/worker/heartbeat/{self.worker_id}"
        #     )
        #     response.raise_for_status()
        #     return True
        # except Exception as e:
        #     logger.error(f"Failed to send heartbeat: {e}")
        #     return False

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
                    # self.s3_client,
                    # "obobo-media-production",
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
            logger.error("No batch ID provided for single batch mode")
            return

        try:
            # TODO: Implement actual batch fetching and processing
            logger.info(f"Processing single batch {len(self.batch)}")
            await asyncio.sleep(5)  # Simulate work
            logger.info(f"Completed single batch {len(self.batch)}")
        except Exception as e:
            logger.error(f"Error in single batch mode: {e}")
        finally:
            self.unregister()

    async def run_continuous(self):
        """Run in continuous mode, polling for batches"""
        while True:
            try:
                if not self.registered and not self.register():
                    logger.error("Failed to register worker, retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue

                # Send heartbeat
                if not self.send_heartbeat():
                    logger.error(
                        "Failed to send heartbeat, attempting to re-register..."
                    )
                    self.registered = False
                    continue

                # Get and process next batch
                batch = self.get_next_batch()
                if batch:
                    logger.info(f"Received batch data: {batch}")
                    logger.info(f"Processing batch with {len(batch['generations'])} generations")
                    await self.process_batch(batch) 
                else:
                    logger.info(f"No batches available, waiting {self.batch_wait_time} seconds...")
                    await asyncio.sleep(self.batch_wait_time)

            except Exception as e:
                logger.error(f"Error in continuous mode: {e}")
                self.registered = False
                await asyncio.sleep(self.batch_wait_time)

    async def run(self):
        """Main worker run loop"""
        try:
            if self.batch and self.batch != "{}":
                await self.run_single_batch()
            else:
                await self.run_continuous()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            if self.registered:
                self.unregister()


def main():
    parser = argparse.ArgumentParser(description="Montecristo Inference Worker")
    parser.add_argument(
        "--api-url",
        required=False,
        default="http://127.0.0.1:8001", #"https://inference.obobo.net", #"http://127.0.0.1:8001",
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

    args = parser.parse_args()

    print(
        f"(ง •̀_•́)ง Starting worker with WORKER_ID {args.worker_id} and COMFYUI_SERVER {args.comfyui_server} and getting batches from API: {args.api_url}"
    )

    worker = Worker(
        api_url=args.api_url, worker_id=args.worker_id, batch=args.batch, comfyui_server=args.comfyui_server,
    )

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.unregister()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    main()
