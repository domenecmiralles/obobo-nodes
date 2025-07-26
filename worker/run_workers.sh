#!/bin/bash

# Constants and arrays
GPUS=(0)  # Default GPU, will be overridden by --gpus argument
NUM_GPUS=${#GPUS[@]}
PIDS=()
API_URL="http://inference.obobo.net"
# "http://localhost:8001"
BASE_WORKER_ID=""

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
    
    # Also kill any ComfyUI, worker, and cloudflared processes that might still be running
    echo "Cleaning up any remaining ComfyUI, worker, and cloudflared processes..."
    pkill -f "python3 main.py --port" 2>/dev/null || true
    pkill -f "python3 main.py --api-url" 2>/dev/null || true
    pkill -f "cloudflared" 2>/dev/null || true
    
    # Clean up shutdown flag files (moved to end)
    if [ -n "$BASE_WORKER_ID" ]; then
        for ((i=0; i<NUM_GPUS; i++)); do
            GPU_ID=${GPUS[$i]}
            WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
            rm -f "/tmp/worker_shutdown_${WORKER_ID}.flag" 2>/dev/null
        done
    fi
    
    echo "Cleanup completed."
    exit 0
}

cleanup_for_machine_shutdown() {
    echo ""
    echo "Preparing for machine shutdown..."
    
    # Kill all tracked PIDs
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Terminating process $pid"
            kill -TERM "$pid" 2>/dev/null
        fi
    done
    
    # Give processes time to terminate gracefully
    sleep 3
    
    # Force kill any remaining processes
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing process $pid"
            kill -KILL "$pid" 2>/dev/null
        fi
    done
    
    # Also kill any ComfyUI, worker, and cloudflared processes that might still be running
    echo "Cleaning up any remaining ComfyUI, worker, and cloudflared processes..."
    pkill -f "python3 main.py --port" 2>/dev/null || true
    pkill -f "python3 main.py --api-url" 2>/dev/null || true
    pkill -f "cloudflared" 2>/dev/null || true
    
    echo "Process cleanup completed. Initiating machine shutdown..."
}

check_worker_shutdown_flags() {
    # Check if any worker has signaled auto-shutdown due to inactivity
    for ((i=0; i<NUM_GPUS; i++)); do
        GPU_ID=${GPUS[$i]}
        WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
        FLAG_FILE="/tmp/worker_shutdown_${WORKER_ID}.flag"
        
        if [ -f "$FLAG_FILE" ]; then
            echo "Detected auto-shutdown flag from worker $WORKER_ID"
            echo "Flag file contents: $(cat "$FLAG_FILE" 2>/dev/null)"
            
            # Parse the flag file to determine shutdown type
            FLAG_CONTENT=$(cat "$FLAG_FILE" 2>/dev/null)
            if echo "$FLAG_CONTENT" | grep -q "SHUTDOWN_MACHINE"; then
                echo "Worker has been idle for $(($IDLE_TIMEOUT/60))+ minutes. Initiating machine shutdown..."
                cleanup_for_machine_shutdown
                echo "Shutting down machine in 10 seconds..."
                # Clean up flag files before shutdown
                rm -f "/tmp/worker_shutdown_${WORKER_ID}.flag" 2>/dev/null
                sleep 10
                sudo shutdown -h now
            else
                echo "Worker has been idle for $(($IDLE_TIMEOUT/60))+ minutes. Initiating process shutdown..."
                cleanup
            fi
        fi
    done
}

# Set up signal traps for graceful shutdown
trap cleanup SIGINT SIGTERM

# Check if BASE_WORKER_ID is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 BASE_WORKER_ID [OPTIONS]"
    echo "  BASE_WORKER_ID: Base name for worker IDs"
    echo ""
    echo "Options:"
    echo "  --gpus GPU_LIST                 Comma-separated list of GPU IDs to use (default: 0)"
    echo "  --shutdown_machine              Enable automatic machine shutdown after worker idle timeout"
    echo "  --idle_timeout SECONDS          Set idle timeout in seconds (default: 300 = 5 minutes)"
    echo "  --no_shutdown                   Disable auto-shutdown (workers run indefinitely)"
    echo ""
    echo "Examples:"
    echo "  $0 worker1                           # Use GPU 0, process shutdown after 5 minutes idle"
    echo "  $0 worker1 --gpus 0,1,2             # Use GPUs 0,1,2"
    echo "  $0 worker1 --gpus 1 --shutdown_machine   # Use GPU 1, machine shutdown after 5 minutes idle"
    echo "  $0 worker1 --gpus 0,1 --idle_timeout 600 # Use GPUs 0,1, process shutdown after 10 minutes"
    echo "  $0 worker1 --gpus 0,1,2,3 --no_shutdown  # Use all 4 GPUs, no auto-shutdown"
    exit 1
fi

BASE_WORKER_ID=$1
SHUTDOWN_MACHINE_FLAG=""
IDLE_TIMEOUT=300
NO_SHUTDOWN=false

# Parse arguments
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpus)
            GPU_LIST="$2"
            if [ -z "$GPU_LIST" ]; then
                echo "Error: --gpus requires a comma-separated list of GPU IDs"
                exit 1
            fi
            # Convert comma-separated string to array
            IFS=',' read -ra GPUS <<< "$GPU_LIST"
            # Validate GPU IDs are numbers
            for gpu in "${GPUS[@]}"; do
                if ! [[ "$gpu" =~ ^[0-9]+$ ]]; then
                    echo "Error: GPU ID '$gpu' is not a valid number"
                    exit 1
                fi
            done
            NUM_GPUS=${#GPUS[@]}
            shift 2
            ;;
        --shutdown_machine)
            SHUTDOWN_MACHINE_FLAG="--shutdown_machine"
            shift
            ;;
        --idle_timeout)
            IDLE_TIMEOUT="$2"
            if ! [[ "$IDLE_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$IDLE_TIMEOUT" -lt 60 ]; then
                echo "Error: idle_timeout must be a number >= 60 seconds"
                exit 1
            fi
            shift 2
            ;;
        --no_shutdown)
            NO_SHUTDOWN=true
            IDLE_TIMEOUT=9999999999999999999999999999999999999999999999999999999999999999999999999  # Very large number to effectively disable
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use $0 --help for usage information"
            exit 1
            ;;
    esac
done

# Display configuration
echo "GPU configuration: Using ${NUM_GPUS} GPU(s): ${GPUS[*]}"
if [ "$NO_SHUTDOWN" = true ]; then
    echo "Auto-shutdown: DISABLED (workers will run indefinitely)"
elif [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
    echo "Machine shutdown enabled: System will shutdown after workers are idle for $(($IDLE_TIMEOUT/60)) minutes"
else
    echo "Process shutdown enabled: Workers will shutdown after idle for $(($IDLE_TIMEOUT/60)) minutes"
fi

# Check if user can sudo shutdown when machine shutdown is enabled
if [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
    if ! sudo -n shutdown --help > /dev/null 2>&1; then
        echo "Warning: Machine shutdown requires sudo permissions. You may be prompted for password during shutdown."
        echo "To avoid prompts, add this line to /etc/sudoers (using 'sudo visudo'):"
        echo "$USER ALL=(ALL) NOPASSWD: /sbin/shutdown"
    fi
fi

# Activate the conda environment
# source ~/miniconda3/etc/profile.d/conda.sh
# conda activate oboboenv

#activate the venv:
source ../../../venv/bin/activate

echo "Will create ${NUM_GPUS} workers for GPUs: ${GPUS[*]}"
echo "First worker will check for tunnel creation"
if [ "$NO_SHUTDOWN" = true ]; then
    echo "Workers will run indefinitely (no auto-shutdown)"
elif [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
    echo "Workers will auto-shutdown after $(($IDLE_TIMEOUT/60)) minutes without jobs and shutdown the machine"
else
    echo "Workers will auto-shutdown after $(($IDLE_TIMEOUT/60)) minutes without jobs (processes only)"
fi

# Clean up any existing shutdown flags
for ((i=0; i<NUM_GPUS; i++)); do
    GPU_ID=${GPUS[$i]}
    WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
    rm -f "/tmp/worker_shutdown_${WORKER_ID}.flag" 2>/dev/null
done

# Loop through the list of GPUs
for ((i=0; i<NUM_GPUS; i++)); do
    GPU_ID=${GPUS[$i]}
    COMFYUI_PORT=$((8100 + GPU_ID))
    WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
    
    # Start ComfyUI
    cd ../../../
    CUDA_VISIBLE_DEVICES=$GPU_ID python3 main.py --port $COMFYUI_PORT --lowvram --dont-upcast-attention &
    COMFYUI_PID=$!
    cd - > /dev/null
    PIDS+=($COMFYUI_PID)
    sleep 30
    
    # Prepare tunnel argument for first worker only
    TUNNEL_ARG=""
    if [ $i -eq 0 ]; then
        TUNNEL_ARG="--create_tunnel"
    fi
    
    # Start the worker
    CUDA_VISIBLE_DEVICES=$GPU_ID python3 main.py \
        --api-url $API_URL \
        --comfyui_server "http://127.0.0.1:$COMFYUI_PORT" \
        --worker_id $WORKER_ID \
        --batch "{}" \
        --idle_timeout $IDLE_TIMEOUT \
        $TUNNEL_ARG \
        $SHUTDOWN_MACHINE_FLAG &
    WORKER_PID=$!
    PIDS+=($WORKER_PID)
    
    if [ $i -eq 0 ]; then
        echo "Started worker $WORKER_ID (PID: $WORKER_PID) and ComfyUI instance (PID: $COMFYUI_PID) on GPU $GPU_ID with port $COMFYUI_PORT (will check for tunnel creation)"
    else
        echo "Started worker $WORKER_ID (PID: $WORKER_PID) and ComfyUI instance (PID: $COMFYUI_PID) on GPU $GPU_ID with port $COMFYUI_PORT"
    fi
done

echo "All workers and ComfyUI instances have been started. Press Ctrl+C to stop all processes."
echo "Monitoring for auto-shutdown signals (checking every 30 seconds)..."

# Monitor processes and check for shutdown flags
while true; do
    # First check for worker auto-shutdown flags (this takes priority)
    check_worker_shutdown_flags
    
    # Then check if any processes have died
    any_process_dead=false
    for pid in "${PIDS[@]}"; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "Process $pid has died"
            any_process_dead=true
        fi
    done
    
    # If any process died, check for shutdown flags immediately before cleanup
    if [ "$any_process_dead" = true ]; then
        echo "One or more processes have died. Checking for shutdown flags..."
        
        # Give a moment for any flag files to be written
        sleep 2
        
        # Debug: List all shutdown flag files
        echo "Checking for shutdown flags in /tmp/:"
        ls -la /tmp/worker_shutdown_*.flag 2>/dev/null || echo "No shutdown flag files found"
        
        # Check for shutdown flags one more time
        machine_shutdown_requested=false
        for ((i=0; i<NUM_GPUS; i++)); do
            GPU_ID=${GPUS[$i]}
            WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
            FLAG_FILE="/tmp/worker_shutdown_${WORKER_ID}.flag"
            
            echo "Checking flag file: $FLAG_FILE"
            if [ -f "$FLAG_FILE" ]; then
                echo "Found shutdown flag after process death: $WORKER_ID"
                echo "Flag file contents: $(cat "$FLAG_FILE" 2>/dev/null)"
                
                # Parse the flag file to determine shutdown type
                FLAG_CONTENT=$(cat "$FLAG_FILE" 2>/dev/null)
                if echo "$FLAG_CONTENT" | grep -q "SHUTDOWN_MACHINE"; then
                    echo "Process death was due to auto-shutdown. Initiating machine shutdown..."
                    machine_shutdown_requested=true
                    break
                fi
            else
                echo "Flag file $FLAG_FILE does not exist"
            fi
        done
        
        # Handle machine shutdown if requested
        if [ "$machine_shutdown_requested" = true ]; then
            cleanup_for_machine_shutdown
            echo "Shutting down machine in 10 seconds..."
            # Clean up all flag files before shutdown
            if [ -n "$BASE_WORKER_ID" ]; then
                for ((i=0; i<NUM_GPUS; i++)); do
                    GPU_ID=${GPUS[$i]}
                    WORKER_ID="${BASE_WORKER_ID}_${GPU_ID}"
                    rm -f "/tmp/worker_shutdown_${WORKER_ID}.flag" 2>/dev/null
                done
            fi
            sleep 10
            sudo shutdown -h now
            exit 0
        fi
        
        echo "No shutdown flags found. Process died unexpectedly. Cleaning up..."
        cleanup
    fi
    
    # Wait 30 seconds before next check
    sleep 30
done