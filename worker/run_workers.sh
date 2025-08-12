#!/bin/bash

# Constants and arrays
GPUS=(0)  # Default GPU, will be overridden by --gpus argument
NUM_GPUS=${#GPUS[@]}
PIDS=()
# Per-worker PID tracking
declare -A COMFYUI_PIDS
declare -A WORKER_PIDS
declare -A CLOUDFLARED_PIDS
API_URL="http://inference.obobo.net"
# "http://localhost:8001"
BASE_WORKER_ID=""
# Instance ID is now passed as the first argument from the API
INSTANCE_ID=""


# Function to terminate EC2 instance
terminate_ec2_instance() {
    local instance_id=$INSTANCE_ID
    if [ -n "$instance_id" ]; then
        echo "Terminating EC2 instance: $instance_id"
        aws ec2 terminate-instances --instance-ids "$instance_id" --region $(curl -s http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null)
        if [ $? -eq 0 ]; then
            echo "EC2 termination request sent successfully"
        else
            echo "Failed to terminate EC2 instance. Falling back to shutdown."
            sudo shutdown -h now
        fi
    else
        echo "Could not retrieve instance ID. Falling back to shutdown."
        sudo shutdown -h now
    fi
}

cleanup_all() {
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
    # Kill all cloudflared processes since all workers managed by this script are shutting down
    pkill -f "cloudflared" 2>/dev/null || true
    
    # Clean up tunnel log files
    rm -f /tmp/cloudflared_*.log 2>/dev/null || true
    
    # Clean up shutdown flag files (moved to end)
    if [ -n "$INSTANCE_ID" ]; then
        for ((i=0; i<NUM_GPUS; i++)); do
            GPU_ID=${GPUS[$i]}
            WORKER_ID="${INSTANCE_ID}_${GPU_ID}"
            rm -f "/tmp/worker_shutdown_${WORKER_ID}.flag" 2>/dev/null
        done
    fi
    
    echo "Cleanup completed."
    exit 0
}

cleanup_for_machine_shutdown() {
    echo ""
    echo "Preparing for EC2 instance termination..."
    
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
    # Kill all cloudflared processes since all workers managed by this script are shutting down
    pkill -f "cloudflared" 2>/dev/null || true
    
    # Clean up tunnel log files
    rm -f /tmp/cloudflared_*.log 2>/dev/null || true
    
    echo "Process cleanup completed. Initiating EC2 instance termination..."
}

cleanup_worker() {
    local gpu_id=$1
    local worker_id="${INSTANCE_ID}_${gpu_id}"
    echo "Cleaning up worker processes for GPU ${gpu_id} (worker ${worker_id})..."
    # Kill specific processes for this worker
    if [ -n "${COMFYUI_PIDS[$gpu_id]}" ] && kill -0 "${COMFYUI_PIDS[$gpu_id]}" 2>/dev/null; then
        kill -TERM "${COMFYUI_PIDS[$gpu_id]}" 2>/dev/null || true
        sleep 1
        kill -KILL "${COMFYUI_PIDS[$gpu_id]}" 2>/dev/null || true
    fi
    if [ -n "${WORKER_PIDS[$gpu_id]}" ] && kill -0 "${WORKER_PIDS[$gpu_id]}" 2>/dev/null; then
        kill -TERM "${WORKER_PIDS[$gpu_id]}" 2>/dev/null || true
        sleep 1
        kill -KILL "${WORKER_PIDS[$gpu_id]}" 2>/dev/null || true
    fi
    if [ -n "${CLOUDFLARED_PIDS[$gpu_id]}" ] && kill -0 "${CLOUDFLARED_PIDS[$gpu_id]}" 2>/dev/null; then
        kill -TERM "${CLOUDFLARED_PIDS[$gpu_id]}" 2>/dev/null || true
        sleep 1
        kill -KILL "${CLOUDFLARED_PIDS[$gpu_id]}" 2>/dev/null || true
    fi
    rm -f "/tmp/cloudflared_${worker_id}.log" 2>/dev/null || true
    rm -f "/tmp/worker_shutdown_${worker_id}.flag" 2>/dev/null || true
    # Unset entries to mark worker inactive
    unset COMFYUI_PIDS[$gpu_id]
    unset WORKER_PIDS[$gpu_id]
    unset CLOUDFLARED_PIDS[$gpu_id]
}

start_worker() {
    local gpu_id=$1
    local comfyui_port=$((8100 + gpu_id))
    local worker_id="${INSTANCE_ID}_${gpu_id}"
    
    echo "Starting new worker for GPU ${gpu_id} (worker ${worker_id})..."
    
    # Start ComfyUI
    cd ../../../
    CUDA_VISIBLE_DEVICES=$gpu_id python3 main.py --port $comfyui_port --lowvram --dont-upcast-attention &
    local comfyui_pid=$!
    cd - > /dev/null
    PIDS+=($comfyui_pid)
    COMFYUI_PIDS[$gpu_id]=$comfyui_pid

    # Wait for ComfyUI to start
    while ! curl -s "http://127.0.0.1:$comfyui_port" > /dev/null 2>&1; do
        echo "Waiting for ComfyUI to start on port $comfyui_port..."
        sleep 1
    done

    sleep 1

    # Create cloudflared tunnel
    echo "Creating cloudflared tunnel for port $comfyui_port..."
    cloudflared tunnel --url "http://localhost:$comfyui_port" > /tmp/cloudflared_${worker_id}.log 2>&1 &
    local cloudflared_pid=$!
    PIDS+=($cloudflared_pid)
    CLOUDFLARED_PIDS[$gpu_id]=$cloudflared_pid
    
    # Wait for tunnel URL
    echo "Waiting for cloudflared tunnel URL..."
    local tunnel_url=""
    for attempt in {1..30}; do
        if [ -f "/tmp/cloudflared_${worker_id}.log" ]; then
            tunnel_url=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' "/tmp/cloudflared_${worker_id}.log" | head -1)
            if [ -n "$tunnel_url" ]; then
                echo "Cloudflared tunnel created successfully: $tunnel_url"
                break
            fi
        fi
        sleep 1
        if [ $((attempt % 5)) -eq 0 ]; then
            echo "Still waiting for cloudflared tunnel URL... ($attempt/30)"
        fi
    done
    
    if [ -z "$tunnel_url" ]; then
        echo "Failed to get cloudflared tunnel URL after 30 seconds"
        tunnel_url=""
    fi

    sleep 1
    
    # Start the worker
    CUDA_VISIBLE_DEVICES=$gpu_id python3 main.py \
        --api-url $API_URL \
        --comfyui_server "http://127.0.0.1:$comfyui_port" \
        --worker_id $worker_id \
        --batch "{}" \
        --idle_timeout $IDLE_TIMEOUT \
        --instance_id $INSTANCE_ID \
        --tunnel_url "$tunnel_url" \
        $SHUTDOWN_MACHINE_FLAG &
    local worker_pid=$!
    PIDS+=($worker_pid)
    WORKER_PIDS[$gpu_id]=$worker_pid
    
    echo "Started replacement worker $worker_id (PID: $worker_pid) and ComfyUI instance (PID: $comfyui_pid) on GPU $gpu_id with port $comfyui_port"
    if [ -n "$tunnel_url" ]; then
        echo "  Tunnel URL: $tunnel_url"
    else
        echo "  No tunnel URL available"
    fi
}

check_worker_shutdown_flags() {
    # New behavior: only act when ALL active workers are idle.
    # We detect idleness via presence of the per-worker flag files.
    local active_workers=0
    local flagged_idle_workers=0
    for ((i=0; i<NUM_GPUS; i++)); do
        GPU_ID=${GPUS[$i]}
        WORKER_ID="${INSTANCE_ID}_${GPU_ID}"
        # Count only active workers (those that still have a worker PID entry)
        if [ -n "${WORKER_PIDS[$GPU_ID]}" ]; then
            active_workers=$((active_workers + 1))
            FLAG_FILE="/tmp/worker_shutdown_${WORKER_ID}.flag"
            if [ -f "$FLAG_FILE" ]; then
                flagged_idle_workers=$((flagged_idle_workers + 1))
            fi
        fi
    done

    if [ "$active_workers" -gt 0 ] && [ "$flagged_idle_workers" -eq "$active_workers" ]; then
        echo "All ($active_workers) workers have been idle for the timeout. Initiating coordinated shutdown."
        if [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
            cleanup_for_machine_shutdown
            echo "Terminating EC2 instance..."
            terminate_ec2_instance
            exit 0
        else
            echo "Shutting down all worker processes on this instance (no EC2 termination)."
            cleanup_all
        fi
    fi
}

# Set up signal traps for graceful shutdown
trap cleanup_all SIGINT SIGTERM

# Check if BASE_WORKER_ID is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 BASE_WORKER_ID [OPTIONS]"
    echo "  BASE_WORKER_ID: Base name for worker IDs (now serves as instance ID from API)"
    echo ""
    echo "Options:"
    echo "  --gpus GPU_LIST                 Comma-separated list of GPU IDs to use (default: 0)"
    echo "  --shutdown_machine              Enable automatic EC2 instance termination after worker idle timeout"
        echo "  --idle_timeout SECONDS          Set idle timeout in seconds (default: 300 = 5 minutes)"
    echo ""
    echo "Examples:"
    echo "  $0 ec2_20231201-143022                           # Use GPU 0, process shutdown after 5 minutes idle"
    echo "  $0 ec2_20231201-143022 --gpus 0,1,2             # Use GPUs 0,1,2"
    echo "  $0 ec2_20231201-143022 --gpus 1 --shutdown_machine   # Use GPU 1, terminate EC2 instance after 5 minutes idle"
        echo "  $0 ec2_20231201-143022 --gpus 0,1 --idle_timeout 600 # Use GPUs 0,1, process shutdown after 10 minutes"
    exit 1
fi

BASE_WORKER_ID=$1
INSTANCE_ID=$1  # The first argument is now the instance ID from the API
SHUTDOWN_MACHINE_FLAG=""
IDLE_TIMEOUT=300

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
        *)
            echo "Unknown option: $1"
            echo "Use $0 --help for usage information"
            exit 1
            ;;
    esac
done

# Validate requested GPU IDs against available GPUs
TOTAL_GPUS=$(nvidia-smi -L 2>/dev/null | wc -l | tr -d ' ')
if [ -z "$TOTAL_GPUS" ] || ! [[ "$TOTAL_GPUS" =~ ^[0-9]+$ ]]; then
    TOTAL_GPUS=1
fi
VALIDATED_GPUS=()
for gpu in "${GPUS[@]}"; do
    if [ "$gpu" -ge 0 ] && [ "$gpu" -lt "$TOTAL_GPUS" ]; then
        VALIDATED_GPUS+=("$gpu")
    else
        echo "Warning: Requested GPU id $gpu is not available on this machine (total $TOTAL_GPUS). Skipping."
    fi
done
if [ ${#VALIDATED_GPUS[@]} -eq 0 ]; then
    echo "No valid GPUs specified. Defaulting to GPU 0."
    VALIDATED_GPUS=(0)
fi
GPUS=("${VALIDATED_GPUS[@]}")
NUM_GPUS=${#GPUS[@]}

# Display configuration
echo "GPU configuration: Using ${NUM_GPUS} GPU(s): ${GPUS[*]}"
echo "Instance ID: ${INSTANCE_ID}"
WORKER_ID_LIST=""
for gpu in "${GPUS[@]}"; do
    if [ -n "$WORKER_ID_LIST" ]; then
        WORKER_ID_LIST="${WORKER_ID_LIST}, "
    fi
    WORKER_ID_LIST="${WORKER_ID_LIST}${INSTANCE_ID}_${gpu}"
done
echo "Worker IDs will be: ${WORKER_ID_LIST}"
if [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
    echo "EC2 termination enabled: Instance will be terminated after workers are idle for $(($IDLE_TIMEOUT/60)) minutes"
else
    echo "Process shutdown enabled: Workers will shutdown after idle for $(($IDLE_TIMEOUT/60)) minutes"
fi

# Check if AWS CLI is available when EC2 termination is enabled
if [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
    if ! command -v aws > /dev/null 2>&1; then
        echo "Warning: EC2 termination requires AWS CLI. Please install it: 'sudo apt install awscli' or 'pip install awscli'"
        echo "Also ensure the EC2 instance has proper IAM permissions to terminate itself."
    fi
fi

# Activate the conda environment
# source ~/miniconda3/etc/profile.d/conda.sh
# conda activate oboboenv

#activate the venv (we activate it in the api):
#source ../../../venv/bin/activate

echo "Will create ${NUM_GPUS} workers for GPUs: ${GPUS[*]}"
echo "All workers will create cloudflared tunnels for their ComfyUI instances"
if [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
    echo "Workers will auto-shutdown after $(($IDLE_TIMEOUT/60)) minutes without jobs and terminate the EC2 instance"
else
    echo "Workers will auto-shutdown after $(($IDLE_TIMEOUT/60)) minutes without jobs (processes only)"
fi

# Clean up any existing shutdown flags
for ((i=0; i<NUM_GPUS; i++)); do
    GPU_ID=${GPUS[$i]}
    # Worker ID format: INSTANCE_ID_GPU_ID (e.g., ec2_20231201-143022_0)
    WORKER_ID="${INSTANCE_ID}_${GPU_ID}"
    rm -f "/tmp/worker_shutdown_${WORKER_ID}.flag" 2>/dev/null
done

# Loop through the list of GPUs and start initial workers
for ((i=0; i<NUM_GPUS; i++)); do
    GPU_ID=${GPUS[$i]}
    start_worker "$GPU_ID"
done

echo "All workers and ComfyUI instances have been started. Press Ctrl+C to stop all processes."
echo "Monitoring for auto-shutdown signals (checking every 30 seconds)..."

# Monitor processes and check for shutdown flags
while true; do
    # First check for worker auto-shutdown flags (this takes priority)
    check_worker_shutdown_flags
    
    # Then check each worker's processes; if a worker died, clean up and restart it
    for ((i=0; i<NUM_GPUS; i++)); do
        GPU_ID=${GPUS[$i]}
        died=false
        if [ -n "${COMFYUI_PIDS[$GPU_ID]}" ] && ! kill -0 "${COMFYUI_PIDS[$GPU_ID]}" 2>/dev/null; then
            died=true
        fi
        if [ -n "${WORKER_PIDS[$GPU_ID]}" ] && ! kill -0 "${WORKER_PIDS[$GPU_ID]}" 2>/dev/null; then
            died=true
        fi
        if [ -n "${CLOUDFLARED_PIDS[$GPU_ID]}" ] && ! kill -0 "${CLOUDFLARED_PIDS[$GPU_ID]}" 2>/dev/null; then
            died=true
        fi
        if [ "$died" = true ]; then
            echo "Detected death of one or more processes for worker ${INSTANCE_ID}_${GPU_ID}. Restarting worker..."
            cleanup_worker "$GPU_ID"
            start_worker "$GPU_ID"
        fi
    done

    # If no workers remain active and shutdown_machine is enabled, terminate the instance
    remaining_active=0
    for ((i=0; i<NUM_GPUS; i++)); do
        GPU_ID=${GPUS[$i]}
        if [ -n "${WORKER_PIDS[$GPU_ID]}" ]; then
            remaining_active=$((remaining_active + 1))
        fi
    done
    if [ "$remaining_active" -eq 0 ] && [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
        echo "No active workers remain. Terminating EC2 instance."
        cleanup_for_machine_shutdown
        terminate_ec2_instance
        exit 0
    fi
    
    # Wait 30 seconds before next check
    sleep 30
done

# Safety watchdog: terminate EC2 if workers fail to register within a grace period
if [ -n "$SHUTDOWN_MACHINE_FLAG" ]; then
  (
    GRACE_SECONDS=960  # 16 minutes
    CHECK_INTERVAL=15
    ELAPSED=0
    echo "Starting registration watchdog (grace: ${GRACE_SECONDS}s)..."
    while [ $ELAPSED -lt $GRACE_SECONDS ]; do
      all_registered=true
      for ((i=0; i<NUM_GPUS; i++)); do
        GPU_ID=${GPUS[$i]}
        WORKER_ID="${INSTANCE_ID}_${GPU_ID}"
        STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/v1/worker/$WORKER_ID")
        if [ "$STATUS_CODE" != "200" ]; then
          all_registered=false
          break
        fi
      done
      if [ "$all_registered" = true ]; then
        echo "All workers registered successfully. Watchdog exiting."
        exit 0
      fi
      sleep $CHECK_INTERVAL
      ELAPSED=$((ELAPSED + CHECK_INTERVAL))
    done
    echo "Workers failed to register within ${GRACE_SECONDS}s and --shutdown_machine is enabled. Terminating EC2 instance."
    cleanup_for_machine_shutdown
    terminate_ec2_instance
  ) &
fi