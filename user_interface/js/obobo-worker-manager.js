import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("🎬 Obobo Worker Manager extension loading...");

class OboboWorkerManager {
    constructor() {
        // Check for auto-load workflow parameter
        this.checkAutoLoadWorkflow();
        
        // Check for canvas-only mode
        this.checkCanvasOnlyMode();
        
        // Setup drag and drop for canvas
        this.setupCanvasDragAndDrop();
    }
    

    async loadWorkflowFromUrl(workflowUrl) {
        // Fetch and load the workflow
        const workflowResponse = await fetch(workflowUrl);
        if (!workflowResponse.ok) {
            throw new Error(`Failed to fetch workflow: ${workflowResponse.statusText}`);
        }
        
        const workflow = await workflowResponse.json();
        app.loadGraphData(workflow);
        
        // Hide spinner if it's showing (for auto-load case)
        this.hideAutoLoadSpinner();
        
        app.extensionManager.toast.add({
            severity: "success",
            summary: "🎬 Workflow Loaded",
            detail: "Successfully loaded current workflow",
            life: 3000
        });
    }

    async saveWorkflow() {
        try {
            // Get workflow context from URL parameters
            const urlParams = new URLSearchParams(window.location.search);
            const workflowNodeId = urlParams.get('workflow_node_id');
            const movieId = urlParams.get('movie_id');
            
            if (!workflowNodeId || !movieId) {
                throw new Error("Missing workflow context. This ComfyUI instance wasn't opened from a workflow node.");
            }
            
            // Get the current ComfyUI graph
            const workflow = app.graph.serialize();
            
            console.log("🎬 Saving workflows (normal + API) to S3...");
            
            // Show loading spinner
            this.showSaveSpinner();
            
            app.extensionManager.toast.add({
                severity: "info",
                summary: "🎬 Saving Workflows",
                detail: "Converting and uploading workflows to S3...",
                life: 3000
            });

            // Get both normal workflow and API workflow
            const apiData = await app.graphToPrompt(workflow, true);
            const apiWorkflow = apiData.output;
            
            // Send both workflows to backend for S3 upload
            const response = await api.fetchApi("/obobo/save_workflow", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    workflow: {
                        nonapi: workflow,
                        api: apiWorkflow
                    },
                    workflow_node_id: workflowNodeId,
                    movie_id: movieId
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log("🎬 Workflows saved successfully to S3");
                
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "🎬 Workflows Saved",
                    detail: "Successfully saved both normal and API workflows to S3",
                    life: 3000
                });
            } else {
                throw new Error(result.message || "Failed to save workflows");
            }
            
        } catch (error) {
            console.error("🎬 Failed to save workflows:", error);
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Save Failed",
                detail: `Failed to save workflows: ${error.message}`,
                life: 5000
            });
        } finally {
            // Always hide the spinner
            this.hideSaveSpinner();
        }
    }

    showSaveSpinner() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'obobo-save-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        // Create spinner
        const spinner = document.createElement('div');
        spinner.style.cssText = `
            width: 50px;
            height: 50px;
            border: 4px solid #333;
            border-top: 4px solid #FF9800;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        `;
        
        // Create loading text
        const loadingText = document.createElement('div');
        loadingText.textContent = '🎬 Saving workflows to S3...';
        loadingText.style.cssText = `
            color: white;
            font-size: 18px;
            font-weight: 500;
            text-align: center;
        `;
        
        // Create subtitle
        const subtitle = document.createElement('div');
        subtitle.textContent = 'Please wait while we upload your workflows';
        subtitle.style.cssText = `
            color: #ccc;
            font-size: 14px;
            text-align: center;
            margin-top: 8px;
        `;
        
        // Add spinner animation CSS if not already present
        if (!document.getElementById('obobo-spinner-styles')) {
            const style = document.createElement('style');
            style.id = 'obobo-spinner-styles';
            style.textContent = `
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
        
        overlay.appendChild(spinner);
        overlay.appendChild(loadingText);
        overlay.appendChild(subtitle);
        document.body.appendChild(overlay);
    }
    
    hideSaveSpinner() {
        const overlay = document.getElementById('obobo-save-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    checkAutoLoadWorkflow() {
        // Check URL parameters for auto-load workflow
        const urlParams = new URLSearchParams(window.location.search);
        const autoLoad = urlParams.get('auto_load_workflow');
        const workflowUrl = urlParams.get('workflow_url');
        
        if (autoLoad === 'true' && workflowUrl) {
            console.log("🎬 Auto-loading workflow from URL parameter:", workflowUrl);
            
            // Show loading spinner
            this.showAutoLoadSpinner();
            
            // Wait a bit for ComfyUI to fully load, then load the workflow
            setTimeout(() => {
                this.autoLoadWorkflowFromUrl(workflowUrl);
            }, 2000);
        }
    }
    
    showAutoLoadSpinner() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'obobo-autoload-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        // Create spinner
        const spinner = document.createElement('div');
        spinner.style.cssText = `
            width: 50px;
            height: 50px;
            border: 4px solid #333;
            border-top: 4px solid #4CAF50;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        `;
        
        // Create loading text
        const loadingText = document.createElement('div');
        loadingText.textContent = '🎬 Loading workflow from webapp...';
        loadingText.style.cssText = `
            color: white;
            font-size: 18px;
            font-weight: 500;
            text-align: center;
        `;
        
        // Create subtitle
        const subtitle = document.createElement('div');
        subtitle.textContent = 'Please wait while we prepare your workflow';
        subtitle.style.cssText = `
            color: #ccc;
            font-size: 14px;
            text-align: center;
            margin-top: 8px;
        `;
        
        // Add spinner animation CSS
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        overlay.appendChild(spinner);
        overlay.appendChild(loadingText);
        overlay.appendChild(subtitle);
        document.body.appendChild(overlay);
    }
    
    hideAutoLoadSpinner() {
        const overlay = document.getElementById('obobo-autoload-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    async autoLoadWorkflowFromUrl(workflowUrl) {
        try {
            console.log("🎬 Fetching workflow from:", workflowUrl);
            
            // Use the shared loading logic
            await this.loadWorkflowFromUrl(workflowUrl);
            
            console.log("🎬 Auto-loaded workflow successfully");
            
        } catch (error) {
            console.error("🎬 Failed to auto-load workflow:", error);
            
            // Show error toast
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Auto-Load Failed",
                detail: `Failed to load workflow: ${error.message}`,
                life: 5000
            });
        } finally {
            // Always hide the spinner, whether success or failure
            this.hideAutoLoadSpinner();
        }
    }

    checkCanvasOnlyMode() {
        const urlParams = new URLSearchParams(window.location.search);
        const canvasOnly = urlParams.get('canvas_only');
        
        if (canvasOnly === 'true') {
            console.log("🎬 Canvas-only mode detected, hiding UI elements...");
            
            // Wait for DOM to be ready
            setTimeout(() => {
                this.enableCanvasOnlyMode();
            }, 1000);
        }
    }
    
    
    enableCanvasOnlyMode() {
        // Hide the main UI sections based on actual ComfyUI structure
        const elementsToHide = [
            '#comfyui-body-top',      // Top menu bar
            '#comfyui-body-bottom',   // Bottom panel
            '#comfyui-body-left',     // Left sidebar
            '#comfyui-body-right',    // Right sidebar
        ];
        
        elementsToHide.forEach(selector => {
            const element = document.querySelector(selector);
            if (element) {
                element.style.display = 'none';
                console.log('🎬 Hidden element:', selector);
            }
        });
        
        // Find and hide any splitter panels except the main graph canvas
        const splitters = document.querySelectorAll('.p-splitter');
        splitters.forEach(splitter => {
            if (!splitter.closest('#graph-canvas-container')) {
                splitter.style.display = 'none';
            }
        });
        
        // Hide sidebar panels within the graph container
        const sidePanels = document.querySelectorAll('.side-bar-panel, .bottom-panel');
        sidePanels.forEach(panel => {
            panel.style.display = 'none';
        });
        
        // Hide splitter gutters (resize handles)
        const gutters = document.querySelectorAll('.p-splitter-gutter');
        gutters.forEach(gutter => {
            gutter.style.display = 'none';
        });
        
        // Hide workflow tabs and controls above the canvas
        const workflowTabs = document.querySelector('.workflow-tabs-container');
        if (workflowTabs) {
            workflowTabs.style.display = 'none';
        }
        
        // Hide zoom controls
        const zoomControls = document.querySelector('.p-buttongroup-vertical');
        if (zoomControls) {
            zoomControls.style.display = 'none';
        }
        
        // Make the main comfyui body container full screen
        const comfyuiBody = document.querySelector('.comfyui-body');
        if (comfyuiBody) {
            comfyuiBody.style.position = 'fixed';
            comfyuiBody.style.top = '0';
            comfyuiBody.style.left = '0';
            comfyuiBody.style.width = '100vw';
            comfyuiBody.style.height = '100vh';
            comfyuiBody.style.zIndex = '1000';
        }
        
        // Make sure the graph canvas container takes full available space (accounting for left sidebar)
        const graphContainer = document.getElementById('graph-canvas-container');
        if (graphContainer) {
            graphContainer.style.position = 'fixed';
            graphContainer.style.top = '0';
            graphContainer.style.left = '80px'; // Leave space for left sidebar
            graphContainer.style.width = 'calc(100vw - 80px)';
            graphContainer.style.height = '100vh';
            graphContainer.style.zIndex = '1001';
        }
        
        // Make the canvas itself full size (accounting for left sidebar)
        const canvas = document.getElementById('graph-canvas');
        if (canvas) {
            canvas.style.width = 'calc(100vw - 80px)';
            canvas.style.height = '100vh';
        }
        
        // Hide document body's default styling
        document.body.style.margin = '0';
        document.body.style.padding = '0';
        document.body.style.overflow = 'hidden';
        
        // Set page title
        document.title = 'ComfyUI - Canvas Only';
        
        // Add minimal node spawning interface for canvas-only mode
        this.createCanvasOnlyNodePanel();
        
        console.log('🎬 Canvas-only mode enabled successfully');
    }
    
    openCanvasOnlyView() {
        // Get current URL and add canvas_only parameter
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('canvas_only', 'true');
        
        // Open in new tab
        window.open(currentUrl.toString(), '_blank', 'width=1200,height=800');
        
        app.extensionManager.toast.add({
            severity: "info",
            summary: "🎬 Canvas View",
            detail: "Opening canvas-only view in new tab",
            life: 3000
        });
    }
    
    openCanvasIframeView() {
        // Get base URL for the iframe version
        const baseUrl = window.location.origin + window.location.pathname.replace(/\/[^\/]*$/, '');
        const iframeUrl = `${baseUrl}/custom_nodes/obobo_nodes/worker/canvas-only.html`;
        
        // Open in new tab
        window.open(iframeUrl, '_blank', 'width=1200,height=800');
        
        app.extensionManager.toast.add({
            severity: "info",
            summary: "🎬 Canvas iFrame View",
            detail: "Opening canvas-only iframe view in new tab",
            life: 3000
        });
    }



    spawnNode(nodeClass, displayName) {
        try {
            // Get the center of the current view for node placement
            const canvas = app.canvas || app.canvasManager?.canvas;
            if (!canvas) {
                throw new Error("Canvas not available");
            }
            
            const canvasEl = canvas.canvas || canvas;
            const [centerX, centerY] = canvas.convertOffsetToCanvas ? 
                canvas.convertOffsetToCanvas([canvasEl.width / 2, canvasEl.height / 2]) :
                [canvasEl.width / 2, canvasEl.height / 2];
            
            // Add some randomness to avoid nodes spawning on top of each other
            const offsetX = (Math.random() - 0.5) * 200;
            const offsetY = (Math.random() - 0.5) * 200;
            
            // Create the node using the correct ComfyUI/LiteGraph API
            let node = null;
            
            // Try different methods to create the node
            if (typeof LiteGraph !== 'undefined' && LiteGraph.createNode) {
                node = LiteGraph.createNode(nodeClass);
            } else if (app.graph && app.graph.createNode) {
                node = app.graph.createNode(nodeClass);
            } else if (window.LiteGraph && window.LiteGraph.createNode) {
                node = window.LiteGraph.createNode(nodeClass);
            } else {
                throw new Error("No suitable node creation method found");
            }
            
            if (!node) {
                throw new Error(`Failed to create node of type: ${nodeClass}. Make sure the node is registered.`);
            }
            
            // Position the node at the center of the view with slight randomization
            node.pos = [centerX + offsetX, centerY + offsetY];
            
            // Add the node to the graph
            app.graph.add(node);
            
            // Refresh the graph display
            if (app.graph.setDirtyCanvas) {
                app.graph.setDirtyCanvas(true, true);
            }
            
            // Show success message
            app.extensionManager.toast.add({
                severity: "success",
                summary: "🎭 Node Added",
                detail: `${displayName} node spawned successfully`,
                life: 2000
            });
            
            console.log(`🎬 Spawned ${nodeClass} node at position [${node.pos[0]}, ${node.pos[1]}]`);
            
        } catch (error) {
            console.error(`🎬 Failed to spawn ${nodeClass} node:`, error);
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎭 Spawn Failed",
                detail: `Failed to create ${displayName} node: ${error.message}`,
                life: 4000
            });
        }
    }

    setupCanvasDragAndDrop() {
        // Wait for the canvas to be available
        const setupDrop = () => {
            const canvas = app.canvas;
            const canvasElement = canvas?.canvas;
            
            if (!canvasElement) {
                // Retry after a short delay if canvas isn't ready
                setTimeout(setupDrop, 500);
                return;
            }
            
            console.log("🎬 Setting up canvas drag and drop");
            
            // Allow dropping on the canvas
            canvasElement.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'copy';
                
                // Add visual feedback
                canvasElement.style.filter = 'brightness(1.1)';
                canvasElement.style.transition = 'filter 0.2s';
            });
            
            canvasElement.addEventListener('dragleave', (e) => {
                // Remove visual feedback when leaving canvas
                canvasElement.style.filter = '';
            });
            
            canvasElement.addEventListener('drop', (e) => {
                e.preventDefault();
                canvasElement.style.filter = '';
                
                try {
                    const nodeData = JSON.parse(e.dataTransfer.getData('application/json'));
                    if (!nodeData.nodeClass) return;
                    
                    // Try multiple methods to get accurate coordinates
                    let graphPos;
                    
                    // Method 1: Use LiteGraph's coordinate conversion
                    if (app.graph && app.graph.convertOffsetToCanvas) {
                        const rect = canvasElement.getBoundingClientRect();
                        const offsetX = e.clientX - rect.left;
                        const offsetY = e.clientY - rect.top;
                        graphPos = app.graph.convertOffsetToCanvas(offsetX, offsetY);
                    }
                    // Method 2: Use canvas coordinate conversion  
                    else if (canvas.convertEventToCanvasOffset) {
                        graphPos = canvas.convertEventToCanvasOffset(e);
                    }
                    // Method 3: Direct LiteGraph coordinate calculation
                    else if (canvas.graph) {
                        const rect = canvasElement.getBoundingClientRect();
                        const x = e.clientX - rect.left;
                        const y = e.clientY - rect.top;
                        graphPos = canvas.graph.convertCanvasToOffset ? 
                            canvas.graph.convertCanvasToOffset(x, y) :
                            [x / canvas.ds.scale - canvas.ds.offset[0] / canvas.ds.scale, 
                             y / canvas.ds.scale - canvas.ds.offset[1] / canvas.ds.scale];
                    }
                    // Method 4: Manual calculation
                    else {
                        const rect = canvasElement.getBoundingClientRect();
                        const clientX = e.clientX - rect.left;
                        const clientY = e.clientY - rect.top;
                        
                        const scale = app.canvas.ds?.scale || 1;
                        const offsetX = app.canvas.ds?.offset[0] || 0;
                        const offsetY = app.canvas.ds?.offset[1] || 0;
                        
                        graphPos = [
                            (clientX - offsetX) / scale,
                            (clientY - offsetY) / scale
                        ];
                    }
                    
                    console.log(`🎬 Drop at: screen(${e.clientX}, ${e.clientY}) -> graph(${graphPos[0]}, ${graphPos[1]})`);
                    
                    this.spawnNodeAtPosition(nodeData.nodeClass, nodeData.displayName, graphPos[0], graphPos[1]);
                    
                } catch (error) {
                    console.error("🎬 Error handling drop:", error);
                }
            });
        };
        
        // Start trying to setup drop handlers
        setupDrop();
    }

    spawnNodeAtPosition(nodeClass, displayName, x, y) {
        try {
            // Create the node using the correct ComfyUI/LiteGraph API
            let node = null;
            
            // Try different methods to create the node
            if (typeof LiteGraph !== 'undefined' && LiteGraph.createNode) {
                node = LiteGraph.createNode(nodeClass);
            } else if (app.graph && app.graph.createNode) {
                node = app.graph.createNode(nodeClass);
            } else if (window.LiteGraph && window.LiteGraph.createNode) {
                node = window.LiteGraph.createNode(nodeClass);
            } else {
                throw new Error("No suitable node creation method found");
            }
            
            if (!node) {
                throw new Error(`Failed to create node of type: ${nodeClass}. Make sure the node is registered.`);
            }
            
            // Position the node at the specified position
            node.pos = [x, y];
            
            // Add the node to the graph
            app.graph.add(node);
            
            // Refresh the graph display
            if (app.graph.setDirtyCanvas) {
                app.graph.setDirtyCanvas(true, true);
            }
            
            console.log(`🎬 Spawned ${nodeClass} node at position [${x}, ${y}]`);
            
        } catch (error) {
            console.error(`🎬 Failed to spawn ${nodeClass} node:`, error);
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎭 Spawn Failed",
                detail: `Failed to create ${displayName} node: ${error.message}`,
                life: 4000
            });
        }
    }

    createCanvasOnlyNodePanel() {
        // Create fixed left sidebar for canvas-only mode
        const panel = document.createElement('div');
        panel.id = 'obobo-canvas-node-panel';
        panel.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 80px;
            height: 100vh;
            background: rgba(25, 25, 25, 0.95);
            border-right: 1px solid #444;
            backdrop-filter: blur(10px);
            z-index: 10000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            flex-direction: column;
        `;

        // Create content area (no header needed for minimal design)
        const content = document.createElement('div');
        content.style.cssText = `
            padding: 8px;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        `;

        // Add save workflow button
        const saveButton = document.createElement('button');
        saveButton.textContent = '💾';
        saveButton.title = 'Save Workflow';
        saveButton.style.cssText = `
            width: 100%;
            height: 48px;
            background-color: #FF9800;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        saveButton.addEventListener('mouseenter', () => {
            saveButton.style.backgroundColor = '#F57C00';
            saveButton.style.transform = 'scale(1.05)';
        });

        saveButton.addEventListener('mouseleave', () => {
            saveButton.style.backgroundColor = '#FF9800';
            saveButton.style.transform = 'scale(1)';
        });

        saveButton.addEventListener('click', () => {
            this.saveWorkflow();
        });

        // Create simple node list
        const allNodes = [
            // Input nodes
            { name: 'Text', class: 'OboboInputText', icon: '📝' },
            { name: 'Number', class: 'OboboInputNumber', icon: '🔢' },
            { name: 'Vector2', class: 'OboboInputVector2', icon: '📐' },
            { name: 'Image', class: 'OboboInputImage', icon: '🖼️' },
            { name: 'Audio', class: 'OboboInputAudio', icon: '🔊' },
            { name: 'Video', class: 'OboboInputVideo', icon: '🎥' },
            { name: 'LoRA', class: 'OboboInputLora', icon: '🎯' },
            // Output nodes
            { name: 'Output', class: 'OboboOutput', icon: '💾' },
            // Control nodes
            { name: 'Bypass', class: 'OboboConditionalBypass', icon: '🔀' }
        ];

        content.appendChild(saveButton);

        // Add separator line
        const separator = document.createElement('div');
        separator.style.cssText = `
            height: 1px;
            background: #444;
            margin: 8px 0;
        `;
        content.appendChild(separator);

        // Add all nodes in a single column
        allNodes.forEach(node => {
            const button = this.createCompactNodeButton(node);
            content.appendChild(button);
        });

        // Assemble panel
        panel.appendChild(content);
        document.body.appendChild(panel);

        console.log('🎬 Fixed left sidebar created for canvas-only mode');
    }

    createCompactNodeButton(node) {
        const button = document.createElement('button');
        button.textContent = `${node.icon}`;
        button.title = node.name; // Tooltip
        button.draggable = true;
        button.style.cssText = `
            width: 100%;
            height: 44px;
            background-color: #2d2d2d;
            color: white;
            border: 1px solid #444;
            border-radius: 6px;
            cursor: grab;
            font-size: 16px;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        // Hover effects
        button.addEventListener('mouseenter', () => {
            button.style.backgroundColor = '#3d3d3d';
            button.style.borderColor = '#555';
            button.style.transform = 'scale(1.05)';
        });

        button.addEventListener('mouseleave', () => {
            button.style.backgroundColor = '#2d2d2d';
            button.style.borderColor = '#444';
            button.style.transform = 'scale(1)';
        });

        // Drag functionality (reuse existing logic)
        button.addEventListener('dragstart', (e) => {
            button.style.cursor = 'grabbing';
            button.style.opacity = '0.5';

            e.dataTransfer.setData('application/json', JSON.stringify({
                nodeClass: node.class,
                displayName: node.name,
                icon: node.icon
            }));

            e.dataTransfer.effectAllowed = 'copy';

            // Create drag image with icon
            const dragImage = document.createElement('div');
            dragImage.textContent = node.icon;
            dragImage.style.cssText = `
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                background-color: rgba(0, 0, 0, 0.8);
                border: 2px solid white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                position: absolute;
                top: -1000px;
                left: -1000px;
            `;

            document.body.appendChild(dragImage);
            e.dataTransfer.setDragImage(dragImage, 16, 16);

            setTimeout(() => document.body.removeChild(dragImage), 50);

            console.log(`🎬 Started dragging ${node.name} node from floating panel`);
        });

        button.addEventListener('dragend', () => {
            button.style.cursor = 'grab';
            button.style.opacity = '1';
        });

        // Click fallback
        button.addEventListener('click', () => {
            this.spawnNode(node.class, node.name);
        });

        return button;
    }


}

// Initialize the worker manager
let oboboWorkerManager = null;

app.registerExtension({
    name: "obobo.worker.ui",
    
    async setup() {
        console.log("🎬 Obobo Worker UI extension setup");
        
        // Create the worker manager
        oboboWorkerManager = new OboboWorkerManager();
        
        // Note: Sidebar removed - obobo nodes now only available in canvas-only mode
        console.log("🎬 Obobo nodes available in canvas-only mode via fixed left sidebar");
    }
});

console.log("🎬 Obobo Worker Manager extension registered!");
