import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("🎬 Obobo Worker Manager extension loading...");

class OboboWorkerManager {
    constructor() {
        this.workerStatus = "🔴 No Worker";
        this.isWorkerActive = false;
        this.totalWorkers = 0;
        this.workers = {};
        this.sidebarElement = null;
        
        // Load status on startup
        this.loadWorkerStatus();
        
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
                
                if (this.activeWorkers > 0) {
                    this.workerStatus = "🟢 Active";
                    this.isWorkerActive = true;
                } else if (this.totalWorkers > 0) {
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
            const claimButton = this.sidebarElement.querySelector("#obobo-claim-button");
            
            if (statusEl) {
                statusEl.textContent = this.workerStatus;
            }
            
            // Update details
            if (detailsEl) {
                let detailsText = "";
                if (this.totalWorkers > 0) {
                    const workerInfo = Object.values(this.workers)[0];
                    if (workerInfo) {
                        detailsText = `Worker: ${workerInfo.worker_id}`;
                    }
                } else {
                    detailsText = "No worker configured";
                }
                detailsEl.textContent = detailsText;
            }
            
            // Show only start OR stop button, not both
            if (startButton && stopButton) {
                if (this.isWorkerActive) {
                    startButton.style.display = "none";
                    stopButton.style.display = "block";
                } else {
                    startButton.style.display = "block";
                    stopButton.style.display = "none";
                }
            }
            
            // Show claim button only when we have a worker
            if (claimButton) {
                if (this.totalWorkers > 0) {
                    claimButton.style.display = "block";
                } else {
                    claimButton.style.display = "none";
                }
            }
        }
    }
    
    claimWorker() {
        if (this.totalWorkers > 0) {
            const workerInfo = Object.values(this.workers)[0];
            if (workerInfo && workerInfo.worker_id) {
                const url = `http://localhost:5173/start_worker/${workerInfo.worker_id}`;
                window.open(url, '_blank');
                console.log("🎬 Opening claim worker URL:", url);
                
                // Show info toast
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
        console.log("🎬 Starting worker...");
        
        // Show starting toast
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
                    api_url: "https://inference.obobo.net"
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log("🎬 Worker started successfully");
                
                // Refresh worker status
                await this.loadWorkerStatus();
                
                // Show success toast
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "🎬 Worker Started",
                    detail: `Worker is now active and processing jobs.`,
                    life: 5000
                });
                
            } else {
                throw new Error(result.message || "Failed to start worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to start worker:", error);
            this.workerStatus = "❌ Failed to start";
            this.isWorkerActive = false;
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
        console.log("🎬 Stopping worker...");
        
        // Show stopping toast
        app.extensionManager.toast.add({
            severity: "info",
            summary: "🎬 Obobo Worker",
            detail: "Stopping worker...",
            life: 3000
        });
        
        this.workerStatus = "🟡 Stopping...";
        this.updateSidebarContent();
        
        try {
            const response = await api.fetchApi("/obobo/stop_worker", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({}) // Send empty JSON object
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log("🎬 Worker stopped successfully");
                
                // Refresh worker status
                await this.loadWorkerStatus();
                
                // Show success toast
                app.extensionManager.toast.add({
                    severity: "success",
                    summary: "🎬 Worker Stopped",
                    detail: "Worker has been marked as inactive",
                    life: 3000
                });
            } else {
                throw new Error(result.message || "Failed to stop worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to stop worker:", error);
            this.workerStatus = "❌ Failed to stop";
            this.updateSidebarContent();
            
            app.extensionManager.toast.add({
                severity: "error",
                summary: "🎬 Worker Stop Failed",
                detail: `Failed to stop worker: ${error.message}`,
                life: 5000
            });
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
                stopButton.textContent = 'Stop Worker';
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
                
                buttonContainer.appendChild(startButton);
                buttonContainer.appendChild(stopButton);
                buttonContainer.appendChild(claimButton);
                
                // Info text
                const infoText = document.createElement('div');
                infoText.style.fontSize = '12px';
                infoText.style.color = '#aaa';
                infoText.style.textAlign = 'center';
                infoText.style.marginTop = 'auto';
                infoText.textContent = 'Consistent worker processes jobs from the API';
                
                // Add event listeners
                startButton.addEventListener('click', () => {
                    oboboWorkerManager.startWorker();
                });
                
                stopButton.addEventListener('click', () => {
                    oboboWorkerManager.stopWorker();
                });
                
                claimButton.addEventListener('click', () => {
                    oboboWorkerManager.claimWorker();
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
