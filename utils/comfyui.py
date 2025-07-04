import os
import re
import json
import copy
import requests
from bson import ObjectId
from pydantic import BaseModel
from typing import Optional, Union, Dict, Any, List
import random
from PIL import Image
import cv2
from dotenv import load_dotenv

load_dotenv()


class QueuedJob(BaseModel):
    job: dict  # generation job
    workflow_prompt: dict  # workflow for comfyui
    prompt_id: str  # comfyui prompt id
    completed: bool = False  # if the job is completed
    output_path: Optional[str] = None  # output filename
    comfyui_status: Optional[str] = "queued"


def download_civitai_lora(url, loras_folder):
    def get_civitai_id(url):
        # match numbers between / and ?
        match = re.search(r"/(\d+)\?", url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid URL format")

    if not os.getenv('CIVITAI_TOKEN'):
        raise ValueError("CIVITAI_TOKEN is not set")
    url = url + f"&token={os.getenv('CIVITAI_TOKEN')}"
    lora_civitai_id = get_civitai_id(url)
    if not os.path.exists(loras_folder):
        os.makedirs(loras_folder)
    file_path = os.path.join(loras_folder, f"{lora_civitai_id}.safetensors")
    # if file exists, return the path
    if os.path.exists(file_path):
        return file_path
    response = requests.get(url, stream=True)
    with open(file_path, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)
    return file_path


def download_file(url, folder, debug=False):
    filename = url.split("/")[-1]
    file_path = f"{folder}/{filename}"
    if debug:
        return file_path
    if not os.path.exists(folder):
        os.makedirs(folder)
    if os.path.exists(file_path):
        return file_path
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return file_path
    else:
        print(f"Failed to download {url}")
        return None


def queue_prompt(workflow_json, client_id, server):
    headers = {
        "Content-Type": "application/json",
    }
    p = {"prompt": workflow_json, "client_id": client_id}
    data = json.dumps(p).encode("utf-8")
    response = requests.post(f"{server}/prompt", headers=headers, data=data)
    return response.json()


def handle_generation_error(error_message, job_id, api_url, server=None):

    # Update the job status in the database
    print(f"Updating job {job_id} status to 'failed' with error message: {error_message}")
    response = requests.post(
        f"{api_url}/v1/inference/update_generation_status_to_failed/{str(job_id)}", 
        json={"error_message": error_message}
    )
    # TODO: is this appropiate?
    if "allocation on device" in error_message.lower() and server:
        print("Unloading models and emptying memory")
        unload_models_and_empty_memory(server)


def set_random_seed_in_workflow(workflow):
    """
    For each node in the workflow, if any input key contains 'seed', set it to a random int.
    """
    for node in workflow.values():
        if "inputs" in node:
            for key in node["inputs"]:
                if "seed" in key.lower():
                    node["inputs"][key] = random.randint(0, 2**32 - 1)
                    print("set seed to: ", node["inputs"][key])
    return workflow


def process_lora_array(loras_array, node):
    """Process an array of LoRAs and add them to the node inputs.
    Currently, we only use the first LoRA in the array.
    """
    print(f"DEBUG: Processing LoRAs array: {json.dumps(loras_array, indent=2)}")

    if not loras_array or len(loras_array) == 0:
        print("DEBUG: No LoRAs to process")
        return

    # For now, we only support the first LoRA
    lora_data = loras_array[0]

    if "type" not in lora_data or lora_data["type"] != "lora":
        print(f"WARNING: Expected lora type, got: {lora_data.get('type')}")
        return

    lora_value = lora_data.get("value", {})
    if not isinstance(lora_value, dict):
        print(f"ERROR: Expected lora value to be a dict, got: {type(lora_value)}")
        return

    # Handle nested value structure if present
    if "value" in lora_value and isinstance(lora_value["value"], dict):
        lora_value = lora_value["value"]
        print(
            f"DEBUG: Using nested value structure: {json.dumps(lora_value, indent=2)}"
        )

    # Get URL and strength
    if "url" not in lora_value:
        print(
            f"ERROR: LoRA value missing 'url' field: {json.dumps(lora_value, indent=2)}"
        )
        return

    lora_url = lora_value["url"]
    lora_strength = lora_value.get("strength", 1.0)

    print(f"DEBUG: LoRA URL: {lora_url}, strength: {lora_strength}")

    # Download the LoRA file
    filepath = download_file(lora_url, "ComfyUI/models/loras/obobo")
    if not filepath:
        print(f"ERROR: Failed to download LoRA from {lora_url}")
        return

    print(f"DEBUG: Downloaded LoRA to: {filepath}")

    # Set the LoRA path and strength in the node inputs
    lora_filename = os.path.basename(filepath)
    lora_path = f"obobo/{lora_filename}"
    print(f"DEBUG: Setting lora_path to: {lora_path}")

    node["inputs"]["lora_path"] = lora_path
    node["inputs"]["lora_strength"] = lora_strength


def get_node_connected_to_node_n(workflow, node_n):
    """
    Given a workflow and a node number, return all nodes that are connected to the given node.
    """
    connects_to = {}
    for n, node in workflow.items():
        for input_k, input_v in node["inputs"].items():
            if isinstance(input_v, list):
                if input_v[0] == str(node_n):
                    if not connects_to:
                        connects_to = {
                            "n": n,
                            "node": node,
                            "connected_input_keys": [input_k],
                        }
                    else:
                        connects_to["connected_input_keys"].append(input_k)
    return connects_to


def get_next_node_n(workflow) -> str:
    """ " Return the highest node_n in a workflow +1."""
    return str(max([int(n) for n in workflow.keys()]) + 1)

def set_block_swap_args(workflow):
    """
    Set the block_swap_args for the workflow.
    """
    for node in workflow.values():
        if "WanVideoBlockSwap" in node["class_type"]:
            print("DEBUG: Setting block_swap_args for WanVideoBlockSwap to 8")
            node["inputs"]["blocks_to_swap"] = 8
            node["inputs"]["offload_img_emb"] = False
            node["inputs"]["offload_txt_emb"] = False
            node["inputs"]["use_non_blocking"] = False
            node["inputs"]["vace_blocks_to_swap"] = 0
    return workflow

def fill_workflow_obobo_inputs(
    workflow,
    workflow_inputs,
    output_file_path,
    download_workflow_path=None,
):
    """
    Fill the workflow with the inputs based on the new structure:
    {
        "prompt": {"type": "text", "value": "..."},
        "LoRAs": [{"type": "lora", "value": {"keyword": "...", "url": "...", "strength": 1}}],
        "resolution": {"type": "vector2", "value": [512, 512]}
    }
    """
    # print("DEBUG: workflow_inputs structure:", json.dumps(workflow_inputs, indent=2))
    # Initializations for the loras
    node_position_to_input_name = {2: "url", 3: "strength"}
    lora_nodes = {}
    LORA_PATH = "ComfyUI/models/loras/obobo"

    # to experiment with block swap in wan2.1
    workflow = set_block_swap_args(workflow)

    for key, node in workflow.items():
        if "OboboOutput" in node["class_type"]:
            node["inputs"]["file_path"] = output_file_path
        if "OboboInput" in node["class_type"]:
            input_name = node["inputs"]["name"]
            print(f"DEBUG: Processing OboboInput node with name '{input_name}'")

            # Special handling for LoRAs which is an array
            if node["class_type"] == "OboboInputLora" and input_name in workflow_inputs:
                # set strength to 0.0 in case there are no loras
                node["inputs"]["lora_strength"] = 0.0
                print("DEBUG: Found LoRAs input")
                lora_loader = get_node_connected_to_node_n(workflow, key)
                first_lora = True
                last_lora_node_n = lora_loader["n"]
                loras_array = workflow_inputs[input_name]
                if not isinstance(loras_array, list):
                    loras_array = [loras_array]
                for input_lora in loras_array:
                    # download lora and find the path
                    if "civitai" in input_lora["value"]["url"]:
                        filepath = download_civitai_lora(
                            input_lora["value"]["url"], LORA_PATH
                        )
                    else:
                        filepath = download_file(
                            input_lora["value"]["url"], LORA_PATH
                        )
                    lora_filename = os.path.basename(filepath)
                    lora_path = f"obobo/{lora_filename}"
                    input_lora["value"]["url"] = lora_path

                    ## now start the logic to inject th values on the nodes
                    lora_loader_node = copy.deepcopy(lora_loader["node"])
                    for input_name, input_value in lora_loader_node["inputs"].items():
                        if isinstance(input_value, list):
                            if (
                                input_value[0] == str(key)
                                and input_value[1] in node_position_to_input_name
                            ):
                                lora_loader_node["inputs"][input_name] = input_lora[
                                    "value"
                                ][node_position_to_input_name[input_value[1]]]

                    if not first_lora:
                        print(last_lora_node_n)
                        current_lora_node_n = get_next_node_n(
                            {**workflow, **lora_nodes}
                        )
                        lora_nodes[current_lora_node_n] = lora_loader_node

                        # Fix the connections of the newly last lora_loader_node
                        # The current node is the one that is connected to oboboinputlora
                        # The new node is the one that is connected to the rest of the graph
                        # thus we need to:
                        # connect the last lora node to the new node
                        print(f"Connecting {last_lora_node_n} to {current_lora_node_n}")
                        for input_k, input_v in lora_nodes[last_lora_node_n][
                            "inputs"
                        ].items():
                            if isinstance(input_v, list):
                                if input_v[0] == str(key):
                                    lora_nodes[last_lora_node_n]["inputs"][input_k] = [
                                        current_lora_node_n,
                                        input_v[1],
                                    ]
                        last_lora_node_n = current_lora_node_n
                    else:
                        lora_nodes[lora_loader["n"]] = lora_loader_node
                        first_lora = False
                        last_lora_node_n = lora_loader["n"]

            # Check if this input exists in workflow_inputs
            if input_name not in workflow_inputs:
                print(f"Missing input: {input_name}")
                continue

            input_data = workflow_inputs[input_name]
            print(
                f"DEBUG: Input data for '{input_name}':",
                json.dumps(input_data, indent=2),
            )

            try:
                input_type = input_data["type"]
                input_value = input_data["value"]
                # TODO: workaround cutre per characters que per alguna rao venen com a dict name url
                if isinstance(input_value, dict) and "value" in input_value:
                    input_value = input_value["value"]
                print(
                    f"DEBUG: Input type: {input_type}, Value type: {type(input_value)}"
                )

                if input_type == "text":
                    node["inputs"]["text"] = input_value
                    print(f"DEBUG: Set text input to: {input_value}")
                elif input_type == "number":
                    node["inputs"]["number"] = input_value
                    print(f"DEBUG: Set number input to: {input_value}")
                elif input_type == "vector2":
                    print(
                        f"DEBUG: Vector2 value: {input_value}, type: {type(input_value)}"
                    )
                    if isinstance(input_value, list) and len(input_value) >= 2:
                        node["inputs"]["x"] = input_value[0]
                        node["inputs"]["y"] = input_value[1]
                        print(
                            f"DEBUG: Set vector2 input to x={input_value[0]}, y={input_value[1]}"
                        )
                    else:
                        print(
                            f"WARNING: Expected vector2 value to be a list with at least 2 elements, got: {input_value}"
                        )
                elif input_type == "audio":
                    print(
                        f"DEBUG: Value type: {type(input_value)}, value: {input_value}"
                    )
                    if isinstance(input_value, str):
                        audio_path = download_file(
                            input_value, "ComfyUI/input/obobo/audios"
                        )
                        print(f"DEBUG: Downloaded audio to: {audio_path}")
                        if audio_path:
                            audio_path = os.path.abspath(audio_path)
                            node["inputs"]["audio_path"] = audio_path
                            print(f"DEBUG: Set audio_path to: {audio_path}")
                        else:
                            print(f"ERROR: Failed to download audio from {input_value}")
                    else:
                        print(
                            f"ERROR: Expected audio value to be a string URL, got: {type(input_value)}"
                        )
                elif input_type == "image":
                    if isinstance(input_value, str):
                        filepath = download_file(
                            input_value, "ComfyUI/input/obobo/images"
                        )
                        if filepath:
                            # Make path absolute
                            filepath = os.path.abspath(filepath)
                            print(f"DEBUG: image filepath: {filepath}")
                            node["inputs"]["image_path"] = filepath
                        else:
                            print(f"ERROR: Failed to download image from {input_value}")
                    elif (
                        isinstance(input_value, dict)
                        and "value" in input_value
                        and isinstance(input_value["value"], str)
                    ):
                        filepath = download_file(
                            input_value["value"], "ComfyUI/input/obobo/images"
                        )
                        if filepath:
                            # Make path absolute
                            filepath = os.path.abspath(filepath)
                            print(f"DEBUG: image filepath: {filepath}")
                            node["inputs"]["image_path"] = filepath
                        else:
                            print(
                                f"ERROR: Failed to download image from {input_value['value']}"
                            )
                    else:
                        print(
                            f"ERROR: Expected image value to be a string URL, got: {type(input_value)}"
                        )
                elif input_type == "video":
                    if isinstance(input_value, str):
                        video_path = download_file(
                            input_value, "ComfyUI/input/obobo/videos"
                        )
                        if video_path:
                            video_path = os.path.abspath(video_path)
                            node["inputs"]["video_path"] = video_path
                            print(f"DEBUG: Set video_path to: {video_path}")
                        else:
                            print(f"ERROR: Failed to download video from {input_value}")
                    else:
                        print(
                            f"ERROR: Expected video value to be a string URL, got: {type(input_value)}"
                        )
            except KeyError as e:
                print(f"ERROR: Missing key in input_data: {e}")
                print(
                    f"ERROR: input_data structure: {json.dumps(input_data, indent=2)}"
                )
            except Exception as e:
                print(f"ERROR: Failed to process input '{input_name}': {str(e)}")
                print(f"ERROR: input_data: {json.dumps(input_data, indent=2)}")
    # add the new nodes to the workflow
    for n, node in lora_nodes.items():
        workflow[n] = node
    # print(f"DEBUG: lora_nodes: {json.dumps(lora_nodes, indent=2)}")
    # Set random seed for any node with a 'seed' input
    workflow = set_random_seed_in_workflow(workflow)
    print(f"DEBUG: Saved modified workflow to {download_workflow_path}")
    if download_workflow_path:
        # Save the modified workflow to a file
        with open(download_workflow_path, "w") as f:
            json.dump(workflow, f, indent=2)

    return workflow


def jobs_in_comfyui_queue(server):
    response = requests.get(f"{server}/prompt")
    return response.json()["exec_info"]["queue_remaining"]
    


def queue_claimed_jobs(
    claimed_jobs,
    server,
    api_url,
) -> list[QueuedJob]:
    # convert claimed jobs into QueuedJobs
    queued_jobs = []
    

    for job in claimed_jobs:
        try:
            print(f"DEBUG: Processing job {job['_id']}")
            # get workflow
            workflow_file = download_file(job["workflow"]["link"], "tmp/workflows")
            print(f"DEBUG: Downloaded workflow to: {workflow_file}")

            with open(workflow_file, "rb") as f:
                workflow = json.load(f)

            # get inputs - use the new structure
            workflow_inputs = job["workflow_inputs"]
            print(f"DEBUG: workflow_inputs keys: {list(workflow_inputs.keys())}")

            # fill workflow with inputs
            workflow = fill_workflow_obobo_inputs(
                workflow,
                workflow_inputs,
                # this is important, do not change!
                f"{job['movie_id']}/{job['scene_id']}/{job['shot_id']}/{str(job['_id'])}",
                download_workflow_path=f"tmp/workflows/{job['_id']}.json",
            )
            if isinstance(workflow, str) and workflow.startswith("No multiple lora"):
                raise Exception(workflow)

            # queue workflow
            print(f"DEBUG: Queueing workflow to ComfyUI")
            response = queue_prompt(
                workflow,
                client_id=str(job["_id"]),
                server=server,
            )

            if "error" in response:
                print(f"DEBUG: ComfyUI returned error: {response['error']}")
                handle_generation_error(
                    response["error"]["message"], job["_id"], api_url, server
                )
                continue

            # create QueuedJob
            print(f"DEBUG: Created QueuedJob with prompt_id: {response['prompt_id']}")
            queued_jobs.append(
                QueuedJob(
                    job=job,
                    workflow_prompt=workflow,
                    prompt_id=response["prompt_id"],
                )
            )
        except Exception as e:
            print(f"DEBUG: Exception in queue_claimed_jobs: {str(e)}")
            handle_generation_error(str(e), job["_id"], api_url, server)
            # remove from claimed_jobs
            # claimed_jobs.remove(job)
    return queued_jobs


def get_comfyui_history(prompt_id, server):
    return requests.get(
        f"{server}/history/{prompt_id}",
    ).json()


def get_execution_time_from_history(job_history):
    if job_history["status"]["status_str"] != "success":
        return 0
    execution_start_ts = 0
    execution_end_ts = 0
    for m in job_history["status"]["messages"]:
        if m and m[0] == "execution_start":
            execution_start_ts = m[1]["timestamp"]
        if m and m[0] == "execution_success":
            execution_end_ts = m[1]["timestamp"]

    return (execution_end_ts - execution_start_ts) / 1000

def update_status_to_running(queued_job, api_url,server):
    try:
        queue_running_job = requests.get(f"{server}/queue").json()["queue_running"]
        if len(queue_running_job) > 0:
            queue_running_job = queue_running_job[0]
            if queue_running_job and queued_job.prompt_id == queue_running_job[1] or str(queued_job.job["_id"]) == queue_running_job[-2]["client_id"]:
                queued_job.comfyui_status = "running"
                requests.post(f"{api_url}/v1/inference/update_generation_status_to_running/{str(queued_job.job['_id'])}")
    except Exception as e:
        print(f"DEBUG: Error updating status to running for job {queued_job.job['_id']}: {e}")
        return False


def check_completed_jobs_and_get_outputs(
    queued_jobs, base_output_path, server, api_url
):
    for job in queued_jobs:
        # Check if this is the currently running job

        # Initialize inference dictionary if it doesn't exist
        if "inference" not in job.job or job.job["inference"] is None:
            job.job["inference"] = {}
            
        job_history = get_comfyui_history(job.prompt_id, server)
        # update_status_to_running(job, api_url, server)
        if job.prompt_id not in job_history:
            # print(f"Job {job.prompt_id} not found in history.")
            continue
        job_history = job_history[job.prompt_id]
        if not job_history["status"]["completed"]:
            # print(f"Job {job.prompt_id} is not completed yet.")
            if job_history["status"]["status_str"] == "error":
                print(f"Job {job.prompt_id} has error status.")
                error_message = ""
                for k, v in job_history["status"].items():
                    if k == "messages":
                        for message in v:
                            if message[0] == "execution_error":
                                error_message = message[1]["exception_message"]
            if error_message:
                handle_generation_error(
                    error_message, job.job["_id"], api_url, server
                )
                # remove from queued_jobs
                queued_jobs.remove(job)
                continue
            continue

        output_local_folder = f"{base_output_path}/{job.job['movie_id']}/{job.job['scene_id']}/{job.job['shot_id']}"
        os.makedirs(output_local_folder, exist_ok=True)

        # get all files in the folder that contain the job ID
        output_local_filenames = [
            f for f in os.listdir(output_local_folder) if str(job.job["_id"]) in f
        ]

        if not output_local_filenames:
            print(f"Job {job.prompt_id} has no output filename.")
            print(
                f"Output folder: {output_local_folder}. Contents: {os.listdir(output_local_folder)}. Job ID: {job.job['_id']}"
            )
            handle_generation_error(
                "Error during ComfyUI generation", job.job["_id"], api_url, server
            )
            # remove from queued_jobs
            print(f"Removing job {job.prompt_id} from queued_jobs")
            queued_jobs.remove(job)
            # requests.delete(f"{server}/prompt/{job.prompt_id}")
            continue

        # if one of the files has a video extension, prioritize those
        video_extensions = ["mp4", "webm", "mov", "avi", "mkv", "gif"]
        video_files = []

        for f in output_local_filenames:
            for ext in video_extensions:
                if f.endswith(ext):
                    video_files.append(f)
                    break

        if video_files:
            # If we have video files, check if any has "-audio" suffix (before extension)
            audio_video_files = []
            for f in video_files:
                name, ext = os.path.splitext(f)
                if name.endswith("-audio"):
                    audio_video_files.append(f)

            # If we found video files with audio, use those
            if audio_video_files:
                audio_video_files.sort()
                output_local_filename = audio_video_files[-1]  # Take the latest one
            else:
                # Otherwise use regular video files
                video_files.sort()
                output_local_filename = video_files[-1]
        else:
            # Fall back to original behavior if no video files found
            output_local_filenames.sort()
            output_local_filename = output_local_filenames[-1]

        job.output_path = f"{output_local_folder}/{output_local_filename}"
        job.completed = True
        job.job["inference"]["prompt_id"] = job.prompt_id
        job.job["inference"]["execution_time_in_seconds"] = (
            get_execution_time_from_history(job_history)
        )
        print(
            f"Job {job.prompt_id} with job id {str(job.job['_id'])} has output filename: {output_local_filename}"
        )
    return queued_jobs


def create_display_image(input_path, generation_type):
    """
    Given an input file path and its type (image or video),
    create a webp image for display and return its path.
    Returns None if not applicable or on error.
    """
    try:
        if generation_type == "image":
            webp_path = input_path.rsplit(".", 1)[0] + ".webp"
            with Image.open(input_path) as im:
                im.save(webp_path, "webp")
            return webp_path
        elif generation_type == "video":
            vidcap = cv2.VideoCapture(input_path)
            success, image = vidcap.read()
            vidcap.release()
            if success:
                webp_path = input_path.rsplit(".", 1)[0] + "_frame.webp"
                im = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                im.save(webp_path, "webp")
                return webp_path
    except Exception as e:
        print(f"Error creating display image: {e}")
    return None


def get_file_size_in_gigabytes(file_path):
    try:
        size_in_bytes = os.path.getsize(file_path)
        size_in_gigabytes = size_in_bytes / (1024**3)
        return size_in_gigabytes
    except Exception as e:
        print(f"Error getting file size: {e}")
        return 0


def upload_completed_jobs(
    queued_jobs,
    api_url,
    s3_prefix,
    s3_client,
    s3_bucket="obobo-media-production",
):
    extensions = {
        "image": ["png", "jpg", "jpeg"],
        "video": ["mp4", "webp", "mov", "avi", "mkv", "webm", "gif"],
        "audio": ["mp3", "wav", "flac", "aac", "ogg"],
        "text": ["txt", "json", "csv"],
    }
    for job in queued_jobs:
        if not job.completed or not job.output_path:
            continue

        print(f"DEBUG: Uploading completed job {job.job['_id']}: {job.output_path}")
            
        # Initialize inference dictionary if it doesn't exist
        if "inference" not in job.job or job.job["inference"] is None:
            job.job["inference"] = {}
            
        # make an if for every possible extension and upload to s3
        extension = job.output_path.split(".")[-1]
        filename = job.output_path.split("/")[-1]
        extension_type = None
        for extension_type in extensions.keys():
            if extension in extensions[extension_type]:
                generation_type = extension_type
                break
        if not extension_type:
            print(f"Unknown file type: {extension}")
            continue

        display_image = ""
        display_image_s3_path = ""
        # Use new create_display_image function for image/video
        if generation_type in ("image", "video"):
            display_image = create_display_image(job.output_path, generation_type)
            if display_image and os.path.exists(display_image):
                display_image_filename = display_image.split("/")[-1]
                s3_client.upload_file(
                    display_image,
                    s3_bucket,
                    f"{s3_prefix}/{job.job['movie_id']}/{display_image_filename}",
                )
                display_image_s3_path = f"https://media.obobo.net/{s3_prefix}/{job.job['movie_id']}/{display_image_filename}"
        # For audio/text, display_image remains empty

        s3_client.upload_file(
            job.output_path,
            s3_bucket,
            f"{s3_prefix}/{job.job['movie_id']}/{filename}",
        )
        s3_path = (
            f"https://media.obobo.net/{s3_prefix}/{job.job['movie_id']}/{filename}"
        )

        inference_output = {
            "type": generation_type,
            "url": s3_path,
            "display_image": display_image_s3_path,
        }
        # get the size of the file
        job.job["inference"]["output_size_in_gb"] = get_file_size_in_gigabytes(
            job.output_path
        )

        # update the job in the database with the output
        requests.post(f"{api_url}/v1/inference/update_generation_status_to_success/{str(job.job['_id'])}", json={"output": inference_output, "inference": job.job["inference"]})

        # pop from queued_jobs list
        queued_jobs.remove(job)

        # remove local file
        # os.remove(job.output_path)
    return queued_jobs


def unload_models_and_empty_memory(server: str):
    requests.post(f"{server}/free", json={"unload_models": True, "free_memory": True})
