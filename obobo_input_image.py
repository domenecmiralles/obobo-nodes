from .obobo_input_media import OboboInputMedia

class OboboInputImage(OboboInputMedia):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_path": ("STRING", {
                    "default": "",
                    "placeholder": "Path to image file",
                    "tooltip": "Full path to the image file or relative path from ComfyUI root"
                }),
                "name": ("STRING", {
                    "default": "Image",
                    "placeholder": "Optional custom name",
                    "tooltip": "Custom name to identify this image input"
                }),
            }
        }

    RETURN_TYPES = OboboInputMedia.RETURN_TYPES
    RETURN_NAMES = OboboInputMedia.RETURN_NAMES
    OUTPUT_IS_LIST = OboboInputMedia.OUTPUT_IS_LIST
    FUNCTION = "process_image"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Specify an image file path for Obobo workflows"

    def process_image(self, image_path, name):
        return self.process_media(image_path, name)