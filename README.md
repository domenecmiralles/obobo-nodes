# Obobo Nodes for ComfyUI

## Overview

Obobo nodes are a collection of simple placeholder nodes for ComfyUI that define inputs for the Obobo content generation system. These nodes act as bridges between ComfyUI workflows and the Obobo application, allowing users to specify where inputs should appear in their Obobo workflows.

## How It Works

When you load a ComfyUI workflow into the Obobo application, the system automatically detects these obobo nodes and creates corresponding input fields in the Obobo interface. This allows users to:

1. **Design workflows in ComfyUI** with obobo nodes as placeholders
2. **Load the workflow into Obobo** where the nodes are automatically converted to input fields
3. **Fill in the inputs in Obobo** without needing to modify the ComfyUI workflow

## Node Types

### Input Nodes

All input nodes are located in the `obobo/input` category in ComfyUI and include:

#### Text Input (`OboboInputText`)
- **Purpose**: Creates a text input field in Obobo
- **ComfyUI Inputs**: 
  - `text`: The text content (multiline supported)
  - `name`: Custom name for the input (default: "Prompt")
  - `tooltip`: Optional documentation text
- **Output**: String value that can be connected to other ComfyUI nodes

#### Number Input (`OboboInputNumber`)
- **Purpose**: Creates a numeric input field in Obobo
- **ComfyUI Inputs**:
  - `number`: Numeric value (float, range: -1,000,000 to 1,000,000)
  - `name`: Custom name for the input (default: "Duration")
  - `tooltip`: Optional documentation text
- **Output**: Both float and integer values for flexibility

#### Vector2 Input (`OboboInputVector2`)
- **Purpose**: Creates a 2D vector input (width × height) in Obobo
- **ComfyUI Inputs**:
  - `x`: Width component (0-8192, default: 1024)
  - `y`: Height component (0-8192, default: 1024)
  - `name`: Custom name for the input (default: "Resolution")
  - `tooltip`: Optional documentation text
- **Output**: Two integer values (x, y) for width and height

#### Image Input (`OboboInputImage`)
- **Purpose**: Creates an image file input field in Obobo
- **ComfyUI Inputs**:
  - `image_path`: Path to the image file
  - `name`: Custom name for the input (default: "Image")
  - `tooltip`: Optional documentation text
- **Output**: File path as a list for ComfyUI compatibility

#### Video Input (`OboboInputVideo`)
- **Purpose**: Creates a video file input field in Obobo
- **ComfyUI Inputs**:
  - `video_path`: Path to the video file
  - `name`: Custom name for the input (default: "Video")
  - `tooltip`: Optional documentation text
- **Output**: File path as a list for ComfyUI compatibility

#### Audio Input (`OboboInputAudio`)
- **Purpose**: Creates an audio file input field in Obobo
- **ComfyUI Inputs**:
  - `audio_path`: Path to the audio file
  - `name`: Custom name for the input (default: "Audio")
  - `tooltip`: Optional documentation text
- **Output**: File path as a list for ComfyUI compatibility

#### LoRA Input (`OboboInputLora`)
- **Purpose**: Creates a LoRA (Low-Rank Adaptation) input field in Obobo
- **ComfyUI Inputs**:
  - `lora_path`: LoRA file path or identifier
  - `lora_strength`: LoRA strength value (-10.0 to 10.0, default: 0.0)
  - `name`: Custom name for the input (default: "LoRA")
  - `tooltip`: Optional documentation text
  - `prev_model`: Optional model connection
  - `clip`: Optional CLIP model connection
- **Output**: Model, CLIP, LoRA path, and strength values

### Control Nodes

Control nodes are located in the `obobo/control` category and provide workflow control functionality:

#### Conditional Bypass (`OboboConditionalBypass`)
- **Purpose**: Conditionally skip or pass through inputs based on a boolean flag
- **ComfyUI Inputs**:
  - `input`: Any type of input to conditionally process
  - `enabled`: Boolean toggle (True = skip, False = pass through, default: False)
  - `name`: Custom name for the node (default: "Conditional Bypass")
  - `tooltip`: Optional documentation text
- **Output**: Either the input value (when enabled=False) or None (when enabled=True)
- **Use Cases**: 
  - Skip processing based on validation logic
  - Conditional workflow branches
  - Dynamic workflow control from UI flags

### Output Node

#### Output (`OboboOutput`)
- **Purpose**: Specifies where the workflow output should be saved
- **ComfyUI Inputs**:
  - `file_path`: Path where the output should be saved
  - `name`: Custom name for the output (default: "Output")
  - `tooltip`: Optional documentation text
- **Output**: Output file path
- **Category**: `obobo/output`

## Usage Instructions

### 1. Installing the Nodes

1. Copy the `obobo_nodes` folder to your ComfyUI `custom_nodes` directory
2. Restart ComfyUI
3. The nodes will appear in the node menu under `obobo/input`, `obobo/control`, and `obobo/output` categories

### 2. Creating a Workflow

1. **Add obobo input nodes** where you want inputs to appear in Obobo
2. **Add control nodes** for conditional processing if needed
3. **Connect them to your existing ComfyUI nodes** as needed
4. **Add an obobo output node** to specify where results should be saved
5. **Save your workflow** as a JSON file

### 3. Using in Obobo

1. **Load your workflow** into the Obobo application
2. **Input fields will automatically appear** based on the obobo nodes in your workflow
3. **Fill in the values** in the Obobo interface
4. **Run the generation** - Obobo will use your inputs with the ComfyUI workflow

## Node Features

### Common Features
- **Tooltip Support**: All nodes support optional tooltip text for documentation
- **Custom Names**: Each node can have a custom name to identify it in Obobo
- **Logging**: Comprehensive logging for debugging and monitoring
- **Error Handling**: Robust error handling with informative messages

### Technical Details
- **Base Class**: All nodes inherit from `OboboBaseNode` for consistent functionality
- **ComfyUI Compatibility**: Uses standard ComfyUI node patterns and conventions
- **Type Safety**: Proper type definitions for all inputs and outputs
- **Flexible Outputs**: Some nodes provide multiple output types for maximum compatibility

## Example Workflows

### Basic Input Workflow
A typical workflow might include:
1. `OboboInputText` → Text generation node
2. `OboboInputNumber` → Duration/parameter control
3. `OboboInputImage` → Reference image for generation
4. `OboboInputVector2` → Resolution settings
5. `OboboOutput` → Specify output location

### Conditional Processing Workflow
For more complex workflows with conditional logic:
1. `OboboInputText` → `OboboConditionalBypass` → Text generation node
2. `OboboInputImage` → `OboboConditionalBypass` → Image processing node
3. `OboboInputNumber` → Control the bypass conditions
4. `OboboOutput` → Specify output location

## Troubleshooting

### Common Issues
- **Nodes not appearing**: Ensure the folder is in the correct `custom_nodes` directory
- **Connection errors**: Check that input/output types match between nodes
- **Path issues**: Use absolute paths or paths relative to ComfyUI root directory
- **Conditional bypass not working**: Ensure downstream nodes can handle None inputs gracefully

### Logging
All nodes include detailed logging. Check the ComfyUI console for:
- Node initialization messages
- Input processing information
- Error details if something goes wrong

## Requirements

The nodes have minimal dependencies and should work with any standard ComfyUI installation. See `requirements.txt` for specific version requirements.

## Development

These nodes are designed to be simple and maintainable:
- Clear inheritance structure with `OboboBaseNode`
- Consistent naming conventions
- Comprehensive documentation and logging
- Modular design for easy extension

For developers wanting to add new node types, simply inherit from `OboboBaseNode` and follow the established patterns.
