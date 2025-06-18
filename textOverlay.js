const fs = require('fs');
const path = require('path');
const pdf = require('pdf-parse');
const { PDFDocument, rgb, StandardFonts } = require('pdf-lib');
const { execSync } = require('child_process');

/**
 * Text Overlay PDF Processor
 * Places text at specific coordinates on PDF pages, regardless of form fields
 */
class TextOverlayProcessor {
    constructor() {
        this.shipmentData = null;
        this.maxFileSize = 1.1 * 1024 * 1024; // 1.1MB in bytes (updated from 1.2MB)
        this.processedCount = 0;
        this.failedFiles = [];
        this.successFiles = [];
        
                    // Text overlay configuration for "Declaration at Import" page
        this.overlayConfig = {
            targetPageNumber: 9, // Page 9 is the "Declaration at Import" page
            font: StandardFonts.Helvetica,
            fontSize: 10,
            textColor: rgb(0, 0, 0), // Black text
            
            // Signature configuration
            signatureConfig: {
                imagePath: './signature.png', // Path to signature image
                width: 400,  // Signature width in points (4x bigger: 120 * 4)
                height: 160, // Signature height in points (4x bigger: 40 * 4)
                x: 44,       // Move left from 100 (10 characters left, ~4 points per char)
                y: 68,       // Move down from 148 (12 lines down, ~8 points per line)
            },
            
            // Field positions (x, y coordinates from bottom-left origin)
            // Fine-tuned coordinates based on user feedback v5 - BG Orange correction!
            fields: [
                {
                    name: 'mvField',
                    x: 200,  // Move LEFT from 400 (50 characters left, ~4 points per char)
                    y: 720,  // Move down from 728 (1 line down, ~8 points per line)
                    description: 'MV/Ship name and date'
                },
                {
                    name: 'containerNumber',
                    x: 460,  // Keep position (was good)
                    y: 384,  // Keep vertical position (was good)
                    description: 'Container number'
                },
                {
                    name: 'importerDate',
                    x: 80,   // Keep horizontal position (was good)
                    y: 646,  // Keep position (was good)
                    description: 'Importer date'
                },
                {
                    name: 'carrierDate',
                    x: 450,  // Keep horizontal position
                    y: 148,  // Keep position (PERFECT!)
                    description: 'Carrier date'
                },
                {
                    name: 'signature',
                    x: 100,  // 25 characters from left margin
                    y: 148,  // Same line as carrier date
                    description: 'Signature image'
                }
            ]
        };
    }

    /**
     * Process multiple PDF files with text overlay
     */
    async processBatch(inputFolder = '.', outputFolder = '.') {
        try {
            console.log('🚀 Starting batch PDF processing with text overlay...');
            console.log(`📁 Input folder: ${inputFolder}`);
            console.log(`📁 Output folder: ${outputFolder}`);
            
            // Find all PDF files
            const pdfFiles = this.findPDFFiles(inputFolder);
            
            if (pdfFiles.length === 0) {
                console.log('❌ No PDF files found!');
                return { success: false, message: 'No PDF files found' };
            }
            
            console.log(`📋 Found ${pdfFiles.length} PDF files to process`);
            
            // Extract shipment data from the first PDF
            console.log('\n📖 Extracting shipment data from first document...');
            await this.extractShipmentData(pdfFiles[0]);
            
            if (!this.shipmentData) {
                console.log('❌ Failed to extract shipment data from first document');
                return { success: false, message: 'Failed to extract shipment data' };
            }
            
            console.log('✅ Shipment data extracted successfully:');
            console.log(`   Container: ${this.shipmentData.containerNumber}`);
            console.log(`   Ship: ${this.shipmentData.mvField}`);
            console.log(`   Date: ${this.shipmentData.todaysDate}`);
            
            // Create output folder if it doesn't exist
            if (!fs.existsSync(outputFolder)) {
                fs.mkdirSync(outputFolder, { recursive: true });
            }
            
        // Check compression tools at startup
        const availableTools = this.checkCompressionTools();
        if (availableTools.length === 0) {
            console.log('⚠️  No external compression tools found!');
            console.log('💡 Install for better compression: brew install ghostscript imagemagick qpdf');
            console.log('📌 Will use basic compression only\n');
        } else {
            console.log(`🛠️  Available compression tools: ${availableTools.join(', ')}\n`);
        }
            for (let i = 0; i < pdfFiles.length; i++) {
                const inputFile = pdfFiles[i];
                const outputFile = this.generateOutputFileName(inputFile, outputFolder);
                
                console.log(`\n📄 Processing ${i + 1}/${pdfFiles.length}: ${path.basename(inputFile)}`);
                
                const result = await this.processSinglePDFWithOverlay(inputFile, outputFile);
                
                if (result.success) {
                    this.successFiles.push({
                        input: inputFile,
                        output: outputFile,
                        sizeMB: result.finalSizeMB,
                        overlaysAdded: result.overlaysAdded
                    });
                    console.log(`   ✅ Success: ${path.basename(outputFile)} (${result.finalSizeMB.toFixed(2)}MB, ${result.overlaysAdded} overlays)`);
                } else {
                    this.failedFiles.push({
                        input: inputFile,
                        error: result.error
                    });
                    console.log(`   ❌ Failed: ${result.error}`);
                }
                
                this.processedCount++;
            }
            
            // Print summary
            this.printBatchSummary();
            
            return {
                success: true,
                processed: this.processedCount,
                successful: this.successFiles.length,
                failed: this.failedFiles.length,
                successFiles: this.successFiles,
                failedFiles: this.failedFiles
            };
            
        } catch (error) {
            console.error('❌ Batch processing failed:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Process a single PDF with text overlay
     */
    async processSinglePDFWithOverlay(inputPath, outputPath) {
        try {
            // Load PDF
            const existingPdfBytes = fs.readFileSync(inputPath);
            const pdfDoc = await PDFDocument.load(existingPdfBytes);
            
            // Get pages
            const pages = pdfDoc.getPages();
            
            if (pages.length < this.overlayConfig.targetPageNumber) {
                throw new Error(`PDF has only ${pages.length} pages, but target page is ${this.overlayConfig.targetPageNumber}`);
            }
            
            // Get the target page (Declaration at Import page)
            const targetPage = pages[this.overlayConfig.targetPageNumber - 1]; // Convert to 0-based index
            
            // Embed font
            const font = await pdfDoc.embedFont(this.overlayConfig.font);
            
            // Add text overlays
            const overlaysAdded = await this.addTextOverlays(targetPage, font);
            
            // Save and check size
            let filledBytes = await pdfDoc.save();
            let filledSizeMB = filledBytes.length / (1024 * 1024);
            
            // Save to temporary file for advanced compression
            const tempPath = `${outputPath}.temp.pdf`;
            fs.writeFileSync(tempPath, filledBytes);
            
            console.log(`   📊 After overlays: ${filledSizeMB.toFixed(2)}MB`);
            
            // Apply advanced compression if needed
            if (filledSizeMB > 1.1) {
                console.log(`   🗜️  Applying advanced compression (target: 1.1MB)...`);
                const compressionResult = await this.advancedCompress(tempPath, outputPath, 1.1);
                
                if (compressionResult.success) {
                    console.log(`   ✅ Compressed: ${compressionResult.originalSizeMB.toFixed(2)}MB → ${compressionResult.finalSizeMB.toFixed(2)}MB`);
                } else {
                    console.log(`   ⚠️  Compression failed, using original`);
                    fs.copyFileSync(tempPath, outputPath);
                }
                
                // Clean up temp file
                if (fs.existsSync(tempPath)) {
                    fs.unlinkSync(tempPath);
                }
            } else {
                // File is already under target, just rename temp to final
                fs.renameSync(tempPath, outputPath);
                console.log(`   ✅ Already under 1.1MB, no compression needed`);
            }
            const finalSizeMB = this.getFileSizeMB(outputPath);
            
            return {
                success: true,
                finalSizeMB: finalSizeMB,
                compressed: filledSizeMB > 1.1,
                overlaysAdded: overlaysAdded
            };
            
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Add text overlays and signature to the target page
     */
    async addTextOverlays(page, font) {
        let overlaysAdded = 0;
        
        try {
            const { width, height } = page.getSize();
            console.log(`   📐 Page dimensions: ${width.toFixed(0)} x ${height.toFixed(0)}`);
            
            // First, try to add signature image
            let signatureAdded = false;
            try {
                if (fs.existsSync(this.overlayConfig.signatureConfig.imagePath)) {
                    const signatureImageBytes = fs.readFileSync(this.overlayConfig.signatureConfig.imagePath);
                    let signatureImage;
                    
                    // Determine image type and embed accordingly
                    const imagePath = this.overlayConfig.signatureConfig.imagePath.toLowerCase();
                    if (imagePath.endsWith('.png')) {
                        signatureImage = await page.doc.embedPng(signatureImageBytes);
                    } else if (imagePath.endsWith('.jpg') || imagePath.endsWith('.jpeg')) {
                        signatureImage = await page.doc.embedJpg(signatureImageBytes);
                    } else {
                        throw new Error('Unsupported image format. Use PNG or JPG.');
                    }
                    
                    // Draw the signature
                    page.drawImage(signatureImage, {
                        x: this.overlayConfig.signatureConfig.x,
                        y: this.overlayConfig.signatureConfig.y,
                        width: this.overlayConfig.signatureConfig.width,
                        height: this.overlayConfig.signatureConfig.height,
                    });
                    
                    console.log(`   ✅ Added signature image at (${this.overlayConfig.signatureConfig.x}, ${this.overlayConfig.signatureConfig.y})`);
                    signatureAdded = true;
                    overlaysAdded++;
                    
                } else {
                    console.log(`   ⚠️  Signature image not found: ${this.overlayConfig.signatureConfig.imagePath}`);
                }
            } catch (signatureError) {
                console.log(`   ❌ Failed to add signature: ${signatureError.message}`);
            }
            
            // Add text overlays (exclude signature field from text processing)
            for (const field of this.overlayConfig.fields) {
                if (field.name === 'signature') continue; // Skip signature field for text
                
                try {
                    let textToAdd = '';
                    
                    // Determine what text to add based on field name
                    switch (field.name) {
                        case 'mvField':
                            textToAdd = this.shipmentData.mvField;
                            break;
                        case 'containerNumber':
                            textToAdd = this.shipmentData.containerNumber;
                            break;
                        case 'importerDate':
                        case 'carrierDate':
                            textToAdd = this.shipmentData.todaysDate;
                            break;
                        default:
                            console.log(`   ⚠️  Unknown field: ${field.name}`);
                            continue;
                    }
                    
                    // Add the text overlay
                    page.drawText(textToAdd, {
                        x: field.x,
                        y: field.y,
                        size: this.overlayConfig.fontSize,
                        font: font,
                        color: this.overlayConfig.textColor,
                    });
                    
                    console.log(`   ✅ Added overlay: ${field.description} = "${textToAdd}" at (${field.x}, ${field.y})`);
                    overlaysAdded++;
                    
                } catch (fieldError) {
                    console.log(`   ❌ Failed to add overlay for ${field.description}: ${fieldError.message}`);
                }
            }
            
        } catch (error) {
            console.error('Error adding text overlays:', error);
        }
        
        return overlaysAdded;
    }

    /**
     * Find PDF files (same as before)
     */
    findPDFFiles(folder) {
        try {
            const files = fs.readdirSync(folder);
            const pdfFiles = files
                .filter(file => file.toLowerCase().endsWith('.pdf'))
                .filter(file => !file.includes('_complete'))
                .map(file => path.join(folder, file))
                .sort();
            
            return pdfFiles;
        } catch (error) {
            console.error('Error finding PDF files:', error);
            return [];
        }
    }

    /**
     * Generate output filename (same as before)
     */
    generateOutputFileName(inputFile, outputFolder) {
        const parsedPath = path.parse(inputFile);
        const outputFileName = `${parsedPath.name}_complete${parsedPath.ext}`;
        return path.join(outputFolder, outputFileName);
    }

    /**
     * Extract shipment data (same as before)
     */
    async extractShipmentData(firstPdfPath) {
        try {
            const dataBuffer = fs.readFileSync(firstPdfPath);
            const pdfData = await pdf(dataBuffer);
            const fullText = pdfData.text;
            
            // Extract container/trailer number
            const containerMatch = fullText.match(/Container\s*\/?\s*Trailer:\s*([A-Z0-9]+)/i);
            const containerNumber = containerMatch ? containerMatch[1] : 'CAAU7611844';
            
            // Extract ship name and date from arrival instructions
            const arrivalMatch = fullText.match(/Arriving per\s+([^(]+)\([^)]+\)\s+on\s+(\d{2}[./]\d{2}[./]\d{4})/i);
            let shipName = 'BG Orange';
            let arrivalDate = '12.06.2025';
            
            if (arrivalMatch) {
                shipName = arrivalMatch[1].trim();
                arrivalDate = arrivalMatch[2].replace(/\//g, '.');
            }
            
            // Get today's date
            const today = new Date();
            const day = String(today.getDate()).padStart(2, '0');
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const year = today.getFullYear();
            const todaysDate = `${day}/${month}/${year}`;
            
            this.shipmentData = {
                containerNumber: containerNumber,
                shipName: shipName,
                arrivalDate: arrivalDate,
                mvField: `${shipName} ${arrivalDate}`,
                todaysDate: todaysDate
            };
            
            return this.shipmentData;
            
        } catch (error) {
            console.error('Error extracting shipment data:', error);
            return null;
        }
    }

    /**
     * Advanced PDF compression using external tools
     */
    async advancedCompress(inputPath, outputPath, targetSizeMB = 1.1) {
        try {
            const originalSizeMB = this.getFileSizeMB(inputPath);
            
            if (originalSizeMB <= targetSizeMB) {
                fs.copyFileSync(inputPath, outputPath);
                return { success: true, originalSizeMB, finalSizeMB: originalSizeMB, method: 'none' };
            }

            // Try compression methods in order of effectiveness
            const methods = [
                { name: 'ghostscript-screen', command: this.getGhostscriptCommand(inputPath, outputPath, 'screen') },
                { name: 'ghostscript-ebook', command: this.getGhostscriptCommand(inputPath, outputPath, 'ebook') },
                { name: 'imagemagick-low', command: this.getImageMagickCommand(inputPath, outputPath, 72, 50) },
                { name: 'imagemagick-med', command: this.getImageMagickCommand(inputPath, outputPath, 96, 70) },
                { name: 'qpdf', command: `qpdf --linearize --optimize-images --compress-streams=y "${inputPath}" "${outputPath}"` }
            ];

            for (const method of methods) {
                try {
                    // Clean up any existing output file
                    if (fs.existsSync(outputPath)) {
                        fs.unlinkSync(outputPath);
                    }

                    execSync(method.command, { stdio: 'ignore', timeout: 30000 });
                    
                    if (fs.existsSync(outputPath)) {
                        const compressedSizeMB = this.getFileSizeMB(outputPath);
                        
                        if (compressedSizeMB <= targetSizeMB) {
                            return {
                                success: true,
                                originalSizeMB,
                                finalSizeMB: compressedSizeMB,
                                method: method.name,
                                compressionRatio: ((originalSizeMB - compressedSizeMB) / originalSizeMB * 100).toFixed(1)
                            };
                        }
                        // This method didn't achieve target, continue to next
                    }
                } catch (methodError) {
                    // Method failed, try next one
                    continue;
                }
            }

            // If no method worked, copy original
            fs.copyFileSync(inputPath, outputPath);
            return {
                success: false,
                originalSizeMB,
                finalSizeMB: originalSizeMB,
                method: 'fallback',
                message: 'Could not achieve target compression'
            };

        } catch (error) {
            // Fallback to original file
            if (fs.existsSync(inputPath)) {
                fs.copyFileSync(inputPath, outputPath);
            }
            
            return {
                success: false,
                originalSizeMB: this.getFileSizeMB(inputPath),
                finalSizeMB: this.getFileSizeMB(inputPath),
                method: 'error',
                error: error.message
            };
        }
    }

    /**
     * Generate Ghostscript compression command
     */
    getGhostscriptCommand(inputPath, outputPath, quality) {
        const qualityMap = {
            'screen': '/screen',    // Lowest quality, highest compression
            'ebook': '/ebook',      // Medium quality
            'printer': '/printer',  // High quality
            'prepress': '/prepress' // Highest quality
        };

        const gsQuality = qualityMap[quality] || '/screen';
        
        return `gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=${gsQuality} -dNOPAUSE -dQUIET -dBATCH -dColorImageResolution=72 -dGrayImageResolution=72 -dMonoImageResolution=72 -sOutputFile="${outputPath}" "${inputPath}"`;
    }

    /**
     * Generate ImageMagick compression command
     */
    getImageMagickCommand(inputPath, outputPath, density, quality) {
        return `convert -density ${density} -quality ${quality} -compress jpeg "${inputPath}" "${outputPath}"`;
    }

    /**
     * Check if compression tools are available
     */
    checkCompressionTools() {
        const tools = [
            { name: 'Ghostscript', command: 'gs --version' },
            { name: 'ImageMagick', command: 'convert --version' },
            { name: 'QPDF', command: 'qpdf --version' }
        ];

        const available = [];
        
        tools.forEach(tool => {
            try {
                execSync(tool.command, { stdio: 'ignore' });
                available.push(tool.name.toLowerCase());
            } catch (error) {
                // Tool not available
            }
        });

        return available;
    }

    /**
     * Get file size in MB
     */
    getFileSizeMB(filePath) {
        const stats = fs.statSync(filePath);
        return stats.size / (1024 * 1024);
    }

    /**
     * Print batch processing summary
     */
    printBatchSummary() {
        console.log('\n' + '='.repeat(60));
        console.log('📊 BATCH PROCESSING SUMMARY (TEXT OVERLAY)');
        console.log('='.repeat(60));
        console.log(`📄 Total files processed: ${this.processedCount}`);
        console.log(`✅ Successful: ${this.successFiles.length}`);
        console.log(`❌ Failed: ${this.failedFiles.length}`);
        
        if (this.successFiles.length > 0) {
            console.log('\n✅ Successfully processed files:');
            this.successFiles.forEach((file, index) => {
                const fileName = path.basename(file.output);
                console.log(`   ${index + 1}. ${fileName} (${file.sizeMB.toFixed(2)}MB, ${file.overlaysAdded} overlays)`);
            });
        }
        
        if (this.failedFiles.length > 0) {
            console.log('\n❌ Failed files:');
            this.failedFiles.forEach((file, index) => {
                const fileName = path.basename(file.input);
                console.log(`   ${index + 1}. ${fileName} - ${file.error}`);
            });
        }
        
        console.log('\n🎯 Text overlays added to page 9:');
        console.log(`   📍 MV Field: "${this.shipmentData.mvField}"`);
        console.log(`   📍 Container: "${this.shipmentData.containerNumber}"`);
        console.log(`   📍 Dates: "${this.shipmentData.todaysDate}"`);
        console.log('='.repeat(60));
    }

    /**
     * Adjust overlay positions (for fine-tuning)
     */
    updateOverlayPositions(newPositions) {
        Object.assign(this.overlayConfig.fields, newPositions);
        console.log('📍 Overlay positions updated');
    }

    /**
     * Test overlay positions on a single page
     */
    async testOverlayPositions(pdfPath, outputPath = 'test_overlay.pdf') {
        try {
            console.log('🧪 Testing overlay positions...');
            
            const result = await this.processSinglePDFWithOverlay(pdfPath, outputPath);
            
            if (result.success) {
                console.log(`✅ Test overlay created: ${outputPath}`);
                console.log(`📍 Overlays added: ${result.overlaysAdded}`);
                console.log('💡 Check the output file and adjust positions if needed');
                
                // Show current positions
                console.log('\n📍 Current overlay positions:');
                this.overlayConfig.fields.forEach(field => {
                    console.log(`   ${field.description}: x=${field.x}, y=${field.y}`);
                });
                
                return result;
            } else {
                console.log(`❌ Test failed: ${result.error}`);
                return result;
            }
            
        } catch (error) {
            console.error('Test overlay failed:', error);
            return { success: false, error: error.message };
        }
    }
}

// Export the class
module.exports = TextOverlayProcessor;

// CLI execution
if (require.main === module) {
    const args = process.argv.slice(2);
    const processor = new TextOverlayProcessor();
    
    if (args[0] === 'test') {
        // Test mode - overlay on single file
        const inputFile = args[1] || './test-pdfs/Simone Ganasen_000-534-927.pdf';
        const outputFile = args[2] || './test_overlay.pdf';
        
        console.log('🧪 TEST MODE: Testing overlay positions...');
        
        // Extract data first
        processor.extractShipmentData(inputFile).then(() => {
            return processor.testOverlayPositions(inputFile, outputFile);
        }).then(() => {
            console.log('\n💡 Tips for adjusting positions:');
            console.log('- Increase x to move text right, decrease to move left');
            console.log('- Increase y to move text up, decrease to move down');
            console.log('- Edit the overlayConfig in textOverlay.js to adjust positions');
        });
        
    } else if (args[0] === 'help') {
        console.log(`
📍 Text Overlay PDF Processor Usage:

Test overlay positions:
  node textOverlay.js test "input.pdf" "test_output.pdf"

Batch process (current folder):
  node textOverlay.js

Batch process (specify folders):
  node textOverlay.js "/path/to/input" "/path/to/output"

Examples:
  node textOverlay.js test                                    # Test with default file
  node textOverlay.js test "./test-pdfs/document.pdf"        # Test specific file
  node textOverlay.js "./pdfs" "./completed"                 # Batch process

Features:
- Places text at exact coordinates on page 9
- Works with any PDF (no form fields needed)
- Adjustable text positions
- Batch processing for multiple files
- Automatic compression to 1.2MB
        `);
        
    } else {
        // Batch processing mode
        const inputFolder = args[0] || '.';
        const outputFolder = args[1] || './completed';
        
        processor.processBatch(inputFolder, outputFolder).then(result => {
            if (result.success) {
                console.log(`\n🎉 Batch processing completed! ${result.successful}/${result.processed} files processed successfully.`);
            } else {
                console.log(`\n❌ Batch processing failed: ${result.message || result.error}`);
                process.exit(1);
            }
        });
    }
}
