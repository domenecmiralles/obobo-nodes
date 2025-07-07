import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("🎬 Obobo Worker Manager extension loading...");

class OboboWorkerManager {
    constructor() {
        this.workerStatus = "🔴 No Worker";
        this.isWorkerActive = false;
        this.hasWorkerProcess = false;  // New flag to track if worker process exists
        this.totalWorkers = 0;
        this.workers = {};
        this.sidebarElement = null;
        
        // Load status on startup
        this.loadWorkerStatus();
        
        // Check for auto-load workflow parameter
        this.checkAutoLoadWorkflow();
        
        // Refresh status periodically
        setInterval(() => {
            this.loadWorkerStatus();
        }, 10000); // Every 10 seconds
    }
    
    async loadWorkerStatus() {
        try {
            const response = await api.fetchApi("/obobo/worker_status");
            const result = await response.json();
            
            if (result.success) {
                this.activeWorkers = result.active_workers || 0;
                this.totalWorkers = result.total_workers || 0;
                this.workers = result.workers || {};
                
                // Update hasWorkerProcess if we have any workers registered
                this.hasWorkerProcess = this.totalWorkers > 0;
                
                if (this.activeWorkers > 0) {
                    this.workerStatus = "🟢 Active";
                    this.isWorkerActive = true;
                } else if (this.hasWorkerProcess) {
                    this.workerStatus = "🟡 Inactive";
                    this.isWorkerActive = false;
                } else {
                    this.workerStatus = "🔴 No Worker";
                    this.isWorkerActive = false;
                }
                
                this.updateSidebarContent();
            }
        } catch (error) {
            console.error("🎬 Failed to load worker status:", error);
        }
    }
    
    updateSidebarContent() {
        if (this.sidebarElement) {
            const statusEl = this.sidebarElement.querySelector("#obobo-status");
            const detailsEl = this.sidebarElement.querySelector("#obobo-details");
            const startButton = this.sidebarElement.querySelector("#obobo-start-button");
            const stopButton = this.sidebarElement.querySelector("#obobo-stop-button");
            const resumeButton = this.sidebarElement.querySelector("#obobo-resume-button");
            const claimButton = this.sidebarElement.querySelector("#obobo-claim-button");
            
            if (statusEl) {
                statusEl.textContent = this.workerStatus;
            }
            
            // Update details
            if (detailsEl) {
                let detailsText = "";
                if (this.hasWorkerProcess) {
                    const workerInfo = Object.values(this.workers)[0];
                    if (workerInfo) {
                        detailsText = `Worker: ${workerInfo.worker_id}`;
                    }
                } else {
                    detailsText = "No worker configured";
                }
                detailsEl.textContent = detailsText;
            }
            
            // Show appropriate buttons based on state
            if (startButton && stopButton && resumeButton) {
                if (!this.hasWorkerProcess) {
                    // No worker process exists - show start button only
                    startButton.style.display = "block";
                    stopButton.style.display = "none";
                    resumeButton.style.display = "none";
                } else if (this.isWorkerActive) {
                    // Worker exists and is active - show stop button only
                    startButton.style.display = "none";
                    stopButton.style.display = "block";
                    resumeButton.style.display = "none";
                } else {
                    // Worker exists but is inactive - show resume button only
                    startButton.style.display = "none";
                    stopButton.style.display = "none";
                    resumeButton.style.display = "block";
                }
            }
            
            // Show claim button only when we have a worker
            if (claimButton) {
                claimButton.style.display = this.hasWorkerProcess ? "block" : "none";
            }
        }
    }
    
    claimWorker() {
        if (this.hasWorkerProcess) {
            const workerInfo = Object.values(this.workers)[0];
            if (workerInfo && workerInfo.worker_id) {
                const url = `http://localhost:5173/start_worker/${workerInfo.worker_id}`;
                window.open(url, '_blank');
                console.log("🎬 Opening claim worker URL:", url);
                
                app.extensionManager.toast.add({
                    severity: "info",
                    summary: "🎬 Claim Worker",
                    detail: `Opening claim page for worker ${workerInfo.worker_id}`,
                    life: 3000
                });
            } else {
                console.error("🎬 No worker ID available for claiming");
                app.extensionManager.toast.add({
                    severity: "error",
                    summary: "🎬 Claim Worker Failed",
                    detail: "No worker ID available",
                    life: 3000
                });
            }
        }
    }
    
    async startWorker() {
        if (this.hasWorkerProcess) {
            console.error("🎬 Worker process already exists");
            return;
        }
        
        console.log("🎬 Starting worker...");
        
        app.extensionManager.toast.add({
            severity: "info",
            summary: "🎬 Obobo Worker",
            detail: "Starting worker...",
            life: 3000
        });
        
        this.workerStatus = "🟡 Starting...";
        this.updateSidebarContent();
        
        try {
            const response = await api.fetchApi("/obobo/start_worker", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    api_url: "http://127.0.0.1:8001", //"https://inference.obobo.net"
                    private: true  // Set worker as private
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log("🎬 Worker started successfully");
                this.hasWorkerProcess = true;
                
                await this.loadWorkerStatus();
                
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "🎬 Worker Started",
                    detail: `Worker process created and is now active.`,
                    life: 5000
                });
                
            } else {
                throw new Error(result.message || "Failed to start worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to start worker:", error);
            this.workerStatus = "❌ Failed to start";
            this.isWorkerActive = false;
            this.hasWorkerProcess = false;
            this.updateSidebarContent();
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Worker Start Failed",
                detail: `Failed to start worker: ${error.message}`,
                life: 5000
            });
        }
    }
    
    async stopWorker() {
        if (!this.hasWorkerProcess || !this.isWorkerActive) {
            console.error("🎬 No active worker to stop");
            return;
        }
        
        console.log("🎬 Setting worker to inactive...");
        
        app.extensionManager.toast.add({
            severity: "info",
            summary: "🎬 Obobo Worker",
            detail: "Setting worker to inactive...",
            life: 3000
        });
        
        this.workerStatus = "🟡 Updating...";
        this.updateSidebarContent();
        
        try {
            const response = await api.fetchApi("/obobo/stop_worker", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log("🎬 Worker set to inactive successfully");
                
                await this.loadWorkerStatus();
                
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "🎬 Worker Updated",
                    detail: "Worker has been set to inactive",
                    life: 3000
                });
            } else {
                throw new Error(result.message || "Failed to stop worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to stop worker:", error);
            this.workerStatus = "❌ Failed to update";
            this.updateSidebarContent();
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Worker Update Failed",
                detail: `Failed to set worker inactive: ${error.message}`,
                life: 5000
            });
        }
    }
    
    async resumeWorker() {
        if (!this.hasWorkerProcess || this.isWorkerActive) {
            console.error("🎬 No inactive worker to resume");
            return;
        }
        
        console.log("🎬 Setting worker to active...");
        
        app.extensionManager.toast.add({
            severity: "info",
            summary: "🎬 Obobo Worker",
            detail: "Setting worker to active...",
            life: 3000
        });
        
        this.workerStatus = "🟡 Updating...";
        this.updateSidebarContent();
        
        try {
            const response = await api.fetchApi("/obobo/resume_worker", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log("🎬 Worker set to active successfully");
                
                await this.loadWorkerStatus();
                
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "🎬 Worker Updated",
                    detail: "Worker has been set to active",
                    life: 3000
                });
            } else {
                throw new Error(result.message || "Failed to resume worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to resume worker:", error);
            this.workerStatus = "❌ Failed to update";
            this.updateSidebarContent();
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Worker Update Failed",
                detail: `Failed to set worker active: ${error.message}`,
                life: 5000
            });
        }
    }

    async loadWorkflow() {
        try {
            // Get workflow URL from our local endpoint
            const response = await api.fetchApi("/obobo/current_workflow");
            if (!response.ok) {
                throw new Error(`Failed to get workflow URL: ${response.statusText}`);
            }
            
            const data = await response.json();
            if (!data.workflow_url) {
                throw new Error("No workflow currently assigned to worker");
            }
            
            console.log("🎬 Loading workflow from URL:", data.workflow_url);
            
            // Use the same loading logic as auto-load
            await this.loadWorkflowFromUrl(data.workflow_url);
            
        } catch (error) {
            console.error("🎬 Failed to load workflow:", error);
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Load Workflow Failed",
                detail: `Failed to load workflow: ${error.message}`,
                life: 5000
            });
        }
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
                    }
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
}

// Initialize the worker manager
let oboboWorkerManager = null;

app.registerExtension({
    name: "obobo.worker.ui",
    
    async setup() {
        console.log("🎬 Obobo Worker UI extension setup");
        
        // Create the worker manager
        oboboWorkerManager = new OboboWorkerManager();
        
        // Register sidebar tab
        app.extensionManager.registerSidebarTab({
            id: "oboboWorker",
            icon: "mdi mdi-robot",
            title: "Obobo Worker",
            tooltip: "Manage Obobo Worker",
            type: "custom",
            render: (el) => {
                oboboWorkerManager.sidebarElement = el;
                
                const container = document.createElement('div');
                container.style.padding = '20px';
                container.style.height = '100%';
                container.style.display = 'flex';
                container.style.flexDirection = 'column';
                container.style.gap = '15px';
                
                // Title
                const title = document.createElement('h3');
                title.textContent = '🎬 Obobo Worker';
                title.style.margin = '0 0 10px 0';
                title.style.color = '#ffffff';
                title.style.fontSize = '16px';
                title.style.borderBottom = '1px solid #444';
                title.style.paddingBottom = '10px';
                
                // Status display
                const statusContainer = document.createElement('div');
                statusContainer.style.textAlign = 'center';
                statusContainer.style.padding = '10px';
                statusContainer.style.backgroundColor = '#1a1a1a';
                statusContainer.style.borderRadius = '4px';
                statusContainer.style.marginBottom = '10px';
                
                const statusText = document.createElement('div');
                statusText.id = 'obobo-status';
                statusText.style.fontWeight = 'bold';
                statusText.style.color = '#ffffff';
                statusText.textContent = oboboWorkerManager.workerStatus;
                
                const detailsText = document.createElement('div');
                detailsText.id = 'obobo-details';
                detailsText.style.fontSize = '12px';
                detailsText.style.color = '#aaa';
                detailsText.style.marginTop = '5px';
                detailsText.textContent = 'Loading...';
                
                statusContainer.appendChild(statusText);
                statusContainer.appendChild(detailsText);
                
                // Action buttons
                const buttonContainer = document.createElement('div');
                buttonContainer.style.display = 'flex';
                buttonContainer.style.gap = '10px';
                buttonContainer.style.flexDirection = 'column';
                
                const startButton = document.createElement('button');
                startButton.id = 'obobo-start-button';
                startButton.textContent = 'Start Worker';
                startButton.style.width = '100%';
                startButton.style.padding = '12px';
                startButton.style.backgroundColor = '#4CAF50';
                startButton.style.color = 'white';
                startButton.style.border = 'none';
                startButton.style.borderRadius = '4px';
                startButton.style.cursor = 'pointer';
                startButton.style.fontWeight = 'bold';
                startButton.style.fontSize = '14px';
                
                const stopButton = document.createElement('button');
                stopButton.id = 'obobo-stop-button';
                stopButton.textContent = 'Set Inactive';
                stopButton.style.width = '100%';
                stopButton.style.padding = '12px';
                stopButton.style.backgroundColor = '#f44336';
                stopButton.style.color = 'white';
                stopButton.style.border = 'none';
                stopButton.style.borderRadius = '4px';
                stopButton.style.cursor = 'pointer';
                stopButton.style.fontWeight = 'bold';
                stopButton.style.fontSize = '14px';
                stopButton.style.display = 'none';  // Initially hidden
                
                const resumeButton = document.createElement('button');
                resumeButton.id = 'obobo-resume-button';
                resumeButton.textContent = 'Set Active';
                resumeButton.style.width = '100%';
                resumeButton.style.padding = '12px';
                resumeButton.style.backgroundColor = '#4CAF50';
                resumeButton.style.color = 'white';
                resumeButton.style.border = 'none';
                resumeButton.style.borderRadius = '4px';
                resumeButton.style.cursor = 'pointer';
                resumeButton.style.fontWeight = 'bold';
                resumeButton.style.fontSize = '14px';
                resumeButton.style.display = 'none';  // Initially hidden
                
                const claimButton = document.createElement('button');
                claimButton.id = 'obobo-claim-button';
                claimButton.textContent = 'Claim Worker';
                claimButton.style.width = '100%';
                claimButton.style.padding = '12px';
                claimButton.style.backgroundColor = '#2196F3';
                claimButton.style.color = 'white';
                claimButton.style.border = 'none';
                claimButton.style.borderRadius = '4px';
                claimButton.style.cursor = 'pointer';
                claimButton.style.fontWeight = 'bold';
                claimButton.style.fontSize = '14px';
                claimButton.style.display = 'none';  // Initially hidden
                
                // Add Save Workflow button
                const saveWorkflowButton = document.createElement('button');
                saveWorkflowButton.id = 'obobo-save-workflow-button';
                saveWorkflowButton.textContent = 'Save Workflow';
                saveWorkflowButton.style.width = '100%';
                saveWorkflowButton.style.padding = '12px';
                saveWorkflowButton.style.backgroundColor = '#FF9800';
                saveWorkflowButton.style.color = 'white';
                saveWorkflowButton.style.border = 'none';
                saveWorkflowButton.style.borderRadius = '4px';
                saveWorkflowButton.style.cursor = 'pointer';
                saveWorkflowButton.style.fontWeight = 'bold';
                saveWorkflowButton.style.fontSize = '14px';

                buttonContainer.appendChild(startButton);
                buttonContainer.appendChild(stopButton);
                buttonContainer.appendChild(resumeButton);
                buttonContainer.appendChild(claimButton);
                buttonContainer.appendChild(saveWorkflowButton);
                
                // Info text
                const infoText = document.createElement('div');
                infoText.style.fontSize = '12px';
                infoText.style.color = '#aaa';
                infoText.style.textAlign = 'center';
                infoText.style.marginTop = 'auto';
                infoText.textContent = 'Worker process runs continuously, toggle active/inactive state as needed';
                
                // Add event listeners
                startButton.addEventListener('click', () => {
                    oboboWorkerManager.startWorker();
                });
                
                stopButton.addEventListener('click', () => {
                    oboboWorkerManager.stopWorker();
                });
                
                resumeButton.addEventListener('click', () => {
                    oboboWorkerManager.resumeWorker();
                });
                
                claimButton.addEventListener('click', () => {
                    oboboWorkerManager.claimWorker();
                });

                saveWorkflowButton.addEventListener('click', () => {
                    oboboWorkerManager.saveWorkflow();
                });
                
                // Assemble the UI
                container.appendChild(title);
                container.appendChild(statusContainer);
                container.appendChild(buttonContainer);
                container.appendChild(infoText);
                
                el.appendChild(container);
                
                // Initial content update
                oboboWorkerManager.updateSidebarContent();
            }
        });
    }
});

console.log("🎬 Obobo Worker Manager extension registered!");
