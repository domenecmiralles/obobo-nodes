import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GPU:
    """Simple GPU info class"""
    def __init__(self, name: str, capacity_in_gb: float):
        self.name = name
        self.capacity_in_gb = capacity_in_gb
    
    def model_dump(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "capacity_in_gb": self.capacity_in_gb
        }

def get_gpu_info() -> List[GPU]:
    """Get GPU information, fallback to ComfyUI's model management if GPUtil not available"""
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        return [GPU(name=gpu.name, capacity_in_gb=gpu.memoryTotal / 1024) for gpu in gpus]
    except ImportError:
        logger.warning("GPUtil not available, attempting to use ComfyUI's model management")
        try:
            import model_management
            # Try to get GPU info from ComfyUI's model management
            if hasattr(model_management, 'get_torch_device'):
                device = model_management.get_torch_device()
                if "cuda" in str(device):
                    # Basic GPU info when GPUtil not available
                    return [GPU(name="CUDA GPU", capacity_in_gb=8.0)]
        except Exception as e:
            logger.warning(f"Could not get GPU info from ComfyUI: {e}")
        
        # Fallback to empty list
        logger.warning("No GPU information available")
        return []
    except Exception as e:
        logger.error(f"Error getting GPU info: {e}")
        return []
