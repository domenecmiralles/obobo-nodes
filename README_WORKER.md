# Obobo Worker Manager for ComfyUI

This extension integrates Obobo's inference worker system directly into ComfyUI, allowing you to run a worker node that processes Obobo generation jobs using your local ComfyUI instance.

## Features

- **🎬 One-Click Worker Setup**: Start/stop Obobo workers directly from ComfyUI's interface
- **🔗 Worker Dashboard Link**: Get instant access to your worker's status on obobo.net
- **🔄 Automatic Job Processing**: Seamlessly processes Obobo generation batches using your ComfyUI workflows
- **⚡ GPU Detection**: Automatically detects and registers your GPU configuration
- **📊 Real-time Status**: Monitor worker status and activity

## How It Works

1. **Click the 🎬 Obobo Worker button** in the top-right corner of ComfyUI
2. **Start Worker** - The system will:
   - Generate a unique secret ID for your worker
   - Register your GPU configuration with Obobo's infrastructure
   - Start processing jobs from the Obobo queue
   - Provide you with a dashboard link: `https://obobo.net/start_worker/{secret_id}`
3. **Monitor Progress** - Use the dashboard link to track your worker's performance
4. **Stop Worker** when you're done to free up resources

## Worker Process

The worker integrates with Obobo's batch processing system:

- **Batch Retrieval**: Fetches generation jobs from the Obobo API
- **Workflow Processing**: Downloads and processes workflows using your local ComfyUI
- **Asset Management**: Handles input downloads (images, videos, audio, LoRAs)
- **Output Upload**: Automatically uploads results to Obobo's media storage
- **Status Updates**: Reports progress back to the Obobo system

## Technical Details

### Files Structure
```
obobo_nodes/
├── js/
│   └── obobo-worker-manager.js    # ComfyUI frontend extension
├── utils/
│   ├── main.py                    # Worker implementation
│   ├── comfyui.py                 # ComfyUI integration utilities
│   ├── database.py                # S3 and database utilities
│   └── device.py                  # GPU detection
├── obobo_worker_api.py            # API endpoints for worker control
└── __init__.py                    # ComfyUI node registration
```

### API Endpoints
- `POST /obobo/start_worker` - Start the worker
- `POST /obobo/stop_worker` - Stop the worker  
- `GET /obobo/worker_status` - Get worker status

### Worker ID Format
Workers are automatically assigned IDs in the format: `comfyui-{secret_id}`

## Requirements

- ComfyUI with the Obobo nodes installed
- Internet connection for API communication
- GPU with sufficient VRAM for your target workflows
- Python dependencies: `requests`, `boto3`, `pillow`, `opencv-python`

## Troubleshooting

### Worker Won't Start
- Check ComfyUI console for error messages
- Ensure internet connectivity to `inference.obobo.net`
- Verify GPU drivers are properly installed
- **Timeout Error**: If you get "ComfyUI server connection timed out", this usually means ComfyUI is busy processing. Wait a moment and try again.

### No Jobs Appearing
- Workers are assigned jobs based on GPU capacity and availability
- Higher-tier users get priority in the job queue
- Jobs are batched for efficiency (6-10 generations per batch)

### Connection Issues
- The worker automatically retries failed connections
- Check firewall settings if persistent connection issues occur
- Worker will attempt to re-register if connection is lost

## Development

To test the worker locally:

```bash
cd utils/
python main.py --api-url https://inference.obobo.net --action start
```

For development with local API:
```bash
python main.py --api-url http://localhost:8001 --action start
```

## Support

For issues or questions:
- Check the ComfyUI console logs for detailed error messages
- Report bugs through the Obobo platform
- Worker activity can be monitored via the dashboard link provided when starting

---

**Note**: This worker system is designed to integrate seamlessly with Obobo's distributed rendering infrastructure. Your local ComfyUI instance becomes part of a larger network of workers processing creative content generation jobs. 