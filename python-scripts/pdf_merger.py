<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Processor & Merger Suite</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }

        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }

        /* Navigation Tabs */
        .nav-tabs {
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 5px;
            backdrop-filter: blur(10px);
        }

        .nav-tab {
            flex: 1;
            max-width: 250px;
            padding: 15px 25px;
            text-align: center;
            cursor: pointer;
            border-radius: 10px;
            transition: all 0.3s ease;
            color: white;
            font-weight: 600;
            text-decoration: none;
        }

        .nav-tab:hover {
            background: rgba(255,255,255,0.2);
            transform: translateY(-2px);
        }

        .nav-tab.active {
            background: white;
            color: #4f46e5;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        /* Content Panels */
        .content-panel {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            padding: 40px;
            display: none;
        }

        .content-panel.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Form Processor Styles */
        .step {
            margin-bottom: 30px;
            padding: 25px;
            border: 2px dashed #e0e7ff;
            border-radius: 15px;
            transition: all 0.3s ease;
        }

        .step.active {
            border-color: #4f46e5;
            background: #f8faff;
        }

        .step-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }

        .step-number {
            background: #4f46e5;
            color: white;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 15px;
        }

        .step-title {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1f2937;
        }

        /* Upload Areas */
        .upload-area {
            border: 2px dashed #d1d5db;
            border-radius: 10px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }

        .upload-area:hover {
            border-color: #4f46e5;
            background: #f8faff;
        }

        .upload-area.dragover {
            border-color: #4f46e5;
            background: #e0e7ff;
        }

        .upload-area.has-files {
            border-color: #10b981;
            background: #f0fdf4;
        }

        .upload-icon {
            font-size: 3rem;
            margin-bottom: 15px;
            opacity: 0.6;
        }

        /* File Lists */
        .file-list {
            margin-top: 20px;
        }

        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 15px;
            background: #f3f4f6;
            border-radius: 8px;
            margin-bottom: 8px;
        }

        .file-info {
            display: flex;
            align-items: center;
            flex: 1;
        }

        .file-name {
            font-weight: 500;
            margin-right: 10px;
        }

        .file-size {
            color: #6b7280;
            font-size: 0.9rem;
        }

        .remove-btn {
            background: #ef4444;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.8rem;
        }

        /* Buttons */
        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }

        .btn-primary {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
        }

        .btn-success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }

        .btn:disabled {
            background: #9ca3af;
            cursor: not-allowed;
            transform: none;
        }

        .btn-block {
            display: block;
            width: 100%;
            margin: 20px 0;
        }

        /* Progress */
        .progress-container {
            margin: 30px 0;
            display: none;
        }

        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981, #059669);
            width: 0%;
            transition: width 0.3s ease;
        }

        .progress-text {
            margin-top: 10px;
            text-align: center;
            color: #6b7280;
        }

        /* Results */
        .results {
            margin-top: 30px;
            padding: 25px;
            border-radius: 10px;
            display: none;
        }

        .results.success {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
        }

        .results.error {
            background: #fef2f2;
            border: 1px solid #fecaca;
        }

        /* Merger Specific Styles */
        .upload-section {
            margin-bottom: 30px;
            padding: 25px;
            border: 2px dashed #e0e7ff;
            border-radius: 15px;
            transition: all 0.3s ease;
        }

        .upload-section:hover {
            border-color: #4f46e5;
            background: #f8faff;
        }

        .upload-section.dragover {
            border-color: #4f46e5;
            background: #e0e7ff;
            transform: scale(1.02);
        }

        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }

        .section-icon {
            font-size: 2rem;
            margin-right: 15px;
        }

        .section-title {
            font-size: 1.3rem;
            font-weight: 700;
            color: #1f2937;
        }

        .section-subtitle {
            color: #6b7280;
            font-size: 0.9rem;
            margin-top: 5px;
        }

        .upload-text {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .upload-hint {
            color: #6b7280;
            font-size: 0.9rem;
        }

        .smart-corrections {
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            display: none;
        }

        .smart-corrections.show {
            display: block;
        }

        .corrections-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .corrections-icon {
            font-size: 1.5rem;
            margin-right: 10px;
        }

        .corrections-title {
            font-weight: 600;
            color: #92400e;
        }

        .correction-item {
            color: #92400e;
            font-size: 0.9rem;
            margin-bottom: 5px;
        }

        .process-section {
            text-align: center;
            margin-top: 40px;
            padding-top: 30px;
            border-top: 2px solid #f3f4f6;
        }

        /* Overlay styles */
        .overlay-controls {
            background: #f8faff;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }

        .overlay-item {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding: 10px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }

        .overlay-item input[type="text"] {
            flex: 1;
            margin: 0 10px;
            padding: 8px 12px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
        }

        .overlay-item button {
            padding: 8px 15px;
            background: #ef4444;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .nav-tabs {
                flex-direction: column;
            }
            
            .nav-tab {
                max-width: none;
                margin-bottom: 5px;
            }
            
            .content-panel {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🚀 PDF Tools Suite</h1>
            <p>Professional PDF processing for shipping & customs</p>
        </div>

        <!-- Navigation -->
        <div class="nav-tabs">
            <div class="nav-tab active" onclick="switchPanel('processor')" id="processor-tab">
                📝 Form Processor
            </div>
            <div class="nav-tab" onclick="switchPanel('merger')" id="merger-tab">
                🚢 Document Merger
            </div>
        </div>

        <!-- Form Processor Panel -->
        <div class="content-panel active" id="processor-panel">
            <div class="step active">
                <div class="step-header">
                    <div class="step-number">1</div>
                    <div class="step-title">Upload PDF Forms</div>
                </div>
                <div class="upload-area" id="processor-upload">
                    <div class="upload-icon">📄</div>
                    <p><strong>Drop your PDF forms here</strong></p>
                    <p>or click to browse files</p>
                    <input type="file" id="processor-files" accept=".pdf" multiple style="display: none;">
                </div>
                <div class="file-list" id="processor-file-list"></div>
            </div>

            <div class="step">
                <div class="step-header">
                    <div class="step-number">2</div>
                    <div class="step-title">Configure Text Overlays</div>
                </div>
                <div class="overlay-controls">
                    <div id="overlay-list">
                        <!-- Overlay items will be added here -->
                    </div>
                    <button class="btn btn-primary" onclick="addOverlay()">+ Add Text Overlay</button>
                </div>
            </div>

            <button class="btn btn-success btn-block" id="process-forms-btn" onclick="processForms()" disabled>
                🚀 Process Forms
            </button>

            <div class="progress-container" id="processor-progress">
                <div class="progress-bar">
                    <div class="progress-fill" id="processor-progress-fill"></div>
                </div>
                <div class="progress-text" id="processor-progress-text">Processing...</div>
            </div>

            <div class="results" id="processor-results">
                <div id="processor-results-content"></div>
            </div>
        </div>

        <!-- Document Merger Panel -->
        <div class="content-panel" id="merger-panel">
            <!-- Smart Corrections Alert -->
            <div class="smart-corrections" id="smart-corrections">
                <div class="corrections-header">
                    <span class="corrections-icon">🤖</span>
                    <span class="corrections-title">Smart Detection Applied</span>
                </div>
                <div id="corrections-list">
                    <!-- Corrections will be added here -->
                </div>
            </div>

            <!-- Step 1: EDI File -->
            <div class="upload-section">
                <div class="section-header">
                    <div class="section-icon">📊</div>
                    <div>
                        <div class="section-title">1. Upload EDI File</div>
                        <div class="section-subtitle">Excel file containing client manifest (.xls or .xlsx)</div>
                    </div>
                </div>
                <div class="upload-area" id="edi-upload" data-type="edi">
                    <div class="upload-text">Drop EDI file here</div>
                    <div class="upload-hint">or click to browse</div>
                </div>
                <div class="file-list" id="edi-files"></div>
                <input type="file" id="edi-input" accept=".xls,.xlsx" style="display: none;">
            </div>

            <!-- Step 2: Advice of Arrival -->
            <div class="upload-section">
                <div class="section-header">
                    <div class="section-icon">📋</div>
                    <div>
                        <div class="section-title">2. Upload Advice of Arrival</div>
                        <div class="section-subtitle">Multi-client document that will be split automatically</div>
                    </div>
                </div>
                <div class="upload-area" id="advice-upload" data-type="advice">
                    <div class="upload-text">Drop Advice of Arrival PDF here</div>
                    <div class="upload-hint">Document will be split by client reference</div>
                </div>
                <div class="file-list" id="advice-files"></div>
                <input type="file" id="advice-input" accept=".pdf" style="display: none;">
            </div>

            <!-- Step 3: Bills & Customer Documents -->
            <div class="upload-section">
                <div class="section-header">
                    <div class="section-icon">🚢</div>
                    <div>
                        <div class="section-title">3. Upload Bills of Lading & Customer Documents</div>
                        <div class="section-subtitle">All other PDFs - will be grouped by client reference</div>
                    </div>
                </div>
                <div class="upload-area" id="documents-upload" data-type="documents">
                    <div class="upload-text">Drop all other PDF files here</div>
                    <div class="upload-hint">Bills of Lading, Customer docs, etc.</div>
                </div>
                <div class="file-list" id="documents-files"></div>
                <input type="file" id="documents-input" accept=".pdf" multiple style="display: none;">
            </div>

            <!-- Process Section -->
            <div class="process-section">
                <button class="btn btn-success" id="merger-process-btn" onclick="startMergerProcessing()" disabled>
                    🚀 Merge Documents & Apply Page 9 Overlays
                </button>
                
                <div class="progress-container" id="merger-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" id="merger-progress-fill"></div>
                    </div>
                    <div class="progress-text" id="merger-progress-text">Processing...</div>
                </div>

                <div class="results" id="merger-results">
                    <div id="merger-results-content"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Global state for both panels
        let processorFiles = [];
        let processorOverlays = [];
        
        // Merger state
        let mergerFiles = {
            edi: [],
            advice: [],
            documents: []
        };

        // Panel switching
        function switchPanel(panelName) {
            // Update tabs
            document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
            document.getElementById(`${panelName}-tab`).classList.add('active');
            
            // Update panels
            document.querySelectorAll('.content-panel').forEach(panel => panel.classList.remove('active'));
            document.getElementById(`${panelName}-panel`).classList.add('active');
        }

        // ==================== FORM PROCESSOR LOGIC ====================
        
        // Initialize form processor uploads
        function initProcessorUploads() {
            const uploadArea = document.getElementById('processor-upload');
            const fileInput = document.getElementById('processor-files');
            
            uploadArea.addEventListener('click', () => fileInput.click());
            
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                handleProcessorFiles(Array.from(e.dataTransfer.files));
            });
            
            fileInput.addEventListener('change', (e) => {
                handleProcessorFiles(Array.from(e.target.files));
            });
        }

        function handleProcessorFiles(files) {
            processorFiles = files;
            updateProcessorFileList();
            updateProcessorButton();
        }

        function updateProcessorFileList() {
            const fileList = document.getElementById('processor-file-list');
            
            if (processorFiles.length > 0) {
                fileList.innerHTML = processorFiles.map((file, index) => `
                    <div class="file-item">
                        <div class="file-info">
                            <span class="file-name">${file.name}</span>
                            <span class="file-size">(${formatFileSize(file.size)})</span>
                        </div>
                        <button class="remove-btn" onclick="removeProcessorFile(${index})">Remove</button>
                    </div>
                `).join('');
            } else {
                fileList.innerHTML = '';
            }
        }

        function removeProcessorFile(index) {
            processorFiles.splice(index, 1);
            updateProcessorFileList();
            updateProcessorButton();
        }

        function updateProcessorButton() {
            document.getElementById('process-forms-btn').disabled = processorFiles.length === 0;
        }

        // Overlay management
        function addOverlay() {
            const overlayId = Date.now();
            const overlay = {
                id: overlayId,
                text: '',
                x: 200,
                y: 400,
                page: 9,
                fontSize: 11
            };
            
            processorOverlays.push(overlay);
            renderOverlays();
        }

        function removeOverlay(overlayId) {
            processorOverlays = processorOverlays.filter(o => o.id !== overlayId);
            renderOverlays();
        }

        function renderOverlays() {
            const overlayList = document.getElementById('overlay-list');
            
            overlayList.innerHTML = processorOverlays.map(overlay => `
                <div class="overlay-item">
                    <input type="text" placeholder="Text to add" value="${overlay.text}" 
                           onchange="updateOverlay(${overlay.id}, 'text', this.value)">
                    <input type="number" placeholder="X" value="${overlay.x}" style="width: 80px;"
                           onchange="updateOverlay(${overlay.id}, 'x', this.value)">
                    <input type="number" placeholder="Y" value="${overlay.y}" style="width: 80px;"
                           onchange="updateOverlay(${overlay.id}, 'y', this.value)">
                    <input type="number" placeholder="Page" value="${overlay.page}" style="width: 80px;"
                           onchange="updateOverlay(${overlay.id}, 'page', this.value)">
                    <button onclick="removeOverlay(${overlay.id})">Remove</button>
                </div>
            `).join('');
        }

        function updateOverlay(overlayId, field, value) {
            const overlay = processorOverlays.find(o => o.id === overlayId);
            if (overlay) {
                overlay[field] = field === 'text' ? value : parseInt(value);
            }
        }

        // Process forms
        async function processForms() {
            const progressContainer = document.getElementById('processor-progress');
            const progressFill = document.getElementById('processor-progress-fill');
            const progressText = document.getElementById('processor-progress-text');
            const processBtn = document.getElementById('process-forms-btn');
            
            processBtn.disabled = true;
            progressContainer.style.display = 'block';
            
            try {
                // Upload files
                progressText.textContent = 'Uploading files...';
                progressFill.style.width = '25%';
                
                const formData = new FormData();
                processorFiles.forEach(file => formData.append('files', file));
                
                const uploadResponse = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!uploadResponse.ok) throw new Error('Upload failed');
                const uploadResult = await uploadResponse.json();
                
                // Process with overlays
                progressText.textContent = 'Processing forms...';
                progressFill.style.width = '75%';
                
                const processResponse = await fetch('/api/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        files: uploadResult.files,
                        overlays: processorOverlays,
                        settings: {}
                    })
                });
                
                if (!processResponse.ok) throw new Error('Processing failed');
                const processResult = await processResponse.json();
                
                // Complete
                progressText.textContent = 'Complete!';
                progressFill.style.width = '100%';
                
                showProcessorResults(processResult);
                
            } catch (error) {
                progressText.textContent = `Error: ${error.message}`;
                console.error('Processing failed:', error);
            } finally {
                processBtn.disabled = false;
            }
        }

        function showProcessorResults(result) {
            const resultsDiv = document.getElementById('processor-results');
            const resultsContent = document.getElementById('processor-results-content');
            
            resultsContent.innerHTML = `
                <h3>✅ Processing Complete!</h3>
                <p>Successfully processed ${result.stats?.successful || 0} files</p>
                <a href="${result.downloadUrl}" class="btn btn-success" download>📥 Download Results</a>
            `;
            
            resultsDiv.className = 'results success';
            resultsDiv.style.display = 'block';
        }

        // ==================== MERGER LOGIC ====================
        
        // Initialize merger uploads
        function initMergerUploads() {
            const uploadTypes = ['edi', 'advice', 'documents'];
            
            uploadTypes.forEach(type => {
                const uploadArea = document.getElementById(`${type}-upload`);
                const fileInput = document.getElementById(`${type}-input`);
                
                // Click to upload
                uploadArea.addEventListener('click', () => fileInput.click());
                
                // Drag and drop
                uploadArea.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    uploadArea.classList.add('dragover');
                });
                
                uploadArea.addEventListener('dragleave', () => {
                    uploadArea.classList.remove('dragover');
                });
                
                uploadArea.addEventListener('drop', (e) => {
                    e.preventDefault();
                    uploadArea.classList.remove('dragover');
                    
                    const files = Array.from(e.dataTransfer.files);
                    handleMergerFileUpload(type, files);
                });
                
                // File input change
                fileInput.addEventListener('change', (e) => {
                    const files = Array.from(e.target.files);
                    handleMergerFileUpload(type, files);
                });
            });
        }

        // Handle merger file uploads with smart detection
        function handleMergerFileUpload(uploadType, files) {
            const corrections = [];
            
            files.forEach(file => {
                let targetType = uploadType;
                
                // Smart detection
                if (uploadType === 'documents') {
                    // Check if it's actually an EDI file
                    if (file.name.endsWith('.xls') || file.name.endsWith('.xlsx')) {
                        targetType = 'edi';
                        corrections.push(`📊 Moved ${file.name} to EDI section (Excel file detected)`);
                    }
                    // Check if it's an Advice document
                    else if (file.name.toLowerCase().includes('advice')) {
                        targetType = 'advice';
                        corrections.push(`📋 Moved ${file.name} to Advice section (filename contains 'advice')`);
                    }
                }
                
                // Add file to appropriate section
                if (targetType === 'edi' && mergerFiles.edi.length > 0) {
                    // Replace existing EDI file
                    mergerFiles.edi = [file];
                } else if (targetType === 'advice' && mergerFiles.advice.length > 0) {
                    // Replace existing Advice file
                    mergerFiles.advice = [file];
                } else {
                    mergerFiles[targetType].push(file);
                }
                
                updateMergerFileList(targetType);
            });
            
            // Show corrections if any
            if (corrections.length > 0) {
                showSmartCorrections(corrections);
            }
            
            updateMergerProcessButton();
        }

        // Show smart corrections
        function showSmartCorrections(corrections) {
            const correctionsList = document.getElementById('corrections-list');
            const correctionsContainer = document.getElementById('smart-corrections');
            
            correctionsList.innerHTML = corrections.map(correction => 
                `<div class="correction-item">✅ ${correction}</div>`
            ).join('');
            
            correctionsContainer.classList.add('show');
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                correctionsContainer.classList.remove('show');
            }, 5000);
        }

        // Update merger file lists
        function updateMergerFileList(type) {
            const fileList = document.getElementById(`${type}-files`);
            const uploadArea = document.getElementById(`${type}-upload`);
            const files = mergerFiles[type];
            
            if (files && files.length > 0) {
                uploadArea.classList.add('has-files');
                
                fileList.innerHTML = files.map((file, index) => `
                    <div class="file-item">
                        <div class="file-info">
                            <span class="file-name">${file.name}</span>
                            <span class="file-size">(${formatFileSize(file.size)})</span>
                        </div>
                        <button class="remove-btn" onclick="removeMergerFile('${type}', ${index})">Remove</button>
                    </div>
                `).join('');
            } else {
                uploadArea.classList.remove('has-files');
                fileList.innerHTML = '';
            }
        }

        // Remove merger file
        function removeMergerFile(type, index) {
            mergerFiles[type].splice(index, 1);
            updateMergerFileList(type);
            updateMergerProcessButton();
        }

        // Update merger process button state
        function updateMergerProcessButton() {
            const processBtn = document.getElementById('merger-process-btn');
            const hasEdi = mergerFiles.edi.length > 0;
            const hasAdvice = mergerFiles.advice.length > 0;
            const hasDocuments = mergerFiles.documents.length > 0;
            
            processBtn.disabled = !(hasEdi && (hasAdvice || hasDocuments));
        }

        // Start merger processing
        async function startMergerProcessing() {
            const progressContainer = document.getElementById('merger-progress');
            const progressFill = document.getElementById('merger-progress-fill');
            const progressText = document.getElementById('merger-progress-text');
            const processBtn = document.getElementById('merger-process-btn');
            
            processBtn.disabled = true;
            progressContainer.style.display = 'block';
            
            try {
                // Step 1: Upload files (25%)
                progressText.textContent = '📤 Uploading files...';
                progressFill.style.width = '25%';
                
                const formData = new FormData();
                
                // Add PDFs
                [...mergerFiles.advice, ...mergerFiles.documents].forEach(file => {
                    formData.append('pdfFiles', file);
                });
                
                // Add EDI file
                if (mergerFiles.edi.length > 0) {
                    formData.append('ediFile', mergerFiles.edi[0]);
                }
                
                const uploadResponse = await fetch('/api/merger/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!uploadResponse.ok) throw new Error('Upload failed');
                const uploadResult = await uploadResponse.json();
                
                // Step 2: Process manifest (50%)
                progressText.textContent = '📊 Processing EDI manifest...';
                progressFill.style.width = '50%';
                
                let manifestPath = null;
                if (uploadResult.files.ediFile) {
                    const manifestResponse = await fetch('/api/merger/process-manifest', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            ediFilePath: uploadResult.files.ediFile.path
                        })
                    });
                    
                    if (manifestResponse.ok) {
                        const manifestResult = await manifestResponse.json();
                        manifestPath = manifestResult.manifestPath;
                    }
                }
                
                // Step 3: Merge documents with page 9 overlays (75%)
                progressText.textContent = '🚢 Merging documents and applying page 9 overlays...';
                progressFill.style.width = '75%';
                
                const mergeResponse = await fetch('/api/merger/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        files: uploadResult.files,
                        manifestPath: manifestPath,
                        settings: {
                            applyPage9Overlays: true,
                            namingFormat: 'name_ref',
                            pageOrder: 'advice_bill_customer'
                        }
                    })
                });
                
                if (!mergeResponse.ok) throw new Error('Merging failed');
                const mergeResult = await mergeResponse.json();
               
                // Add these debugging lines:
                console.log('🔍 Full merge result:', mergeResult);
                console.log('🔍 Download URL:', mergeResult.downloadUrl);
                console.log('🔍 Stats object:', mergeResult.stats);
                console.log('🔍 Job ID:', mergeResult.jobId);
                
                // Complete (100%)
                progressText.textContent = '✅ Processing complete!';
                progressFill.style.width = '100%';
                
                showMergerResults(mergeResult);
                
            } catch (error) {
                progressText.textContent = `❌ Error: ${error.message}`;
                console.error('Merger processing failed:', error);
            } finally {
                processBtn.disabled = false;
            }
        }
        // Add this NEW function
        function displayTaxAlerts(taxAlerts) {
            if (!taxAlerts || taxAlerts.length === 0) {
                return ''; // No alerts to show
            }
            
            let alertHtml = `
                <div style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="color: #856404; margin-top: 0; display: flex; align-items: center;">
                        🚨 Tax Alert Summary
                    </h3>
                    <p style="margin: 10px 0;"><strong>${taxAlerts.length} client(s) flagged for customs review</strong></p>
            `;
            
            taxAlerts.forEach(alert => {
                alertHtml += `
                    <div style="border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; background: white; border-radius: 4px;">
                        <strong style="color: #856404;">${alert.client_name}</strong> 
                        <span style="color: #6c757d;">(${alert.client_ref})</span>
                        <ul style="margin: 8px 0; padding-left: 20px;">`;
                
                alert.alerts.forEach(item => {
                    alertHtml += `<li style="margin: 4px 0;"><strong>${item.keyword}</strong> found on page ${item.page}</li>`;
                });
                
                alertHtml += `</ul></div>`;
            });
            
            alertHtml += `</div>`;
            return alertHtml;
        }

        function showMergerResults(result) {
            const resultsDiv = document.getElementById('merger-results');
            const resultsContent = document.getElementById('merger-results-content');
            
            // Add fallback values with debugging
            const clientCount = result.stats?.merged_clients || 0;
            
            // Build the results HTML
            let resultsHtml = `
                <h3>✅ Merger Complete!</h3>
                <p>Successfully merged documents for ${clientCount} clients</p>
                <p>All documents include page 9 overlays with container/ship information</p>
                <a href="${result.downloadUrl}" class="btn btn-success" download>📥 Download Merged Documents</a>
            `;
            
            // ADD TAX ALERTS HERE
            if (result.tax_alerts) {
                resultsHtml += displayTaxAlerts(result.tax_alerts);
            }
            
            resultsContent.innerHTML = resultsHtml;
            resultsDiv.className = 'results success';
            resultsDiv.style.display = 'block';
        }

        // ==================== UTILITY FUNCTIONS ====================
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            initProcessorUploads();
            initMergerUploads();
            console.log('🚀 PDF Tools Suite initialized!');
        });
    </script>
</body>
</html>
