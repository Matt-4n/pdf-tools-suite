const { performance } = require('perf_hooks');
const fs = require('fs-extra');
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

const app = express();
const PORT = process.env.PORT || 3000;

// Simple Performance Monitor Class
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
    
    // Start tracking a job
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
    
    // Complete a job successfully
    completeJob(jobId, result = {}) {
        const job = this.activeJobs.get(jobId);
        if (!job) return null;
        
        const duration = performance.now() - job.startTime;
        job.duration = duration;
        job.status = 'completed';
        job.result = result;
        
        // Update metrics
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
    
    // Mark a job as failed
    failJob(jobId, error) {
        const job = this.activeJobs.get(jobId);
        if (!job) return null;
        
        const duration = performance.now() - job.startTime;
        job.duration = duration;
        job.status = 'failed';
        job.error = error.message || error;
        
        // Update metrics
        this.metrics.totalRequests++;
        this.metrics.failedRequests++;
        
        // Keep track of recent errors (last 50)
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
    
    // Get current metrics
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
    
    // Get health status
    getHealthStatus() {
        const metrics = this.getMetrics();
        const recentErrors = this.metrics.errors.filter(
            error => Date.now() - new Date(error.timestamp).getTime() < 60000 // Last minute
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
    contentSecurityPolicy: false // Allow inline scripts for our app
}));
app.use(compression());
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
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
            const allowedTypes = /\.(pdf|xls|xlsx)$/i;
            if (allowedTypes.test(file.originalname)) {
                cb(null, true);
            } else {
                cb(new Error('Only PDF, XLS, and XLSX files are allowed'));
            }
        }
    });
};

const uploadProcessor = createMulterStorage('uploads');
const uploadMerger = createMulterStorage('merger-uploads');

// Serve static files
app.use(express.static('public'));

// ==================== EXISTING FORM PROCESSOR ROUTES ====================

// Your existing form processor upload endpoint
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

        res.json({
            success: true,
            files: processedFiles,
            message: `Uploaded ${req.files.length} files successfully`
        });
    } catch (error) {
        logger.error('Upload error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Your existing form processor process endpoint
app.post('/api/process', async (req, res) => {
    try {
        const { files, overlays, settings } = req.body;
        logger.info(`Processing ${files.length} files with form overlay`);

        // Your existing form processing logic would go here
        // This is a placeholder for your textOverlay.js functionality
        
        const jobId = uuidv4();
        const outputDir = path.join('outputs', jobId);
        await fs.ensureDir(outputDir);

        // Simulate processing (replace with your actual logic)
        const processedFiles = [];
        for (const file of files) {
            // Your existing PDF processing logic
            processedFiles.push({
                originalName: file.originalName,
                processedName: `processed_${file.originalName}`,
                path: path.join(outputDir, `processed_${file.originalName}`)
            });
        }

        res.json({
            success: true,
            jobId: jobId,
            processedFiles: processedFiles,
            downloadUrl: `/api/download/${jobId}`
        });

    } catch (error) {
        logger.error('Processing error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// ==================== NEW PDF MERGER ROUTES ====================

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

        // Process PDF files
        if (req.files.pdfFiles) {
            uploadedFiles.pdfFiles = req.files.pdfFiles.map(file => ({
                id: uuidv4(),
                originalName: file.originalname,
                filename: file.filename,
                path: file.path,
                size: file.size
            }));
        }

        // Process EDI file
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

        // Process reference document
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

        // Process EDI file if provided
        if (ediFilePath && await fs.pathExists(ediFilePath)) {
            manifest = await processEdiFile(ediFilePath);
        } else if (referenceDocPath && await fs.pathExists(referenceDocPath)) {
            // For reference docs, you'd call your Python script
            manifest = await processReferenceDocument(referenceDocPath);
        }

        // Save manifest as CSV
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

// Main merger processing endpoint - ENHANCED WITH PERFORMANCE MONITORING
app.post('/api/merger/process', async (req, res) => {
    // Generate job ID and start performance tracking
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

        // Prepare Python script arguments
        const pythonOptions = {
            mode: 'text',
            pythonPath: 'python', // Adjust if needed
            scriptPath: path.join(__dirname),  // Use root directory since pdf_merger.py is there
            args: [
                '--input-folder', 'merger-uploads',
                '--output-folder', outputDir,
                '--job-id', jobId,
                '--json-output'  // Enable JSON output for web app
            ]
        };

        // Add manifest if available
        if (manifestPath && await fs.pathExists(manifestPath)) {
            pythonOptions.args.push('--manifest-file', manifestPath);
        }

        // Add settings
        if (settings) {
            if (settings.namingFormat) {
                pythonOptions.args.push('--naming-format', settings.namingFormat);
            }
            if (settings.pageOrder) {
                pythonOptions.args.push('--page-order', settings.pageOrder);
            }
        }

        // Execute Python merger script
        const results = await new Promise((resolve, reject) => {
            PythonShell.run('pdf_merger.py', pythonOptions, (err, results) => {
                if (err) {
                    logger.error('Python script error:', err);
                    reject(err);
                } else {
                    try {
                        // Get the last line which should be JSON output
                        const lastLine = results[results.length - 1];
                        const result = JSON.parse(lastLine);
                        resolve(result);
                    } catch (parseErr) {
                        logger.error('Failed to parse Python results:', parseErr);
                        logger.error('Raw output:', results);
                        // Fallback result if JSON parsing fails
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

        // Add job info to results
        results.jobId = jobId;
        results.downloadUrl = `/api/merger/download/${jobId}`;

        logger.info(`Merger processing completed for job ${jobId}`);

        // Complete the performance tracking job successfully
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
        // Mark the performance tracking job as failed
        performanceMonitor.failJob(trackingJobId, error);
        
        logger.error('Merger processing error:', error);
        res.status(500).json({ 
            success: false, 
            error: error.message,
            jobId: trackingJobId
        });
    }
});

        // Add manifest if available
        if (manifestPath && await fs.pathExists(manifestPath)) {
            pythonOptions.args.push('--manifest-file', manifestPath);
        }

        // Add settings
        if (settings) {
            if (settings.namingFormat) {
                pythonOptions.args.push('--naming-format', settings.namingFormat);
            }
            if (settings.pageOrder) {
                pythonOptions.args.push('--page-order', settings.pageOrder);
            }
        }

        // Execute Python merger script
        const results = await new Promise((resolve, reject) => {
            PythonShell.run('pdf_merger.py', pythonOptions, (err, results) => {
                if (err) {
                    logger.error('Python script error:', err);
                    reject(err);
                } else {
                    try {
                        const result = JSON.parse(results[results.length - 1]);
                        resolve(result);
                    } catch (parseErr) {
                        logger.error('Failed to parse Python results:', parseErr);
                        reject(parseErr);
                    }
                }
            });
        });

        // Add job info to results
        results.jobId = jobId;
        results.downloadUrl = `/api/merger/download/${jobId}`;

        logger.info(`Merger processing completed for job ${jobId}`);

        res.json({
            success: true,
            ...results
        });

    } catch (error) {
        logger.error('Merger processing error:', error);
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

        // Add all PDF files from the output directory
        const files = await fs.readdir(outputDir);
        const pdfFiles = files.filter(file => file.endsWith('.pdf'));

        for (const file of pdfFiles) {
            const filePath = path.join(outputDir, file);
            archive.file(filePath, { name: file });
        }

        await archive.finalize();

        // Wait for the zip to be created
        await new Promise((resolve) => output.on('close', resolve));

        res.download(zipPath, `merged_documents_${jobId}.zip`, (err) => {
            if (err) {
                logger.error('Download error:', err);
            }
            // Clean up zip file after download
            fs.remove(zipPath).catch(console.error);
        });

    } catch (error) {
        logger.error('Download error:', error);
        res.status(500).json({ error: error.message });
    }
});
// Download merged files
app.get('/api/merger/download/:jobId', async (req, res) => {
    // ... your existing download code stays here
});

// ==================== PERFORMANCE MONITORING ENDPOINTS ====================
// ADD THESE NEW ENDPOINTS HERE:

// Get current metrics
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

// Health check endpoint
app.get('/api/health', (req, res) => {
    try {
        const health = performanceMonitor.getHealthStatus();
        res.json(health);
    } catch (error) {
        res.status(500).json({ 
            status: 'error', 
            error: error.message 
        });
    }
});

// Detailed system information
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

// ==================== END MONITORING ENDPOINTS ====================

// Clean up old files (runs daily at 2 AM)
cron.schedule('0 2 * * *', async () => {
    // ... your existing cron job code stays here
});                                                                                                                                                                                
                                                                                                                                                                                

// ==================== SHARED ROUTES ====================

// Download processed files (existing functionality)
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

// Health check
app.get('/api/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
            formProcessor: 'active',
            documentMerger: 'active'
        }
    });
});

// Get application info
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
            // Adjust these column names based on your EDI format
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
    // This would call your Python script to extract manifest from PDF
    // For now, return empty manifest
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

// Cleanup old files (runs daily at 2 AM)
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
        
        app.listen(PORT, () => {
            logger.info(`🚀 PDF Processor & Merger Suite running on port ${PORT}`);
            logger.info(`📋 Form Processor: http://localhost:${PORT}`);
            logger.info(`🚢 Document Merger: http://localhost:${PORT}#merger`);
            logger.info(`📊 Health Check: http://localhost:${PORT}/api/health`);
        });
    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
}

startServer();

module.exports = app;

// Upload endpoint
app.post('/api/upload', upload.array('pdfs', 50), (req, res) => {
    try {
        const uploadedFiles = req.files || [];
        
        if (uploadedFiles.length === 0) {
            return res.status(400).json({ error: 'No files uploaded' });
        }

        console.log(`📁 Received ${uploadedFiles.length} PDF files:`);
        uploadedFiles.forEach(file => {
            console.log(`  - ${file.originalname} (${(file.size/1024/1024).toFixed(2)} MB)`);
        });

        const signatureExists = fs.existsSync('./signatures/default-signature.png');
        console.log(`✍️  Default signature: ${signatureExists ? 'Found' : 'Missing'}`);

        res.json({
            success: true,
            sessionId: Date.now().toString(),
            message: `Successfully uploaded ${uploadedFiles.length} files`,
            signatureAvailable: signatureExists,
            files: uploadedFiles.map(f => ({
                name: f.originalname,
                size: f.size
            }))
        });

    } catch (error) {
        console.error('Upload error:', error);
        res.status(500).json({ error: 'Upload failed' });
    }
});

// Process endpoint
app.post('/api/process', async (req, res) => {
    try {
        const { sessionId } = req.body;
        
        console.log(`🚀 Processing files for session ${sessionId}...`);
        console.log('✍️  Using default signature: ./signatures/default-signature.png');
        
        // Simulate processing for now
        setTimeout(() => {
            res.json({
                success: true,
                message: 'Files processed successfully with signature overlay! (Demo mode)',
                processed: 1,
                successful: 1,
                failed: 0
            });
        }, 2000);

    } catch (error) {
        console.error('Processing error:', error);
        res.status(500).json({ error: 'Processing failed' });
    }
});

// Health check
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        signatureAvailable: fs.existsSync('./signatures/default-signature.png')
    });
});

// Start server
app.listen(port, () => {
    console.log('🚀 PDF Processor Server Starting...');
    console.log(`📱 Access at: http://localhost:${port}`);
    
    // Check if files exist
    const indexExists = fs.existsSync('./public/index.html');
    const signatureExists = fs.existsSync('./signatures/default-signature.png');
    
    console.log(`📄 index.html: ${indexExists ? 'Found' : 'Missing'}`);
    console.log(`✍️  Signature: ${signatureExists ? 'Found' : 'Missing'}`);
    console.log('✅ Server ready!');
});

module.exports = app;
