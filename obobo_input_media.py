import os
import logging
from .obobo_utils import AlwaysEqualProxy
from .obobo_base_node import OboboBaseNode

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputMedia(OboboBaseNode):
    def __init__(self):
        super().__init__()
        self.path = None
        self.name = ""
        logger.info(f"{self.__class__.__name__} node initialized")

    @staticmethod
    def process_media(path, name, tooltip=""):
        """Return the path as a list (rows), using AlwaysEqualProxy for compatibility."""
        if isinstance(path, str):
            rows = [path.split('\n')[0]]
        else:
            rows = [str(path)]
        return (rows,)

    RETURN_TYPES = (AlwaysEqualProxy('*'),)
    RETURN_NAMES = ("media_path",)
    OUTPUT_IS_LIST = (True,)
