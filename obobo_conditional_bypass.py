import logging
from .obobo_utils import AlwaysEqualProxy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OboboConditionalBypass:
    """
    Simple conditional bypass node that can skip processing based on a boolean flag.
    When enabled=True, acts as a stopping point in the workflow.
    When enabled=False, allows the workflow to continue.
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "input": (AlwaysEqualProxy('*'), {
                    "tooltip": "Input value to conditionally process"
                }),
            }
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "conditional_bypass"
    CATEGORY = "obobo/control"
    DESCRIPTION = "Conditionally bypass processing based on a boolean flag"

    def conditional_bypass(self, input, enabled):
        pass
        