# 📚 PDF Tools Suite - User Guide

## 🎯 Welcome to Your PDF Processing Solution

The PDF Tools Suite combines two powerful tools in one easy-to-use web application:
- **📝 Form Processor** - Adds text overlays to PDF forms
- **🚢 Document Merger** - Merges shipping documents by client

---

## 🚀 Getting Started

### Access the Application
1. Open your web browser
2. Go to: `http://localhost:3000` (or your server's address)
3. You'll see two tabs: **Form Processor** and **Document Merger**

---

## 📝 Form Processor Guide

### What It Does
Automatically adds text overlays to specific positions on PDF forms - perfect for:
- Customs declarations (TOR forms)
- Import/export documents
- Shipping forms

### Step-by-Step Instructions

#### 1. Upload Your PDF Forms
- Click the **Form Processor** tab
- **Drag and drop** PDF files into the upload area
- Or click the area to **browse and select** files
- ✅ **Multiple files supported** - process batches together

#### 2. Configure Text Overlays
- Click **"+ Add Text Overlay"** for each text field you need
- For each overlay, specify:
  - **Text**: What you want to write (e.g., "Simone Ganasen")
  - **Page**: Which page to add it to (usually page 9 for TOR forms)
  - **X Position**: Horizontal position (e.g., 200 = move right)
  - **Y Position**: Vertical position (e.g., 400 = move up)
  - **Font Size**: Text size (10-12 works best)

#### 3. Upload Signature (Optional)
- Drop a signature image (PNG, JPG, GIF)
- Will be automatically added to all forms

#### 4. Process Forms
- Click **"🚀 Process Forms"**
- Wait for processing (shows progress bar)
- Download completed files

### 💡 Pro Tips
- **Test first**: Use one file to test overlay positions before batch processing
- **Standard positions**: For TOR forms, text usually goes on page 9
- **Font size**: 10-12 point works best for most forms
- **Positioning**: Start with X=200, Y=400 and adjust from there

---

## 🚢 Document Merger Guide

### What It Does
Organizes and merges shipping documents by client reference, combining:
- **Advice of Arrivals** (multi-client documents)
- **Bills of Lading** (multi-client documents)
- **Customer Documents** (individual client files)

### Step-by-Step Instructions

#### 1. Upload Your Documents
Click the **Document Merger** tab and upload:

**📊 EDI File** (.xls/.xlsx):
- Contains client names and references
- Most reliable way to get correct client information
- Should have client names in column 6, references in column 11

**📄 PDF Documents**:
- **Advice of Arrivals**: Multi-client PDF documents
- **Bills of Lading**: Multi-client PDF documents
- **Customer Documents**: Individual client PDFs

#### 2. Process Manifest (Recommended)
- If you uploaded an EDI file, click **"📊 Process Manifest"**
- This creates a client reference list from your EDI file
- Review the client list that appears
- This ensures correct client names in final PDFs

#### 3. Configure Settings
- **File Naming**: Choose how output files are named
  - `name_ref`: "John Smith_123-456-789.pdf"
  - `ref_name`: "123-456-789_John Smith.pdf"
- **Page Order**: How documents are arranged
  - `advice_bill_customer`: Advice → Bills → Customer (recommended)

#### 4. Merge Documents
- Click **"🚢 Merge Documents"**
- System automatically:
  - Identifies which pages belong to which client
  - Groups documents by client reference (e.g., 123/456/789)
  - Creates merged PDFs for each client
  - Organizes pages in your chosen order

#### 5. Download Results
- Individual client PDFs are created
- Download the complete package as ZIP
- Files named according to your settings

### 📋 File Requirements

**EDI File Format:**
- Column 6: Consignee Name (e.g., "John Smith")
- Column 11: Consignee Reference (e.g., "123/456/789")

**Customer Document Naming:**
- Include client reference in filename: `Client_123-456-789.pdf`
- Reference format: 123/456/789 or 123-456-789

### 💡 Pro Tips
- **EDI file is essential**: Most reliable way to get correct client names
- **Check references**: Ensure customer documents have client references in filenames
- **Batch processing**: Handle hundreds of documents efficiently
- **Preview first**: Use "Process Manifest" to verify client list before merging

---

## 🔧 Settings & Configuration

### Performance Monitoring
Check your system's performance:
- **Health Status**: `http://localhost:3000/api/health`
- **Detailed Metrics**: `http://localhost:3000/api/metrics`
- **System Info**: `http://localhost:3000/api/system-info`

### File Limits
- **Maximum file size**: 100MB per file
- **Maximum files**: 50 files per upload
- **Supported formats**: PDF, XLS, XLSX

### Output Optimization
- **Automatic compression**: PDFs optimized to ~1.2MB
- **Quality preservation**: Text and images remain sharp
- **Fast processing**: Optimized for batch operations

---

## 🐛 Troubleshooting

### Common Issues

#### Upload Problems
**"File upload failed"**
- ✅ Check file size (under 100MB)
- ✅ Verify file format (PDF, XLS, XLSX only)
- ✅ Refresh page and try again

#### Form Processor Issues
**"Text appears in wrong position"**
- ✅ Check page number (usually page 9 for TOR forms)
- ✅ Adjust X/Y coordinates
- ✅ Test with single file first

**"Text is too small/large"**
- ✅ Adjust font size (try 10-12)
- ✅ Test different sizes

#### Document Merger Issues
**"Client not found"**
- ✅ Check client reference format (123/456/789)
- ✅ Verify EDI file contains the client
- ✅ Ensure customer document filenames include reference

**"Wrong client name"**
- ✅ Use EDI file for accurate names
- ✅ Check EDI file column format
- ✅ Process manifest before merging

### Getting Help
1. **Check this guide** for solutions
2. **Look at log files** (admins can check server logs)
3. **Refresh the page** and try again
4. **Contact IT support** if issues persist

---

## 🎓 Best Practices

### Daily Workflow

**For Form Processing:**
1. Gather all PDF forms needing the same overlays
2. Test overlay positions with one sample file
3. Batch process all similar forms together
4. Quality check random samples

**For Document Merging:**
1. Prepare EDI file with all client references
2. Upload all documents at once
3. Process manifest first to verify client list
4. Review settings before merging
5. Download and distribute merged PDFs to clients

### File Organization
```
📁 Daily Processing/
├── 📄 EDI_2025-06-19.xlsx
├── 📄 Advice_of_Arrival_2025-06-19.pdf
├── 📄 Bills_of_Lading_2025-06-19.pdf
└── 📁 Customer_Documents/
    ├── 📄 Client1_123-456-789.pdf
    ├── 📄 Client2_987-654-321.pdf
    └── 📄 Client3_555-666-777.pdf
```

### Quality Control
- **Backup originals** before processing
- **Test with small batches** first
- **Review output** before distributing
- **Keep processing logs** for reference

---

## 📊 Success Metrics

### What Good Performance Looks Like
- **Processing time**: < 2 minutes for typical batches
- **Error rate**: < 5% with proper setup
- **File sizes**: Consistent ~1.2MB output files
- **User satisfaction**: Easy to use after initial setup

### Time Savings
**Before PDF Tools Suite:**
- 30 documents × 2 minutes each = 60 minutes
- Manual positioning and formatting
- Inconsistent results

**After PDF Tools Suite:**
- 30 documents × 1 click = 2 minutes
- Automated positioning and compression
- Consistent, professional results

**💰 ROI: 58 minutes saved per batch!**

---

## 🆘 Emergency Procedures

### If the System is Down
1. Check if server is running
2. Restart the application: `npm start`
3. Check for error messages in console
4. Contact system administrator

### If Files Are Lost
1. Check the `outputs` and `merger-outputs` folders
2. Files are kept for 7 days automatically
3. Check backup systems if available

### If Processing Fails
1. Try with smaller batch (5-10 files)
2. Check file formats and sizes
3. Verify EDI file format
4. Clear browser cache and try again

---

## 🎉 You're Ready!

This PDF Tools Suite will transform your document processing workflow. Remember:

- **Start small** with test batches
- **Use EDI files** for best merger results
- **Test overlay positions** before large batches
- **Keep backups** of original files

**Happy processing! 🚀**

---

*For technical support or feature requests, contact your IT team.*
