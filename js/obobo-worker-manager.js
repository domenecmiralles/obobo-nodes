import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("🎬 Obobo Worker Manager extension loading...");

class OboboWorkerUI {
    constructor() {
        this.workerStatus = "🔴 Stopped";
        this.isWorkerRunning = false;
        this.popup = null;
        this.button = null;
        this.secretId = null;
        this.workerLink = null;
        
        this.init();
    }
    
    init() {
        // Wait for ComfyUI to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.createUI());
        } else {
            this.createUI();
        }
        
        // Also try after a short delay to ensure ComfyUI UI is fully loaded
        setTimeout(() => this.createUI(), 500);
        setTimeout(() => this.createUI(), 2000);
    }
    
    createUI() {
        // Don't create multiple buttons
        if (this.button && document.contains(this.button)) {
            console.log("🎬 Button already exists");
            return;
        }
        
        console.log("🎬 Creating Obobo UI...");
        
        this.createButton();
        this.createPopup();
        this.addToComfyUI();
    }
    
    createButton() {
        this.button = document.createElement("button");
        this.button.innerHTML = "🎬 Obobo Worker";
        this.button.id = "obobo-worker-button";
        this.button.className = "obobo-worker-btn";
        
        // Style the button to match ComfyUI's aesthetic
        Object.assign(this.button.style, {
            position: "fixed",
            top: "10px",
            right: "10px",
            zIndex: "9999",
            padding: "8px 12px",
            backgroundColor: "#353535",
            color: "#ffffff",
            border: "1px solid #555555",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "12px",
            fontFamily: "Arial, sans-serif",
            fontWeight: "bold",
            boxShadow: "0 2px 4px rgba(0,0,0,0.3)",
            transition: "all 0.2s ease"
        });
        
        // Add hover effects
        this.button.addEventListener("mouseenter", () => {
            this.button.style.backgroundColor = "#454545";
            this.button.style.transform = "translateY(-1px)";
        });
        
        this.button.addEventListener("mouseleave", () => {
            this.button.style.backgroundColor = "#353535";
            this.button.style.transform = "translateY(0)";
        });
        
        // Add click handler
        this.button.addEventListener("click", () => this.togglePopup());
        
        console.log("🎬 Button created");
    }
    
    createPopup() {
        this.popup = document.createElement("div");
        this.popup.id = "obobo-worker-popup";
        this.popup.className = "obobo-worker-popup";
        
        // Style the popup
        Object.assign(this.popup.style, {
            position: "fixed",
            top: "50px",
            right: "10px",
            width: "320px",
            backgroundColor: "#2a2a2a",
            border: "1px solid #555555",
            borderRadius: "8px",
            padding: "20px",
            zIndex: "10000",
            display: "none",
            boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
            color: "#ffffff",
            fontSize: "14px",
            fontFamily: "Arial, sans-serif"
        });
        
        this.popup.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #444; padding-bottom: 10px;">
                <h3 style="margin: 0; color: #ffffff; font-size: 16px;">🎬 Obobo Worker</h3>
                <button id="obobo-close-btn" style="background: none; border: none; color: #ffffff; cursor: pointer; font-size: 18px; padding: 0; width: 20px; height: 20px;">×</button>
            </div>
            
            <div style="margin-bottom: 15px; text-align: center; padding: 10px; background: #1a1a1a; border-radius: 4px;">
                <div id="obobo-status" style="font-weight: bold;">${this.workerStatus}</div>
            </div>
            
            <div id="obobo-worker-link" style="margin-bottom: 15px; padding: 10px; background: #2a4a2a; border-radius: 4px; display: none;">
                <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">Worker Dashboard:</div>
                <a id="obobo-link" href="#" target="_blank" style="color: #4CAF50; text-decoration: none; font-weight: bold; word-break: break-all;"></a>
                <button id="obobo-copy-link" style="margin-left: 10px; padding: 2px 6px; background: #4CAF50; color: white; border: none; border-radius: 2px; cursor: pointer; font-size: 10px;">Copy</button>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button id="obobo-start-btn" style="flex: 1; padding: 10px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Start Worker</button>
                <button id="obobo-stop-btn" style="flex: 1; padding: 10px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Stop Worker</button>
            </div>
            
            <div style="margin-top: 15px; font-size: 12px; color: #aaa; text-align: center;">
                Worker will process your Obobo jobs automatically
            </div>
        `;
        
        // Add event listeners
        this.popup.querySelector("#obobo-close-btn").addEventListener("click", () => this.hidePopup());
        this.popup.querySelector("#obobo-start-btn").addEventListener("click", () => this.startWorker());
        this.popup.querySelector("#obobo-stop-btn").addEventListener("click", () => this.stopWorker());
        this.popup.querySelector("#obobo-copy-link").addEventListener("click", () => this.copyWorkerLink());
        
        // Prevent popup from closing when clicking inside it
        this.popup.addEventListener("click", (e) => e.stopPropagation());
        
        console.log("🎬 Popup created");
    }
    
    addToComfyUI() {
        // Add button and popup to the document
        document.body.appendChild(this.button);
        document.body.appendChild(this.popup);
        
        // Close popup when clicking outside
        document.addEventListener("click", (e) => {
            if (!this.popup.contains(e.target) && e.target !== this.button) {
                this.hidePopup();
            }
        });
        
        console.log("🎬 UI added to ComfyUI successfully!");
    }
    
    togglePopup() {
        if (this.popup.style.display === "none" || this.popup.style.display === "") {
            this.showPopup();
        } else {
            this.hidePopup();
        }
    }
    
    showPopup() {
        this.popup.style.display = "block";
        this.updateStatus();
        console.log("🎬 Popup shown");
    }
    
    hidePopup() {
        this.popup.style.display = "none";
        console.log("🎬 Popup hidden");
    }
    
    updateStatus() {
        const statusEl = this.popup.querySelector("#obobo-status");
        if (statusEl) {
            statusEl.textContent = this.workerStatus;
        }
    }
    
    async startWorker() {
        console.log("🎬 Starting worker...");
        this.workerStatus = "🟡 Starting...";
        this.updateStatus();
        
        try {
            // Call the Python worker script via ComfyUI API
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
                this.workerStatus = "🟢 Running";
                this.isWorkerRunning = true;
                this.secretId = result.secret_id;
                this.workerLink = `https://obobo.net/start_worker/${this.secretId}`;
                
                this.updateStatus();
                this.showWorkerLink();
                
                console.log("🎬 Worker started successfully");
                
                // Update button to show running status
                this.button.innerHTML = "🟢 Obobo Worker";
            } else {
                throw new Error(result.message || "Failed to start worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to start worker:", error);
            this.workerStatus = "❌ Failed to start";
            this.updateStatus();
            alert(`Failed to start worker: ${error.message}`);
        }
    }
    
    async stopWorker() {
        console.log("🎬 Stopping worker...");
        this.workerStatus = "🟡 Stopping...";
        this.updateStatus();
        
        try {
            // Call the Python worker script via ComfyUI API
            const response = await api.fetchApi("/obobo/stop_worker", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                }
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.workerStatus = "🔴 Stopped";
                this.isWorkerRunning = false;
                this.secretId = null;
                this.workerLink = null;
                
                this.updateStatus();
                this.hideWorkerLink();
                
                console.log("🎬 Worker stopped successfully");
                
                // Update button to show stopped status
                this.button.innerHTML = "🎬 Obobo Worker";
            } else {
                throw new Error(result.message || "Failed to stop worker");
            }
            
        } catch (error) {
            console.error("🎬 Failed to stop worker:", error);
            this.workerStatus = "❌ Failed to stop";
            this.updateStatus();
            alert(`Failed to stop worker: ${error.message}`);
        }
    }
    
    showWorkerLink() {
        const linkContainer = this.popup.querySelector("#obobo-worker-link");
        const linkElement = this.popup.querySelector("#obobo-link");
        
        if (this.workerLink && linkContainer && linkElement) {
            linkElement.href = this.workerLink;
            linkElement.textContent = this.workerLink;
            linkContainer.style.display = "block";
        }
    }
    
    hideWorkerLink() {
        const linkContainer = this.popup.querySelector("#obobo-worker-link");
        if (linkContainer) {
            linkContainer.style.display = "none";
        }
    }
    
    copyWorkerLink() {
        if (this.workerLink) {
            navigator.clipboard.writeText(this.workerLink).then(() => {
                const copyBtn = this.popup.querySelector("#obobo-copy-link");
                const originalText = copyBtn.textContent;
                copyBtn.textContent = "Copied!";
                copyBtn.style.background = "#2a5a2a";
                
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.style.background = "#4CAF50";
                }, 2000);
            }).catch(err => {
                console.error("Failed to copy link:", err);
                alert("Failed to copy link to clipboard");
            });
        }
    }
}

// Initialize the UI when the extension loads
let oboboUI = null;

app.registerExtension({
    name: "obobo.worker.ui",
    
    async setup() {
        console.log("🎬 Obobo Worker UI extension setup");
        
        // Create the UI
        oboboUI = new OboboWorkerUI();
    }
});

console.log("🎬 Obobo Worker Manager extension registered!");
