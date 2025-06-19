# 🚀 PDF Tools Suite

Professional PDF processing solution for shipping and customs documents.

## ✨ Features

- **📝 Form Processor**: Automatic text overlays for PDF forms
- **🚢 Document Merger**: Merge shipping documents by client
- **🖥️ Web Interface**: User-friendly browser-based application
- **📊 Performance Monitoring**: Real-time metrics and health checks
- **🗜️ Smart Compression**: Automatic PDF size optimization
- **📋 Comprehensive Logging**: Detailed processing logs

## 🚀 Quick Start

```bash
# Install dependencies
npm install
pip install -r python-requirements.txt

# Start the application
npm start

# Access the application
open http://localhost:3000
```

## 📚 Documentation

- **[📖 Complete User Guide](docs/USER_GUIDE.md)** - Comprehensive instructions
- **[🚀 Quick Reference](docs/QUICK_REFERENCE.md)** - Cheat sheet for daily use
- **[🔧 API Documentation](docs/API.md)** - Technical reference

## 🎯 What's Included

### Form Processor
- Add text overlays to specific PDF positions
- Batch processing for multiple forms
- Signature integration
- Automatic compression

### Document Merger
- EDI file processing for client manifests
- Smart document classification
- Client-based document grouping
- Configurable output formats

## 📊 Performance Monitoring

- **Health Check**: `GET /api/health`
- **Metrics**: `GET /api/metrics`
- **System Info**: `GET /api/system-info`

## 🛠️ Technical Stack

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Node.js, Express
- **PDF Processing**: Python, PyMuPDF
- **Text Overlays**: PDF-lib, JavaScript
- **File Handling**: Multer, Archiver

## 🔧 Configuration

Key settings in `server.js`:
- File size limits
- Processing directories
- Log levels
- Performance monitoring

## 📝 Usage Examples

### Command Line (Python)
```bash
python pdf_merger.py --input-folder ./pdfs --output-folder ./merged --edi-file EDI.xlsx
```

### Web API
```javascript
// Upload and process forms
POST /api/upload
POST /api/process

// Merge documents
POST /api/merger/upload
POST /api/merger/process
```

## 🚦 System Requirements

- **Node.js**: v14 or higher
- **Python**: v3.7 or higher
- **Memory**: 2GB RAM minimum
- **Storage**: 10GB free space recommended

## 📊 Performance

- **Processing Speed**: ~2 minutes per batch
- **File Size**: Optimized to 1.2MB average
- **Concurrent Users**: Supports multiple users
- **Uptime**: Designed for 24/7 operation

## 🔒 Security

- File validation and size limits
- Automatic cleanup of temporary files
- No persistent storage of sensitive data
- Local processing (no cloud dependencies)

## 🆘 Support

1. Check the [User Guide](docs/USER_GUIDE.md)
2. Review [Quick Reference](docs/QUICK_REFERENCE.md)
3. Check server logs in `logs/` folder
4. Contact IT support

## 📈 Roadmap

- [ ] Template saving for common overlay configurations
- [ ] Advanced batch processing with scheduling
- [ ] Integration APIs for other systems
- [ ] Mobile-responsive interface improvements
- [ ] Advanced PDF optimization options

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Your license here]

---

**Transform your PDF processing workflow today! 🎉**gestions welcome!
