
const { spawn } = require('child_process');
const { performance } = require('perf_hooks');
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs-extra');
const cors = require('cors');
const archiver = require('archiver');
const { v4: uuidv4 } = require('uuid');
const cron = require('node-cron');
const winston = require('winston');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { PythonShell } = require('python-shell');
const XLSX = require('xlsx');
const csv = require('csv-parser');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;

// Import your text overlay processor
const TextOverlayProcessor = require('./textOverlay.js');

const app = express();
const PORT = process.env.PORT || 3000;

// Constants
const SIGNATURE_PATH = './signatures/default-signature.png';

// Simple Performance Monitor Class (keeping your existing implementation)
class SimplePerformanceMonitor {
    constructor() {
        this.metrics = {
            totalRequests: 0,
            successfulRequests: 0,
            failedRequests: 0,
            totalProcessingTime: 0,
            averageProcessingTime: 0,
            mergerJobs: 0,
            formProcessorJobs: 0,
            startTime: Date.now(),
            errors: []
        };
        
        this.activeJobs = new Map();
    }
    
    startJob(jobType, jobId, details = {}) {
        const job = {
            type: jobType,
            id: jobId,
            startTime: performance.now(),
            details,
            status: 'running'
        };
        
        this.activeJobs.set(jobId, job);
        console.log(`📊 Started ${jobType} job: ${jobId}`);
        
        return job;
    }
    
    completeJob(jobId, result = {}) {
        const job = this.activeJobs.get(jobId);
        if (!job) return null;
        
        const duration = performance.now() - job.startTime;
        job.duration = duration;
        job.status = 'completed';
        job.result = result;
        
        this.metrics.totalRequests++;
        this.metrics.successfulRequests++;
        this.metrics.totalProcessingTime += duration;
        this.metrics.averageProcessingTime = this.metrics.totalProcessingTime / this.metrics.successfulRequests;
        
        if (job.type === 'merger') {
            this.metrics.mergerJobs++;
        } else if (job.type === 'form-processor') {
            this.metrics.formProcessorJobs++;
        }
        
        this.activeJobs.delete(jobId);
        
        console.log(`✅ Completed ${job.type} job: ${jobId} (${duration.toFixed(2)}ms)`);
        return job;
    }
    
    failJob(jobId, error) {
        const job = this.activeJobs.get(jobId);
        if (!job) return null;
        
        const duration = performance.now() - job.startTime;
        job.duration = duration;
        job.status = 'failed';
        job.error = error.message || error;
        
        this.metrics.totalRequests++;
        this.metrics.failedRequests++;
        
        this.metrics.errors.push({
            jobId,
            type: job.type,
            error: job.error,
            timestamp: new Date().toISOString()
        });
        
        if (this.metrics.errors.length > 50) {
            this.metrics.errors = this.metrics.errors.slice(-50);
        }
        
        this.activeJobs.delete(jobId);
        
        console.log(`❌ Failed ${job.type} job: ${jobId} - ${job.error}`);
        return job;
    }
    
    getMetrics() {
        const uptime = Date.now() - this.metrics.startTime;
        const successRate = this.metrics.totalRequests > 0 ? 
            (this.metrics.successfulRequests / this.metrics.totalRequests * 100).toFixed(2) : 0;
        
        return {
            ...this.metrics,
            uptime: uptime,
            uptimeHours: (uptime / (1000 * 60 * 60)).toFixed(2),
            successRate: `${successRate}%`,
            activeJobs: this.activeJobs.size,
            currentTime: new Date().toISOString()
        };
    }
    
    getHealthStatus() {
        const metrics = this.getMetrics();
        const recentErrors = this.metrics.errors.filter(
            error => Date.now() - new Date(error.timestamp).getTime() < 60000
        );
        
        const isHealthy = recentErrors.length === 0 && parseFloat(metrics.successRate) > 95;
        
        return {
            status: isHealthy ? 'healthy' : 'degraded',
            uptime: metrics.uptimeHours + ' hours',
            successRate: metrics.successRate,
            activeJobs: metrics.activeJobs,
            recentErrors: recentErrors.length,
            lastCheck: new Date().toISOString()
        };
    }
}

// Create global performance monitor
const performanceMonitor = new SimplePerformanceMonitor();

// Enhanced logging
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    transports: [
        new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
        new winston.transports.File({ filename: 'logs/combined.log' }),
        new winston.transports.Console({
            format: winston.format.simple()
        })
    ]
});

// Security and performance middleware
app.use(helmet({
    contentSecurityPolicy: false
}));
app.use(compression());
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100
});
app.use('/api/', limiter);

// Ensure directories exist
const ensureDirectories = async () => {
    const dirs = [
        'uploads', 'outputs', 'signatures', 'logs', 
        'merger-uploads', 'merger-outputs', 'manifests'
    ];
    
    for (const dir of dirs) {
        await fs.ensureDir(dir);
    }
};

// Check signature file
const ensureSignature = async () => {
    if (!await fs.pathExists(SIGNATURE_PATH)) {
        logger.warn(`⚠️  Default signature not found at: ${SIGNATURE_PATH}`);
        console.log('📝 Place your signature image at:', SIGNATURE_PATH);
        console.log('💡 Supported formats: PNG, JPG, GIF');
    } else {
        logger.info('✅ Default signature loaded');
        console.log('✅ Default signature found');
    }
};

// Configure multer for different file types
const createMulterStorage = (destination) => {
    return multer({
        storage: multer.diskStorage({
            destination: (req, file, cb) => {
                cb(null, destination);
            },
            filename: (req, file, cb) => {
                const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
                cb(null, uniqueSuffix + '-' + file.originalname);
            }
        }),
        limits: {
            fileSize: 100 * 1024 * 1024 // 100MB limit
        },
        fileFilter: (req, file, cb) => {
            const allowedTypes = /\.(pdf|xls|xlsx|png|jpg|jpeg|gif)$/i;
            if (allowedTypes.test(file.originalname)) {
                cb(null, true);
            } else {
                cb(new Error('Only PDF, Excel, and image files are allowed'));
            }
        }
    });
};

const uploadProcessor = createMulterStorage('uploads');
const uploadMerger = createMulterStorage('merger-uploads');

// Serve static files
app.use(express.static('public'));

// ==================== FORM PROCESSOR ROUTES ====================

// Form processor upload endpoint
app.post('/api/upload', uploadProcessor.array('files'), async (req, res) => {
    try {
        logger.info(`Form processor upload: ${req.files.length} files`);
        
        const processedFiles = req.files.map(file => ({
            id: uuidv4(),
            originalName: file.originalname,
            filename: file.filename,
            path: file.path,
            size: file.size
        }));

        // Check if signature exists
        const signatureExists = await fs.pathExists(SIGNATURE_PATH);

        res.json({
            success: true,
            files: processedFiles,
            signatureAvailable: signatureExists,
            message: `Uploaded ${req.files.length} files successfully`
        });
    } catch (error) {
        logger.error('Upload error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Form processor process endpoint - NOW PROPERLY INTEGRATED
app.post('/api/process', async (req, res) => {
    const trackingJobId = `form_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const job = performanceMonitor.startJob('form-processor', trackingJobId, {
        fileCount: req.body.files?.length || 0,
        overlays: req.body.overlays?.length || 0
    });

    try {
        const { files, overlays, settings } = req.body;
        logger.info(`Processing ${files.length} files with form overlay`);

        const jobId = uuidv4();
        const outputDir = path.join('outputs', jobId);
        await fs.ensureDir(outputDir);

        // Initialize the text overlay processor
        const processor = new TextOverlayProcessor();
        
        // Configure overlays if provided
        if (overlays && overlays.length > 0) {
            // Convert frontend overlay format to processor format
            const overlayConfig = overlays.map(overlay => ({
                name: overlay.name || 'customOverlay',
                x: overlay.x || 100,
                y: overlay.y || 100,
                text: overlay.text || '',
                description: overlay.description || 'Custom overlay'
            }));
            
            // Update processor overlay configuration
            processor.overlayConfig.fields = overlayConfig;
        }

        // Copy uploaded files to a temporary processing directory
        const tempInputDir = path.join('uploads', 'temp_' + jobId);
        await fs.ensureDir(tempInputDir);

        const processedFiles = [];
        for (const file of files) {
            const originalPath = path.join('uploads', file.filename || file.originalName);
            const tempPath = path.join(tempInputDir, file.originalName);
            
            if (await fs.pathExists(originalPath)) {
                await fs.copy(originalPath, tempPath);
                processedFiles.push({
                    originalName: file.originalName,
                    tempPath: tempPath
                });
            }
        }

        // Process the PDFs using your existing textOverlay processor
        const result = await processor.processBatch(tempInputDir, outputDir);

        // Clean up temporary directory
        await fs.remove(tempInputDir);

        // Complete the performance tracking
        const completedJob = performanceMonitor.completeJob(trackingJobId, result);

        res.json({
            success: true,
            jobId: jobId,
            processedFiles: result.successFiles || processedFiles,
            downloadUrl: `/api/download/${jobId}`,
            performance: {
                duration: completedJob.duration,
                filesPerSecond: (result.successful || 0) / (completedJob.duration / 1000)
            },
            stats: {
                processed: result.processed || 0,
                successful: result.successful || 0,
                failed: result.failed || 0
            }
        });

    } catch (error) {
        performanceMonitor.failJob(trackingJobId, error);
        logger.error('Form processing error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// ==================== DOCUMENT MERGER ROUTES ====================

// Upload files for merger
app.post('/api/merger/upload', uploadMerger.fields([
    { name: 'pdfFiles', maxCount: 50 },
    { name: 'ediFile', maxCount: 1 },
    { name: 'referenceDoc', maxCount: 1 }
]), async (req, res) => {
    try {
        logger.info('Merger upload request received');
        
        const uploadedFiles = {
            pdfFiles: [],
            ediFile: null,
            referenceDoc: null
        };

        if (req.files.pdfFiles) {
            uploadedFiles.pdfFiles = req.files.pdfFiles.map(file => ({
                id: uuidv4(),
                originalName: file.originalname,
                filename: file.filename,
                path: file.path,
                size: file.size
            }));
        }

        if (req.files.ediFile && req.files.ediFile[0]) {
            const file = req.files.ediFile[0];
            uploadedFiles.ediFile = {
                id: uuidv4(),
                originalName: file.originalname,
                filename: file.filename,
                path: file.path,
                size: file.size
            };
        }

        if (req.files.referenceDoc && req.files.referenceDoc[0]) {
            const file = req.files.referenceDoc[0];
            uploadedFiles.referenceDoc = {
                id: uuidv4(),
                originalName: file.originalname,
                filename: file.filename,
                path: file.path,
                size: file.size
            };
        }

        logger.info(`Merger upload successful: ${uploadedFiles.pdfFiles.length} PDFs, EDI: ${!!uploadedFiles.ediFile}`);

        res.json({
            success: true,
            files: uploadedFiles,
            message: 'Files uploaded successfully for merger'
        });

    } catch (error) {
        logger.error('Merger upload error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Process manifest from uploaded files
app.post('/api/merger/process-manifest', async (req, res) => {
    try {
        const { ediFilePath, referenceDocPath } = req.body;
        logger.info('Processing manifest from uploaded files');

        let manifest = {};

        if (ediFilePath && await fs.pathExists(ediFilePath)) {
            manifest = await processEdiFile(ediFilePath);
        } else if (referenceDocPath && await fs.pathExists(referenceDocPath)) {
            manifest = await processReferenceDocument(referenceDocPath);
        }

        const manifestId = uuidv4();
        const manifestPath = path.join('manifests', `manifest_${manifestId}.csv`);
        await saveManifestAsCsv(manifest, manifestPath);

        res.json({
            success: true,
            manifest: manifest,
            manifestId: manifestId,
            manifestPath: manifestPath,
            count: Object.keys(manifest).length
        });

    } catch (error) {
        logger.error('Manifest processing error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});



// Download merged files
app.get('/api/merger/download/:jobId', async (req, res) => {
    try {
        const { jobId } = req.params;
        const outputDir = path.join('merger-outputs', jobId);

        if (!await fs.pathExists(outputDir)) {
            return res.status(404).json({ error: 'Job not found' });
        }

        const zipPath = path.join('merger-outputs', `${jobId}_merged.zip`);
        const output = fs.createWriteStream(zipPath);
        const archive = archiver('zip', { zlib: { level: 9 } });

        archive.pipe(output);

        const files = await fs.readdir(outputDir);
        const pdfFiles = files.filter(file => file.endsWith('.pdf'));

        for (const file of pdfFiles) {
            const filePath = path.join(outputDir, file);
            archive.file(filePath, { name: file });
        }

        await archive.finalize();
        await new Promise((resolve) => output.on('close', resolve));

        res.download(zipPath, `merged_documents_${jobId}.zip`, (err) => {
            if (err) {
                logger.error('Download error:', err);
            }
            fs.remove(zipPath).catch(console.error);
        });

    } catch (error) {
        logger.error('Download error:', error);
        res.status(500).json({ error: error.message });
    }
});

// Add this new endpoint after your existing /api/merger/process endpoint in server.js

// Main merger processing endpoint with page 9 overlays
app.post('/api/merger/process', async (req, res) => {
    const trackingJobId = `merger_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const job = performanceMonitor.startJob('merger', trackingJobId, {
        fileCount: req.body.files?.pdfFiles?.length || 0,
        hasEdi: !!req.body.files?.ediFile,
        settings: req.body.settings,
        applyOverlays: req.body.settings?.applyPage9Overlays || false
    });
    
    try {
        const { files, settings, manifestPath } = req.body;
        logger.info(`Starting enhanced merger process with ${files.pdfFiles?.length || 0} PDF files`);

        const jobId = uuidv4();
        const outputDir = path.join('merger-outputs', jobId);
        const tempOverlayDir = path.join('outputs', `overlay_${jobId}`);
        
        await fs.ensureDir(outputDir);
        await fs.ensureDir(tempOverlayDir);

        // Step 1: Run Python merger first
        const pythonOptions = {
            mode: 'text',
            pythonPath: '/Users/matthewforan/SevenSeas_Code_Project/pdf-tools-suite-1/.venv/bin/python',
            scriptPath: path.join(__dirname, 'python-scripts'),
            args: [
                '--input-folder', 'merger-uploads',
                '--output-folder', outputDir,
                '--job-id', jobId,
                '--json-output'
            ]
        };

        if (manifestPath && await fs.pathExists(manifestPath)) {
            pythonOptions.args.push('--manifest-file', manifestPath);
        }

        // Add EDI file if exists
        if (files.ediFile && await fs.pathExists(files.ediFile.path)) {
            pythonOptions.args.push('--edi-file', files.ediFile.path);
        }

      logger.info('Running Python merger with child_process...');

        const pythonArgs = [
            'python-scripts/pdf_merger.py',
            '--input-folder', 'merger-uploads',
            '--output-folder', outputDir,
            '--job-id', jobId,
            '--json-output'
        ];

        if (manifestPath && await fs.pathExists(manifestPath)) {
            pythonArgs.push('--manifest-file', manifestPath);
        }

        if (files.ediFile && await fs.pathExists(files.ediFile.path)) {
            pythonArgs.push('--edi-file', files.ediFile.path);
        }

        logger.info('Python command:', pythonArgs.join(' '));

        const mergerResults = await new Promise((resolve, reject) => {
            const python = spawn('./.venv/bin/python', pythonArgs);
            
            let stdout = '';
            let stderr = '';
            
            python.stdout.on('data', (data) => {
                const output = data.toString();
                stdout += output;
                logger.info('Python stdout:', output.trim());
            });
            
            python.stderr.on('data', (data) => {
                const error = data.toString();
                stderr += error;
                logger.error('Python stderr:', error.trim());
            });
            
            python.on('close', (code) => {
                logger.info(`Python process finished with code: ${code}`);
                
                if (code !== 0) {
                    reject(new Error(`Python script failed with code ${code}: ${stderr}`));
                } else {
                    // Find JSON output in stdout
                    const lines = stdout.split('\n');
                    const jsonLine = lines.find(line => line.trim().startsWith('{'));
                    
                    if (jsonLine) {
                        try {
                            const result = JSON.parse(jsonLine);
                            logger.info('Parsed Python result:', result);
                            resolve(result);
                        } catch (e) {
                            logger.error('JSON parse error:', e);
                            resolve({ success: true, message: 'Completed but parse failed' });
                        }
                    } else {
                        logger.warning('No JSON output found');
                        resolve({ success: true, message: 'Completed successfully' });
                    }
                }
            });
            
            // Add timeout
            setTimeout(() => {
                python.kill();
                reject(new Error('Python process timeout'));
            }, 5 * 60 * 1000); // 5 minute timeout
        });

        // Step 2: Apply page 9 overlays if requested
        if (settings?.applyPage9Overlays) {
            logger.info('Applying page 9 overlays to merged documents...');
            
            // Get all merged PDF files
            const mergedFiles = await fs.readdir(outputDir);
            const pdfFiles = mergedFiles.filter(file => file.endsWith('.pdf'));
            
            if (pdfFiles.length > 0) {
                // Initialize text overlay processor
                // Remove this line:
            // const TextOverlayProcessor = require('./textOverlay.js');

            // And replace with (since you already imported it at the top):
            const overlayProcessor = new TextOverlayProcessor();
                
                // Extract shipment data from the first PDF file
                const firstPdfPath = path.join(outputDir, pdfFiles[0]);
                await overlayProcessor.extractShipmentData(firstPdfPath);
                
                if (overlayProcessor.shipmentData) {
                    logger.info(`Extracted shipment data: Container ${overlayProcessor.shipmentData.containerNumber}, Ship ${overlayProcessor.shipmentData.shipName}`);
                    
                    // Process each merged PDF with overlays
                    for (const pdfFile of pdfFiles) {
                        const inputPath = path.join(outputDir, pdfFile);
                        const tempPath = path.join(tempOverlayDir, pdfFile);
                        
                        logger.info(`Applying overlays to: ${pdfFile}`);
                        
                         const overlayResult = await overlayProcessor.processSinglePDFWithOverlay(inputPath, tempPath);
                        
                        if (overlayResult.success) {
                            // Replace original with overlay version
                            await fs.move(tempPath, inputPath, { overwrite: true });
                            logger.info(`✅ Applied overlays to ${pdfFile}`);
                        } else {
                            logger.warning(`⚠️ Failed to apply overlays to ${pdfFile}: ${overlayResult.error}`);
                        }
                    }
                    
                    mergerResults.overlaysApplied = pdfFiles.length;
                    mergerResults.shipmentData = overlayProcessor.shipmentData;
                } else {
                    logger.warning('Could not extract shipment data for overlays');
                    mergerResults.overlaysApplied = 0;
                }
            }
        }

        // Clean up temp overlay directory
        await fs.remove(tempOverlayDir);

        mergerResults.jobId = jobId;
        mergerResults.downloadUrl = `/api/merger/download/${jobId}`;

        logger.info(`Enhanced merger processing completed for job ${jobId}`);

        const completedJob = performanceMonitor.completeJob(trackingJobId, mergerResults);
        
        res.json({
            success: true,
            jobId: jobId,
            downloadUrl: `/api/merger/download/${jobId}`,
            stats: {
                merged_clients: mergerResults.stats?.merged_clients || mergerResults.merged_clients || 0,
                processed_files: mergerResults.stats?.processed_files || mergerResults.processed_files || 0,
                overlays_applied: mergerResults.overlaysApplied || 0
            },
            performance: {
                duration: completedJob.duration,
                filesPerSecond: (mergerResults.stats?.processed_files || mergerResults.stats?.processed || 0) / (completedJob.duration / 1000)
            },
            originalResults: mergerResults  // Keep full results for debugging
        });

    } catch (error) {
        performanceMonitor.failJob(trackingJobId, error);
        logger.error('Enhanced merger processing error:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message,
            jobId: trackingJobId
        });
    }
});

// ==================== SHARED ROUTES ====================

// Download processed files
app.get('/api/download/:jobId', async (req, res) => {
    try {
        const { jobId } = req.params;
        const outputDir = path.join('outputs', jobId);

        if (!await fs.pathExists(outputDir)) {
            return res.status(404).json({ error: 'Job not found' });
        }

        const zipPath = path.join('outputs', `${jobId}_processed.zip`);
        const output = fs.createWriteStream(zipPath);
        const archive = archiver('zip', { zlib: { level: 9 } });

        archive.pipe(output);
        archive.directory(outputDir, false);
        await archive.finalize();

        await new Promise((resolve) => output.on('close', resolve));

        res.download(zipPath, `processed_files_${jobId}.zip`, (err) => {
            if (err) {
                logger.error('Download error:', err);
            }
            fs.remove(zipPath).catch(console.error);
        });

    } catch (error) {
        logger.error('Download error:', error);
        res.status(500).json({ error: error.message });
    }
});

// ==================== MONITORING ENDPOINTS ====================

app.get('/api/metrics', (req, res) => {
    try {
        const metrics = performanceMonitor.getMetrics();
        res.json({
            success: true,
            metrics: metrics
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Add these new routes to your server.js after your existing routes

// ==================== SMART UPLOAD ROUTES ====================

// Serve the smart interface as an alternative
app.get('/smart', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'smart.html'));
});

// Smart file analysis endpoint
app.post('/api/smart-analyze', uploadProcessor.array('files'), async (req, res) => {
    try {
        logger.info(`Smart analysis: ${req.files.length} files`);
        
        const analysis = {
            torForms: [],
            adviceDocuments: [],
            billsOfLading: [],
            customerDocuments: [],
            ediFiles: [],
            signatures: [],
            unknownPdfs: [],
            processingMode: null,
            recommendations: []
        };

        // Analyze each uploaded file
        for (const file of req.files) {
            const fileInfo = {
                id: uuidv4(),
                originalName: file.originalname,
                filename: file.filename,
                path: file.path,
                size: file.size,
                type: detectFileType(file.originalname)
            };

            // Categorize files
            switch (fileInfo.type) {
                case 'tor_form':
                    analysis.torForms.push(fileInfo);
                    break;
                case 'advice_document':
                    analysis.adviceDocuments.push(fileInfo);
                    break;
                case 'bill_of_lading':
                    analysis.billsOfLading.push(fileInfo);
                    break;
                case 'customer_document':
                    analysis.customerDocuments.push(fileInfo);
                    break;
                case 'edi_file':
                    analysis.ediFiles.push(fileInfo);
                    break;
                case 'signature':
                    analysis.signatures.push(fileInfo);
                    break;
                default:
                    analysis.unknownPdfs.push(fileInfo);
            }
        }

        // Determine processing mode
        const hasShippingDocs = analysis.adviceDocuments.length + analysis.billsOfLading.length + analysis.customerDocuments.length > 0;
        const hasTorForms = analysis.torForms.length > 0;

        if (hasTorForms && hasShippingDocs) {
            analysis.processingMode = 'combined';
            analysis.recommendations.push('Process TOR forms and merge shipping documents');
        } else if (hasTorForms) {
            analysis.processingMode = 'form_processing';
            analysis.recommendations.push('Add text overlays to TOR forms');
        } else if (hasShippingDocs) {
            analysis.processingMode = 'document_merging';
            analysis.recommendations.push('Merge shipping documents by client');
        } else {
            analysis.processingMode = 'unknown';
            analysis.recommendations.push('Manual classification required');
        }

        // Store analysis for later processing
        const analysisId = uuidv4();
        const analysisPath = path.join('manifests', `analysis_${analysisId}.json`);
        await fs.writeJson(analysisPath, analysis);

        res.json({
            success: true,
            analysis: analysis,
            analysisId: analysisId,
            message: `Analyzed ${req.files.length} files successfully`
        });

    } catch (error) {
        logger.error('Smart analysis error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Smart auto-processing endpoint
app.post('/api/smart-process', async (req, res) => {
    const trackingJobId = `smart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const job = performanceMonitor.startJob('smart-processor', trackingJobId);

    try {
        const { analysisId, settings } = req.body;
        
        // Load the analysis
        const analysisPath = path.join('manifests', `analysis_${analysisId}.json`);
        if (!await fs.pathExists(analysisPath)) {
            throw new Error('Analysis not found');
        }
        
        const analysis = await fs.readJson(analysisPath);
        logger.info(`Smart processing: ${analysis.processingMode} mode`);

        const results = {};
        const jobId = uuidv4();

        // Process TOR forms if any
        if (analysis.torForms.length > 0) {
            logger.info(`Processing ${analysis.torForms.length} TOR forms`);
            
            const formJobId = `forms_${jobId}`;
            const formOutputDir = path.join('outputs', formJobId);
            await fs.ensureDir(formOutputDir);

            // Initialize text overlay processor
            const processor = new TextOverlayProcessor();
            
            // Create temporary input directory
            const tempInputDir = path.join('uploads', 'temp_forms_' + formJobId);
            await fs.ensureDir(tempInputDir);

            // Copy TOR form files to temp directory
            for (const torForm of analysis.torForms) {
                const sourcePath = torForm.path;
                const destPath = path.join(tempInputDir, torForm.originalName);
                if (await fs.pathExists(sourcePath)) {
                    await fs.copy(sourcePath, destPath);
                }
            }

            // Process the forms
            const formResult = await processor.processBatch(tempInputDir, formOutputDir);
            
            // Clean up temp directory
            await fs.remove(tempInputDir);
            
            results.formProcessing = {
                success: true,
                jobId: formJobId,
                downloadUrl: `/api/download/${formJobId}`,
                stats: formResult
            };
        }

        // Process document merging if needed
        if (analysis.adviceDocuments.length + analysis.billsOfLading.length + analysis.customerDocuments.length > 0) {
            logger.info('Processing document merging');
            
            const mergerJobId = `merger_${jobId}`;
            const mergerOutputDir = path.join('merger-outputs', mergerJobId);
            await fs.ensureDir(mergerOutputDir);

            // Copy relevant files to merger-uploads
            const mergerInputDir = path.join('merger-uploads', 'temp_' + mergerJobId);
            await fs.ensureDir(mergerInputDir);

            // Copy shipping documents
            const allShippingDocs = [
                ...analysis.adviceDocuments,
                ...analysis.billsOfLading,
                ...analysis.customerDocuments
            ];

            for (const doc of allShippingDocs) {
                if (await fs.pathExists(doc.path)) {
                    await fs.copy(doc.path, path.join(mergerInputDir, doc.originalName));
                }
            }

            // Copy EDI file if exists
            let ediPath = null;
            if (analysis.ediFiles.length > 0) {
                const ediFile = analysis.ediFiles[0];
                ediPath = path.join(mergerInputDir, ediFile.originalName);
                if (await fs.pathExists(ediFile.path)) {
                    await fs.copy(ediFile.path, ediPath);
                }
            }

            // Run Python merger
            const pythonOptions = {
                mode: 'text',
                pythonPath: '/Users/matthewforan/SevenSeas_Code_Project/pdf-tools-suite-1/.venv/bin/python',
                scriptPath: path.join(__dirname, 'python-scripts'),
                args: [
                    '--input-folder', mergerInputDir,
                    '--output-folder', mergerOutputDir,
                    '--job-id', mergerJobId,
                    '--json-output'
                ]
            };

            if (ediPath) {
                pythonOptions.args.push('--edi-file', ediPath);
            }

            const mergerResults = await new Promise((resolve, reject) => {
                PythonShell.run('pdf_merger.py', pythonOptions, (err, results) => {
                    if (err) {
                        logger.error('Python merger error:', err);
                        reject(err);
                    } else {
                        try {
                            const lastLine = results[results.length - 1];
                            const result = JSON.parse(lastLine);
                            resolve(result);
                        } catch (parseErr) {
                            logger.error('Failed to parse merger results:', parseErr);
                            resolve({
                                success: true,
                                message: 'Merging completed, but could not parse detailed results'
                            });
                        }
                    }
                });
            });

            // Clean up temp directory
            await fs.remove(mergerInputDir);

            results.documentMerging = {
                success: true,
                jobId: mergerJobId,
                downloadUrl: `/api/merger/download/${mergerJobId}`,
                stats: mergerResults
            };
        }

        // Complete tracking
        const completedJob = performanceMonitor.completeJob(trackingJobId, results);

        res.json({
            success: true,
            results: results,
            processingMode: analysis.processingMode,
            performance: {
                duration: completedJob.duration,
                mode: analysis.processingMode
            },
            downloadUrls: generateDownloadUrls(results)
        });

    } catch (error) {
        performanceMonitor.failJob(trackingJobId, error);
        logger.error('Smart processing error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Generate download URLs based on processing results
function generateDownloadUrls(results) {
    const urls = [];
    
    if (results.formProcessing && results.formProcessing.success) {
        urls.push({
            type: 'Form Processing Results',
            url: results.formProcessing.downloadUrl,
            description: 'TOR forms with text overlays'
        });
    }
    
    if (results.documentMerging && results.documentMerging.success) {
        urls.push({
            type: 'Merged Documents',
            url: results.documentMerging.downloadUrl,
            description: 'Shipping documents merged by client'
        });
    }
    
    return urls;
}

// File type detection utility
function detectFileType(filename) {
    const name = filename.toLowerCase();
    
    if (name.includes('tor') || name.includes('declaration')) {
        return 'tor_form';
    } else if (name.includes('advice') || name.includes('arrival')) {
        return 'advice_document';
    } else if (name.includes('bill') || name.includes('lading')) {
        return 'bill_of_lading';
    } else if (name.endsWith('.xls') || name.endsWith('.xlsx')) {
        return 'edi_file';
    } else if (/\d{3}[-\/]\d{3}[-\/]\d{3}/.test(name)) {
        return 'customer_document';
    } else if (name.endsWith('.png') || name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.gif')) {
        return 'signature';
    } else if (name.endsWith('.pdf')) {
        return 'unknown_pdf';
    }
    
    return 'unknown';
}

// Health check endpoint specifically for smart mode
app.get('/api/smart/health', (req, res) => {
    try {
        const health = performanceMonitor.getHealthStatus();
        const signatureExists = fs.existsSync(SIGNATURE_PATH);
        
        res.json({
            ...health,
            smartMode: {
                status: 'active',
                features: [
                    'Auto file detection',
                    'Smart processing mode selection',
                    'Combined form processing and document merging'
                ]
            },
            services: {
                formProcessor: 'active',
                documentMerger: 'active',
                signature: signatureExists ? 'available' : 'missing',
                smartAnalysis: 'active'
            }
        });
    } catch (error) {
        res.status(500).json({ 
            status: 'error', 
            error: error.message 
        });
    }
});

app.get('/api/health', (req, res) => {
    try {
        const health = performanceMonitor.getHealthStatus();
        const signatureExists = fs.existsSync(SIGNATURE_PATH);
        
        res.json({
            ...health,
            services: {
                formProcessor: 'active',
                documentMerger: 'active',
                signature: signatureExists ? 'available' : 'missing'
            }
        });
    } catch (error) {
        res.status(500).json({ 
            status: 'error', 
            error: error.message 
        });
    }
});

app.get('/api/system-info', (req, res) => {
    try {
        const metrics = performanceMonitor.getMetrics();
        
        res.json({
            application: {
                name: 'PDF Tools Suite',
                version: '2.0.0',
                uptime: metrics.uptimeHours + ' hours',
                startTime: new Date(metrics.startTime).toISOString()
            },
            performance: {
                totalRequests: metrics.totalRequests,
                successfulRequests: metrics.successfulRequests,
                failedRequests: metrics.failedRequests,
                successRate: metrics.successRate,
                averageProcessingTime: metrics.averageProcessingTime.toFixed(2) + 'ms'
            },
            jobs: {
                mergerJobs: metrics.mergerJobs,
                formProcessorJobs: metrics.formProcessorJobs,
                activeJobs: metrics.activeJobs
            },
            system: {
                memoryUsage: process.memoryUsage(),
                platform: process.platform,
                nodeVersion: process.version,
                currentTime: new Date().toISOString()
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.get('/api/info', (req, res) => {
    res.json({
        name: 'PDF Processor & Merger Suite',
        version: '2.0.0',
        features: [
            'PDF Form Filling',
            'Document Merging',
            'Batch Processing',
            'Manifest Management'
        ]
    });
});

// ==================== UTILITY FUNCTIONS ====================

async function processEdiFile(filePath) {
    try {
        const workbook = XLSX.readFile(filePath);
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const data = XLSX.utils.sheet_to_json(worksheet);

        const manifest = {};
        
        data.forEach(row => {
            const consigneeRef = row['Consignees Reference'] || row['Reference'];
            const consigneeName = row['Consignees Name'] || row['Name'];
            
            if (consigneeRef && consigneeName) {
                manifest[consigneeRef.toString().trim()] = consigneeName.toString().trim();
            }
        });

        logger.info(`Processed EDI file: ${Object.keys(manifest).length} entries`);
        return manifest;

    } catch (error) {
        logger.error('EDI processing error:', error);
        throw error;
    }
}

async function processReferenceDocument(filePath) {
    logger.info('Reference document processing not yet implemented');
    return {};
}

async function saveManifestAsCsv(manifest, filePath) {
    const csvWriter = createCsvWriter({
        path: filePath,
        header: [
            { id: 'reference', title: 'ConsigneeRef' },
            { id: 'name', title: 'FullName' }
        ]
    });

    const records = Object.entries(manifest).map(([ref, name]) => ({
        reference: ref,
        name: name
    }));

    await csvWriter.writeRecords(records);
    logger.info(`Manifest saved to ${filePath} with ${records.length} entries`);
}

// Cleanup old files (daily at 2 AM)
cron.schedule('0 2 * * *', async () => {
    logger.info('Starting daily cleanup');
    
    const cleanupDirs = ['uploads', 'outputs', 'merger-uploads', 'merger-outputs'];
    const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
    
    for (const dir of cleanupDirs) {
        try {
            if (await fs.pathExists(dir)) {
                const files = await fs.readdir(dir);
                for (const file of files) {
                    const filePath = path.join(dir, file);
                    const stats = await fs.stat(filePath);
                    
                    if (Date.now() - stats.mtime.getTime() > maxAge) {
                        await fs.remove(filePath);
                        logger.info(`Cleaned up old file: ${filePath}`);
                    }
                }
            }
        } catch (error) {
            logger.error(`Cleanup error for ${dir}:`, error);
        }
    }
});

// ==================== START SERVER ====================

async function startServer() {
    try {
        await ensureDirectories();
        await ensureSignature();
        
        app.listen(PORT, () => {
            logger.info(`🚀 PDF Processor & Merger Suite running on port ${PORT}`);
            logger.info(`📋 Form Processor: http://localhost:${PORT}`);
            logger.info(`🚢 Document Merger: http://localhost:${PORT}#merger`);
            logger.info(`📊 Health Check: http://localhost:${PORT}/api/health`);
            console.log('✅ Server ready!');
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();

module.exports = app;
