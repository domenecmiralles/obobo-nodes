from .obobo_input_media import OboboInputMedia

class OboboInputVideo(OboboInputMedia):
    @classmethod
    def INPUT_TYPES(cls):
        base_inputs = cls.get_base_input_types()
        node_inputs = {
            "video_path": ("STRING", {
                "default": "",
                "placeholder": "Path to video file",
                "tooltip": "Full path to the video file or relative path from ComfyUI root"
            }),
            "name": ("STRING", {
                "default": "Video",
                "placeholder": "Optional custom name",
                "tooltip": "Custom name to identify this video input"
            }),
        }
        
        return {
            "required": {**node_inputs, **base_inputs.get("required", {})},
            "optional": base_inputs.get("optional", {})
        }

    RETURN_TYPES = OboboInputMedia.RETURN_TYPES
    RETURN_NAMES = OboboInputMedia.RETURN_NAMES
    OUTPUT_IS_LIST = OboboInputMedia.OUTPUT_IS_LIST
    FUNCTION = "process_video"
    CATEGORY = "obobo/input"
    DESCRIPTION = "Specify a video file path for Obobo workflows"

    def process_video(self, video_path, name, tooltip=""):
        self.set_tooltip(tooltip)
        return self.process_media(video_path, name, tooltip)