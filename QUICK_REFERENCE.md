# 🚀 PDF Tools Suite - Quick Reference

## 📝 Form Processor Cheat Sheet

### Standard TOR Form Settings
- **Page**: 9
- **Font Size**: 11
- **Common Positions**:
  - Name field: X=200, Y=450
  - Date field: X=400, Y=100
  - Reference: X=150, Y=300

### Quick Steps
1. Upload PDFs → 2. Add overlays → 3. Process → 4. Download

---

## 🚢 Document Merger Cheat Sheet

### File Requirements
- **EDI**: Column 6 = Names, Column 11 = References
- **Customer docs**: Include reference in filename
- **Reference format**: 123/456/789

### Quick Steps
1. Upload all files → 2. Process manifest → 3. Merge → 4. Download

---

## 🔧 Common Settings

### File Limits
- Max size: 100MB per file
- Max files: 50 per upload
- Formats: PDF, XLS, XLSX

### API Endpoints
- Health: `/api/health`
- Metrics: `/api/metrics`
- System: `/api/system-info`

---

## 🐛 Quick Fixes

| Problem | Solution |
|---------|----------|
| Text wrong position | Adjust X/Y coordinates |
| Upload fails | Check file size/format |
| Client not found | Verify reference format |
| Slow processing | Use smaller batches |

---

## 📞 Emergency Contacts

- **Server restart**: `npm start`
- **Check logs**: `logs/` folder
- **Clear cache**: Ctrl+F5 (browser)
- **IT Support**: [Your contact info]

---

*Keep this reference handy for daily use! 📌*
