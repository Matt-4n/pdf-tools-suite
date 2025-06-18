const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const app = express();
const port = 3000;

// Disable caching for development
app.use((req, res, next) => {
    res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    next();
});

// Configure file upload
const upload = multer({ 
    dest: 'uploads/',
    limits: { fileSize: 50 * 1024 * 1024 }
});

// Serve static files from public directory
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Create directories
const dirs = ['./uploads', './outputs', './signatures', './public'];
dirs.forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
});

// Explicitly serve index.html for root path
app.get('/', (req, res) => {
    const indexPath = path.join(__dirname, 'public', 'index.html');
    console.log('📄 Serving index.html from:', indexPath);
    console.log('📄 File exists:', fs.existsSync(indexPath));
    res.sendFile(indexPath);
});

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
