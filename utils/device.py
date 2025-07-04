import GPUtil
from oboboready.data.models import GPU


def get_gpu_info():
    gpus = GPUtil.getGPUs()
    return [GPU(name=gpu.name, capacity_in_gb=gpu.memoryTotal / 1024) for gpu in gpus]
