# 🔧 PDF Merger Integration Guide

## Quick Integration Steps

### 1. **Update Your Project Structure**

Add these to your existing `pdf-processor-webapp/` directory:

```
pdf-processor-webapp/
├── public/
│   └── index.html              # REPLACE with enhanced version
├── textOverlay.js              # Your existing processor (keep)
├── server.js                   # REPLACE with enhanced version  
├── package.json                # REPLACE with enhanced version
├── python-requirements.txt     # ADD new file
├── python-scripts/             # ADD new directory
│   └── pdf_merger.py           # ADD new file
├── uploads/                    # Existing (keep)
├── outputs/                    # Existing (keep)
├── signatures/                 # Existing (keep)
├── merger-uploads/             # AUTO-CREATED by new server
├── merger-outputs/             # AUTO-CREATED by new server
├── manifests/                  # AUTO-CREATED by new server
└── logs/                       # AUTO-CREATED by new server
```

### 2. **Installation Commands**

```bash
# Navigate to your project
cd pdf-processor-webapp

# Install new Node.js dependencies
npm install python-shell xlsx csv-parser csv-writer archiver uuid node-cron winston helmet compression express-rate-limit

# Install Python dependencies
pip install -r python-requirements.txt

# Create Python scripts directory
mkdir python-scripts

# Copy the Python merger script to python-scripts/pdf_merger.py
```

### 3. **File Updates Required**

#### Replace these files with the enhanced versions:
- ✅ `package.json` - Adds new dependencies
- ✅ `server.js` - Adds merger endpoints while keeping your existing form processor
- ✅ `public/index.html` - Adds merger interface while keeping your form processor

#### Add these new files:
- ✅ `python-requirements.txt` - Python dependencies
- ✅ `python-scripts/pdf_merger.py` - Python merger script

#### Keep unchanged:
- ✅ `textOverlay.js` - Your existing form processor logic
- ✅ All existing files in `uploads/`, `outputs/`, `signatures/`

### 4. **Testing the Integration**

```bash
# Start your enhanced server
npm start

# Test both features:
# 1. Form Processor: http://localhost:3000 (your existing functionality)
# 2. Document Merger: http://localhost:3000#merger (new functionality)
```

## 🎯 What This Integration Provides

### **Enhanced Capabilities**
- ✅ **Dual Functionality**: Form processor + Document merger in one app
- ✅ **Unified Interface**: Single web app with tabbed navigation
- ✅ **Shared Infrastructure**: Common file handling, logging, security
- ✅ **Professional UI**: Modern interface for both tools

### **New Merger Features**
- 📊 **EDI File Processing**: Automatic client manifest generation
- 🚢 **Smart Document Classification**: Bills of Lading, Advice of Arrivals, Customer Documents
- 👥 **Client Grouping**: Automatically merge documents by client reference
- ⚙️ **Configurable Settings**: File naming, page ordering, error handling
- 📈 **Processing Statistics**: Detailed reports and analytics

### **Technical Improvements**
- 🔒 **Enhanced Security**: Helmet, rate limiting, input validation
- 📝 **Comprehensive Logging**: Winston logging with file outputs
- 🧹 **Automatic Cleanup**: Scheduled cleanup of temporary files
- ⚡ **Performance**: Compression, optimized file handling
- 🔄 **Error Recovery**: Robust error handling and recovery

## 🔄 Migration Strategy

### **Phase 1: Safe Integration (Recommended)**
1. **Backup your current project**
2. **Test in development environment first**
3. **Gradually migrate files one by one**
4. **Verify existing form processor still works**

### **Phase 2: Full Deployment**
1. **Deploy enhanced version to production**
2. **Monitor logs for any issues**
3. **Train users on new merger functionality**

## 🐛 Troubleshooting

### **Common Issues & Solutions**

#### 1. **Python Script Not Found**
```bash
# Ensure Python is in PATH and script exists
which python
ls python-scripts/pdf_merger.py
```

#### 2. **Module Import Errors**
```bash
# Install missing Python packages
pip install PyMuPDF openpyxl xlrd
```

#### 3. **File Upload Issues**
```bash
# Check directory permissions
chmod 755 merger-uploads merger-outputs manifests
```

#### 4. **Port Conflicts**
```bash
# Change port in server.js if needed
const PORT = process.env.PORT || 3001;
```

### **Debug Mode**
```bash
# Enable debug logging
DEBUG=* npm start

# Check log files
tail -f logs/combined.log
tail -f logs/error.log
```

## 📚 API Endpoints Reference

### **Existing Form Processor** (unchanged)
- `POST /api/upload` - Upload PDF forms
- `POST /api/process` - Process forms with overlays
- `GET /api/download/:jobId` - Download processed files

### **New Document Merger**
- `POST /api/merger/upload` - Upload PDFs and EDI files
- `POST /api/merger/process-manifest` - Process manifest from EDI
- `POST /api/merger/process` - Merge documents by client
- `GET /api/merger/download/:jobId` - Download merged files

### **Shared Endpoints**
- `GET /api/health` - Health check for both services
- `GET /api/info` - Application information
- `POST /api/cleanup` - Clean temporary files

## 🚀 Advanced Configuration

### **Environment Variables**
```bash
# Add to your .env file
PORT=3000
LOG_LEVEL=info
CLEANUP_INTERVAL=daily
MAX_FILE_SIZE=100MB
RATE_LIMIT_WINDOW=15min
RATE_LIMIT_MAX=100
```

### **Custom Python Path**
```javascript
// In server.js, update Python path if needed
const pythonOptions = {
    pythonPath: '/usr/bin/python3',  // Adjust as needed
    // ... other options
};
```

### **Production Optimizations**
```bash
# Use PM2 for production
npm install -g pm2
pm2 start server.js --name "pdf-tools-suite"
pm2 startup
pm2 save
```

## 📞 Support

If you encounter any issues during integration:

1. **Check the logs**: `logs/error.log` and `logs/combined.log`
2. **Verify dependencies**: Ensure all npm and pip packages are installed
3. **Test individually**: Test form processor and merger separately
4. **Check file permissions**: Ensure write access to all directories

## 🎉 Success Indicators

You'll know the integration worked when:

- ✅ Your existing form processor still works at `http://localhost:3000`
- ✅ New merger interface appears at `http://localhost:3000#merger`
- ✅ Both tabs in the interface work properly
- ✅ File uploads work for both processors and merger
- ✅ Downloads work for both features
- ✅ No errors in the console or log files

---

**Ready to transform your PDF processing capabilities!** 🚀
