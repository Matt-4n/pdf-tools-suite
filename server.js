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

// Main merger processing endpoint
app.post('/api/merger/process', async (req, res) => {
    const trackingJobId = `merger_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const job = performanceMonitor.startJob('merger', trackingJobId, {
        fileCount: req.body.files?.pdfFiles?.length || 0,
        hasEdi: !!req.body.ediFile,
        settings: req.body.settings
    });
    
    try {
        const { files, settings, manifestPath } = req.body;
        logger.info(`Starting merger process with ${files.pdfFiles?.length || 0} PDF files`);

        const jobId = uuidv4();
        const outputDir = path.join('merger-outputs', jobId);
        await fs.ensureDir(outputDir);

        const pythonOptions = {
            mode: 'text',
            pythonPath: 'python',
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

        if (settings) {
            if (settings.namingFormat) {
                pythonOptions.args.push('--naming-format', settings.namingFormat);
            }
            if (settings.pageOrder) {
                pythonOptions.args.push('--page-order', settings.pageOrder);
            }
        }

        const results = await new Promise((resolve, reject) => {
            PythonShell.run('pdf_merger.py', pythonOptions, (err, results) => {
                if (err) {
                    logger.error('Python script error:', err);
                    reject(err);
                } else {
                    try {
                        const lastLine = results[results.length - 1];
                        const result = JSON.parse(lastLine);
                        resolve(result);
                    } catch (parseErr) {
                        logger.error('Failed to parse Python results:', parseErr);
                        resolve({
                            success: true,
                            message: 'Processing completed, but could not parse detailed results',
                            stats: {
                                processed_files: files.pdfFiles?.length || 0,
                                merged_clients: 0
                            }
                        });
                    }
                }
            });
        });

        results.jobId = jobId;
        results.downloadUrl = `/api/merger/download/${jobId}`;

        logger.info(`Merger processing completed for job ${jobId}`);

        const completedJob = performanceMonitor.completeJob(trackingJobId, results);
        
        res.json({
            success: true,
            ...results,
            performance: {
                duration: completedJob.duration,
                filesPerSecond: (results.stats?.processed_files || 0) / (completedJob.duration / 1000)
            }
        });

    } catch (error) {
        performanceMonitor.failJob(trackingJobId, error);
        logger.error('Merger processing error:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message,
            jobId: trackingJobId
        });
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
