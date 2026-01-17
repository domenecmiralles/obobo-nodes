import os
import json
import torch
import numpy as np
from PIL import Image, ImageOps
from .obobo_base_node import OboboBaseNode
import folder_paths # Internal ComfyUI module to find image folders

class OboboLoadImageWithMetadata(OboboBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        # We use the same 'image' list logic as the standard Load Image node
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "image": (sorted(files), {"image_upload": True})
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "mask", "prompt")
    FUNCTION = "load_and_extract"
    CATEGORY = "obobo/loaders"

    def load_and_extract(self, image):
            image_path = folder_paths.get_annotated_filepath(image)
            
            # --- Part A: Standard Image Loading ---
            img = Image.open(image_path)
            img = ImageOps.exif_transpose(img) 
            image_np = np.array(img).astype(np.float32) / 255.0
            
            if image_np.shape[2] == 4: 
                mask = 1.0 - torch.from_numpy(image_np[:, :, 3])
                image_np = image_np[:, :, :3]
            else:
                mask = torch.zeros((64, 64), dtype=torch.float32)

            image_tensor = torch.from_numpy(image_np)[None,]

            # --- Part B: Metadata Investigation & Extraction ---
            prompt_text = "Prompt not found"
            
            print(f"\n{'='*50}")
            print(f"DEBUGGING METADATA FOR: {image}")
            print(f"Keys found in img.info: {list(img.info.keys())}")
            
            try:
                if 'prompt' in img.info:
                    workflow_data = json.loads(img.info['prompt'])
                    
                    # THIS PRINTS THE WHOLE JSON TO YOUR TERMINAL
                    print("FULL PROMPT METADATA:")
                    print(json.dumps(workflow_data, indent=2)) 
                    
                    # Logic to find the prompt
                    for node_id, node_data in workflow_data.items():
                        class_type = node_data.get("class_type", "")
                        inputs = node_data.get("inputs", {})
                        
                        # Look for anything that looks like a positive prompt
                        if class_type == "CLIPTextEncode":
                            title = node_data.get("_meta", {}).get("title", "").lower()
                            # If we find a node with 'text', let's grab it for now
                            if "text" in inputs:
                                current_text = inputs["text"]
                                print(f"Found CLIPTextEncode (ID {node_id}, Title '{title}'): {current_text[:50]}...")
                                
                                # Prioritize nodes labeled 'positive'
                                if "positive" in title or prompt_text == "Prompt not found":
                                    prompt_text = current_text
                else:
                    print("RESULT: No 'prompt' key found. This image might have been stripped of metadata.")
            
            except Exception as e:
                print(f"ERROR DURING SEARCH: {str(e)}")

            print(f"{'='*50}\n")

            return (image_tensor, mask, prompt_text)