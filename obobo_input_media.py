import os
import logging
from .obobo_utils import AlwaysEqualProxy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboInputMedia:
    def __init__(self):
        self.path = None
        self.name = ""
        logger.info(f"{self.__class__.__name__} node initialized")

    @staticmethod
    def process_media(path, name):
        """Return the path as a list (rows), using AlwaysEqualProxy for compatibility."""
        if isinstance(path, str):
            rows = [path.split('\n')[0]]
        else:
            rows = [str(path)]
        return (rows,)

    RETURN_TYPES = (AlwaysEqualProxy('*'),)
    RETURN_NAMES = ("media_path",)
    OUTPUT_IS_LIST = (True,)
