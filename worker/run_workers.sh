#!/bin/bash

# example usage: ./run_workers.sh test_worker

# Hardcoded list of usable GPU IDs
GPUS=(5 6 7)  # Modify this array to set available GPUs
NUM_GPUS=${#GPUS[@]}

# Array to store background process PIDs for cleanup
PIDS=()

# Cleanup function to terminate all background processes
cleanup() {
    echo ""
    echo "Received termination signal. Cleaning up processes..."
    
    # Kill all tracked PIDs
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Terminating process $pid"
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    
    # Give processes time to terminate gracefully
    sleep 5
    
    # Force kill any remaining processes
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing process $pid"
            kill -KILL "$pid" 2>/dev/null
        fi
    done
    
    # Also kill any ComfyUI or worker processes that might still be running
    echo "Cleaning up any remaining ComfyUI and worker processes..."
    pkill -f "python main.py --port" 2>/dev/null || true
    pkill -f "python main.py --api-url" 2>/dev/null || true
    
    echo "Cleanup completed."
    exit 0
}

# Set up signal traps for graceful shutdown
trap cleanup SIGINT SIGTERM

# Check if BASE_WORKER_ID is provided
if [ $# -lt 1 ]; then
  echo "Usage: $0 BASE_WORKER_ID"
  exit 1
fi

BASE_WORKER_ID=$1

# Activate the conda environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate oboboenv

# Loop through the list of GPUs
for ((i=0; i<NUM_GPUS; i++))
do
  GPU_ID=${GPUS[$i]}
  # Assign each worker-comfyui pair to a specific GPU
  COMFYUI_PORT=$((8000 + GPU_ID))
  WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
  
  # Start ComfyUI
  echo "Starting ComfyUI on GPU $GPU_ID with port $COMFYUI_PORT"
  (
    cd ../../../ && \
    CUDA_VISIBLE_DEVICES=$GPU_ID python main.py --port $COMFYUI_PORT --lowvram --dont-upcast-attention
  ) &
  COMFYUI_PID=$!
  PIDS+=($COMFYUI_PID)

  sleep 30  # Wait for ComfyUI to start

  # Start the worker
  # --api-url http://localhost:8001 \
  (
    CUDA_VISIBLE_DEVICES=$GPU_ID python main.py \
      --api-url http://inference.obobo.net \
      --comfyui_server "http://127.0.0.1:$COMFYUI_PORT" \
      --worker_id $WORKER_ID \
      --batch "{}"
  ) &
  WORKER_PID=$!
  PIDS+=($WORKER_PID)

  echo "Started worker $WORKER_ID (PID: $WORKER_PID) and ComfyUI instance (PID: $COMFYUI_PID) on GPU $GPU_ID with port $COMFYUI_PORT"
done

echo "All workers and ComfyUI instances have been started. Press Ctrl+C to stop all processes."

# Wait for all background processes to finish
wait

echo "All workers and ComfyUI instances have finished." 