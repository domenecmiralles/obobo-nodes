import GPUtil
from pydantic import BaseModel

class GPU(BaseModel):
    name: str
    capacity_in_gb: float

def get_gpu_info():
    gpus = GPUtil.getGPUs()
    return [GPU(name=gpu.name, capacity_in_gb=gpu.memoryTotal / 1024) for gpu in gpus]
