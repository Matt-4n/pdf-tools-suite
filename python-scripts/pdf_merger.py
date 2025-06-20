import os
import re
import fitz  # PyMuPDF
import csv
import argparse
import sys
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from pdf_optimizer import PDFOptimizer

# For Excel file reading
try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    try:
        import xlrd
        EXCEL_AVAILABLE = True
    except ImportError:
        EXCEL_AVAILABLE = False

def setup_logging(job_id=None):
    """Set up simple logging for PDF merger"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if job_id:
        log_filename = f"merger_{job_id}_{timestamp}.log"
    else:
        log_filename = f"pdf_merger_{timestamp}.log"
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # Log to file
            logging.FileHandler(log_dir / log_filename, encoding='utf-8'),
            # Also show on screen (console)
            logging.StreamHandler()
        ]
    )
    
    # Return logger
    logger = logging.getLogger('PDFMerger')
    logger.info("=== PDF Merger Started ===")
    logger.info(f"Log file: {log_filename}")
    
    return logger

class PDFMerger:
    def __init__(self, input_folder, output_folder, reference_doc=None, edi_file=None, 
                 enable_optimization=True, target_size_mb=1.2):
        # Add logging
        self.logger = logging.getLogger('PDFMerger')
        self.logger.info(f"Initializing PDF Merger: {input_folder} -> {output_folder}")
        
        # Basic initialization
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
        self.clients = defaultdict(lambda: {'info': None, 'pages': []})
        self.manifest = {}
        self.reference_doc = reference_doc
        self.edi_file = edi_file
        
        # Add optimization settings
        self.enable_optimization = enable_optimization
        self.target_size_mb = target_size_mb
        
        if self.enable_optimization:
            self.optimizer = PDFOptimizer(target_size_mb=target_size_mb, quality=85)
            self.logger.info(f"PDF optimization enabled (target: {target_size_mb}MB)")
            
            # Initialize optimization statistics
            self.optimization_stats = {
                'files_optimized': 0,
                'total_savings_mb': 0,
                'average_compression_ratio': 0
            }
        
        # Priority order for creating manifest:
        # 1. EDI Excel file (most reliable)
        # 2. Reference PDF document
        # 3. Existing CSV manifest
        if edi_file:
            self.create_manifest_from_edi(edi_file)
        elif reference_doc:
            self.create_manifest_from_reference(reference_doc)
        else:
            # Try to load existing CSV manifest
            self.load_manifest("client_manifest.csv")
    
    def create_manifest_from_edi(self, edi_file_path):
        """Create CSV manifest from EDI Excel file"""
        edi_path = Path(edi_file_path)
        if not edi_path.exists():
            self.logger.error(f"EDI file not found: {edi_file_path}")
            return
        
        if not EXCEL_AVAILABLE:
            self.logger.error("Excel libraries not available. Please install openpyxl or xlrd.")
            return
        
        self.logger.info(f"Creating manifest from EDI file: {edi_file_path}")
        
        try:
            manifest_data = {}
            
            # Check file extension and use appropriate library
            if str(edi_path).endswith('.xls'):
                # Use xlrd for .xls files
                import xlrd
                workbook = xlrd.open_workbook(edi_path)
                sheet = workbook.sheet_by_index(0)
                
                # Read data starting from row 1 (skip header row 0)
                for row_idx in range(1, sheet.nrows):
                    row = sheet.row_values(row_idx)
                    if len(row) > 11:  # Ensure we have enough columns
                        consignee_name = row[6]  # Column 6: "Consignees Name"
                        consignee_ref = row[11]  # Column 11: "Consignees Reference"
                        
                        if consignee_ref and consignee_name:
                            # Clean up the reference format
                            ref_clean = str(consignee_ref).strip()
                            name_clean = str(consignee_name).strip()
                            
                            if ref_clean and name_clean:
                                if self.is_valid_name(name_clean):
                                    manifest_data[ref_clean] = name_clean
                                    self.logger.debug(f"Added: {ref_clean} -> {name_clean}")
            
            else:
                # Use openpyxl for .xlsx files
                from openpyxl import load_workbook
                workbook = load_workbook(edi_path, read_only=True)
                sheet = workbook.active
                
                # Read data starting from row 2 (skip header)
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if row and len(row) > 11:  # Ensure we have enough columns
                        consignee_name = row[6]  # Column 6: "Consignees Name"
                        consignee_ref = row[11]  # Column 11: "Consignees Reference"
                        
                        if consignee_ref and consignee_name:
                            # Clean up the reference format
                            ref_clean = str(consignee_ref).strip()
                            name_clean = str(consignee_name).strip()
                            
                            if ref_clean and name_clean:
                                if self.is_valid_name(name_clean):
                                    manifest_data[ref_clean] = name_clean
                                    self.logger.debug(f"Added: {ref_clean} -> {name_clean}")
            
            # Save to CSV file
            csv_path = "client_manifest.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ConsigneeRef', 'FullName'])  # Header
                
                for ref, name in sorted(manifest_data.items()):
                    writer.writerow([ref, name])
            
            self.logger.info(f"Created manifest CSV with {len(manifest_data)} clients: {csv_path}")
            
            # Load the created manifest into memory
            self.manifest = manifest_data
            
        except Exception as e:
            self.logger.error(f"Error creating manifest from EDI file: {e}")
            if self.reference_doc:
                self.create_manifest_from_reference(self.reference_doc)
            else:
                self.load_manifest("client_manifest.csv")

    def create_manifest_from_reference(self, reference_doc_path):
        """Create CSV manifest from reference PDF document"""
        reference_path = Path(reference_doc_path)
        if not reference_path.exists():
            self.logger.error(f"Reference document not found: {reference_doc_path}")
            return
        
        self.logger.info(f"Creating manifest from reference document: {reference_doc_path}")
        
        try:
            doc = fitz.open(reference_path)
            manifest_data = {}
            
            # Process each page of the reference document
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Extract all client entries from this page
                clients_on_page = self.extract_clients_from_reference_page(text)
                
                for consignee_ref, name in clients_on_page:
                    if consignee_ref and name:
                        manifest_data[consignee_ref] = name
                        self.logger.debug(f"Found: {consignee_ref} -> {name}")
            
            doc.close()
            
            # Save to CSV file
            csv_path = "client_manifest.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ConsigneeRef', 'FullName'])  # Header
                
                for ref, name in sorted(manifest_data.items()):
                    writer.writerow([ref, name])
            
            self.logger.info(f"Created manifest CSV with {len(manifest_data)} clients: {csv_path}")
            
            # Load the created manifest into memory
            self.manifest = manifest_data
            
        except Exception as e:
            self.logger.error(f"Error creating manifest from reference: {e}")
    
    def extract_clients_from_reference_page(self, text):
        """Extract client info from reference document page"""
        clients = []
        
        # Split text into lines and look for client entries
        lines = text.split('\n')
        
        current_ref = None
        current_name = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for customer reference pattern
            ref_match = re.search(r'Cust Ref:\s*(\d{3}/\d{3}/\d{3})', line)
            if ref_match:
                current_ref = ref_match.group(1)
                continue
            
            # Look for name pattern (usually appears after "Name:" field)
            name_match = re.search(r'Name:\s*([A-Z][a-z]+ (?:[A-Z][a-z]+ )*[A-Z][a-z]+)', line)
            if name_match and current_ref:
                current_name = name_match.group(1).strip()
                
                # Validate the name
                if self.is_valid_name(current_name):
                    clients.append((current_ref, current_name))
                    current_ref = None  # Reset for next client
                    current_name = None
        
        return clients
    
    def load_manifest(self, manifest_file):
        """Load client manifest from CSV file"""
        manifest_path = Path(manifest_file)
        if not manifest_path.exists():
            self.logger.warning(f"No existing manifest file found: {manifest_file}")
            return
        
        try:
            self.logger.info(f"Loading existing manifest from: {manifest_file}")
            with open(manifest_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        consignee_ref = row[0].strip()
                        full_name = row[1].strip()
                        self.manifest[consignee_ref] = full_name
                        
            self.logger.info(f"Loaded {len(self.manifest)} clients from manifest")
        except Exception as e:
            self.logger.error(f"Error loading manifest: {e}")
    
    def get_name_from_manifest(self, consignee_ref):
        """Get name from manifest if available"""
        return self.manifest.get(consignee_ref)
    
    def extract_text_from_page(self, doc, page_num):
        """Extract text from a specific page"""
        try:
            page = doc[page_num]
            return page.get_text()
        except:
            return ""
    
    def find_client_info_on_page(self, text):
        """Extract consignee reference and match against EDI manifest ONLY"""
        # Find consignee reference in text
        ref_patterns = [
            r'(\d{3}/\d{3}/\d{3})',  # 000/531/023
            r'(\d{3}-\d{3}-\d{3})',  # 000-531-023
        ]
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Normalize reference format
                normalized_ref = match.replace('-', '/')
                
                # Check if this reference exists in EDI manifest
                if normalized_ref in self.manifest:
                    consignee_ref = normalized_ref
                    full_name = self.manifest[normalized_ref]
                    return consignee_ref, full_name
        
        # No EDI match found
        return None, None
    
    def is_valid_name(self, name):
        """Check if extracted text is a valid person name"""
        if not name:
            return False
        
        # Clean up the name
        name_cleaned = re.sub(r'\s+', ' ', name.strip())
        
        # Must have at least 2 words
        words = name_cleaned.split()
        if len(words) < 2:
            return False
        
        # Exclude common business/location terms
        exclude_terms = [
            'Seven Seas', 'Hong Kong', 'Dublin Port', 'Advice of', 'Bill of',
            'Ever Gain', 'Notify Party', 'New South', 'Old Hospital', 
            'Little Lonsdale', 'Maunganui Road', 'Grange Manor'
        ]
        
        if any(term in name_cleaned for term in exclude_terms):
            return False
        
        # Skip if contains numbers or common non-name words
        if re.search(r'\d|Street|Road|Avenue|Building|Plaza|Unit|Apartment|House|Court|Park|Lane|Drive', name_cleaned):
            return False
        
        # Check if it looks like a real person's name
        for word in words:
            if len(word) == 0:
                continue
            if not (word[0].isupper() and (word[1:].islower() or "'" in word)):
                return False
        
        return True
    
    def process_multi_client_document(self, pdf_path, doc_type):
        """Process Advice of Arrivals or Bills of Lading"""
        self.logger.info(f"Processing Multi-Client Document: {pdf_path.name}")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        self.logger.info(f"Document has {total_pages} pages")
        
        # Analyze each page to find which client it belongs to
        for page_num in range(total_pages):
            text = self.extract_text_from_page(doc, page_num)
            consignee_ref, full_name = self.find_client_info_on_page(text)
            
            if consignee_ref and full_name:
                self.logger.info(f"Page {page_num + 1}: {consignee_ref} - {full_name}")
                
                # Store client info and page reference
                client_key = consignee_ref
                if not self.clients[client_key]['info']:
                    self.clients[client_key]['info'] = (consignee_ref, full_name)
                
                # Add this page to the client's collection
                self.clients[client_key]['pages'].append({
                    'source_doc': pdf_path,
                    'page_num': page_num,
                    'doc_type': doc_type,
                    'doc_obj': doc
                })
            else:
                self.logger.warning(f"Page {page_num + 1}: Could not identify client")
        
        return doc
    
    def process_customer_document_edi_first(self, pdf_path):
        """Process individual customer document using EDI-first matching"""
        self.logger.info(f"Processing Customer Document: {pdf_path.name}")
        
        # First, try to extract reference from filename
        filename = pdf_path.name
        ref_match = re.search(r'(\d{3}[-/]\d{3}[-/]\d{3})', filename)
        
        doc = fitz.open(pdf_path)
        
        if ref_match:
            file_ref = ref_match.group(1).replace('-', '/')
            
            # Check if this reference exists in EDI manifest
            if file_ref in self.manifest:
                client_name = self.manifest[file_ref]
                self.logger.info(f"Customer Doc: {file_ref} - {client_name} (EDI match)")
                
                # Store customer document info
                if not self.clients[file_ref]['info']:
                    self.clients[file_ref]['info'] = (file_ref, client_name)
                
                # Add all pages of customer document to this client
                for page_num in range(len(doc)):
                    self.clients[file_ref]['pages'].append({
                        'source_doc': pdf_path,
                        'page_num': page_num,
                        'doc_type': 'Customer Document',
                        'doc_obj': doc
                    })
                
                return doc
        
        # If filename didn't work, scan document content for EDI references
        text = ""
        for page in doc:
            text += page.get_text()
        
        # Look for any EDI reference in the document text
        for edi_ref in self.manifest.keys():
            if edi_ref in text or edi_ref.replace('/', '-') in text:
                client_name = self.manifest[edi_ref]
                self.logger.info(f"Customer Doc: {edi_ref} - {client_name} (EDI content match)")
                
                if not self.clients[edi_ref]['info']:
                    self.clients[edi_ref]['info'] = (edi_ref, client_name)
                
                for page_num in range(len(doc)):
                    self.clients[edi_ref]['pages'].append({
                        'source_doc': pdf_path,
                        'page_num': page_num,
                        'doc_type': 'Customer Document',
                        'doc_obj': doc
                    })
                
                return doc
        
        # Document doesn't match any EDI reference
        self.logger.warning(f"Customer document {pdf_path.name} does not match any EDI reference - skipping")
        doc.close()
        return None
    
    def merge_client_documents(self, client_key, client_data):
        """Merge all documents for a specific client with optimization"""
        consignee_ref, full_name = client_data['info']
        if not consignee_ref:
            self.logger.error(f"Missing consignee reference for {client_key}")
            return False
        
        # If no name, create a default one
        if not full_name:
            full_name = f"Client_{consignee_ref.replace('/', '_')}"
        
        self.logger.info(f"Merging documents for: {consignee_ref} - {full_name}")
        
        # Group pages by document type
        advice_pages = []
        bill_pages = []
        customer_pages = []
        
        for page_info in client_data['pages']:
            if page_info['doc_type'] == 'Advice of Arrivals':
                advice_pages.append(page_info)
            elif page_info['doc_type'] == 'Bill of Lading':
                bill_pages.append(page_info)
            elif page_info['doc_type'] == 'Customer Document':
                customer_pages.append(page_info)
        
        self.logger.info(f"Found: {len(advice_pages)} Advice pages, {len(bill_pages)} Bill pages, {len(customer_pages)} Customer pages")
        
        # Create merged PDF in correct order: Advice → Bills → Customer
        merged_doc = fitz.open()  # Create new empty document
        
        # Add pages in order
        for page_info in advice_pages:
            source_doc = page_info['doc_obj']
            page_num = page_info['page_num']
            merged_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
        
        for page_info in bill_pages:
            source_doc = page_info['doc_obj']
            page_num = page_info['page_num']
            merged_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
        
        for page_info in customer_pages:
            source_doc = page_info['doc_obj']
            page_num = page_info['page_num']
            merged_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
        
        # Save merged document
        safe_ref = consignee_ref.replace('/', '-')
        safe_name = re.sub(r'[^\w\s-]', '', full_name).strip()
        
        output_filename = f"{safe_name}_{safe_ref}.pdf"
        output_path = self.output_folder / output_filename
        
        # Save initial merged document
        merged_doc.save(str(output_path))
        merged_doc.close()
        
        total_pages = len(advice_pages) + len(bill_pages) + len(customer_pages)
        self.logger.info(f"✅ Merged: {output_filename} ({total_pages} pages)")
        
        # Apply optimization if enabled
        if self.enable_optimization:
            try:
                self.logger.info(f"🗜️ Optimizing: {output_filename}")
                optimization_result = self.optimizer.optimize_pdf(output_path)
                
                if optimization_result['optimized']:
                    self.logger.info(f"   Optimized: {optimization_result['original_size_mb']:.2f}MB → "
                                  f"{optimization_result['final_size_mb']:.2f}MB "
                                  f"(saved {optimization_result['savings_mb']:.2f}MB)")
                    
                    # Update optimization statistics
                    self.optimization_stats['files_optimized'] += 1
                    self.optimization_stats['total_savings_mb'] += optimization_result['savings_mb']
                    
                    # Update average compression ratio
                    files_count = self.optimization_stats['files_optimized']
                    current_avg = self.optimization_stats['average_compression_ratio']
                    new_ratio = optimization_result['compression_ratio']
                    self.optimization_stats['average_compression_ratio'] = (
                        (current_avg * (files_count - 1) + new_ratio) / files_count
                    )
                else:
                    self.logger.info(f"   No optimization needed: {optimization_result['reason']}")
                    
            except Exception as e:
                self.logger.warning(f"   ⚠️ Optimization failed: {str(e)}")
        
        return True
    
    def process_all_documents(self):
        """Main process: analyze all PDFs and merge by EDI client list ONLY"""
        pdf_files = list(self.input_folder.glob("*.pdf"))
        
        if not pdf_files:
            self.logger.error("No PDF files found!")
            return
        
        # CRITICAL: Only proceed if we have an EDI manifest
        if not self.manifest:
            self.logger.error("No EDI manifest loaded! Cannot process without client list.")
            return
        
        self.logger.info(f"Found {len(pdf_files)} PDF files to process")
        self.logger.info(f"EDI manifest contains {len(self.manifest)} clients")
        
        opened_docs = []  # Keep track of opened documents
        
        # Process each PDF file
        for pdf_path in pdf_files:
            filename = pdf_path.name.lower()
            
            if 'advice' in filename:
                doc = self.process_multi_client_document(pdf_path, 'Advice of Arrivals')
                if doc:
                    opened_docs.append(doc)
            elif 'bill' in filename or 'lading' in filename:
                doc = self.process_multi_client_document(pdf_path, 'Bill of Lading')
                if doc:
                    opened_docs.append(doc)
            else:
                # Assume it's a customer document
                doc = self.process_customer_document_edi_first(pdf_path)
                if doc:
                    opened_docs.append(doc)
        
        # ONLY merge documents for EDI clients
        edi_clients_processed = 0
        
        self.logger.info(f"MERGING DOCUMENTS FOR {len(self.manifest)} EDI CLIENTS")
        
        for edi_ref, edi_name in self.manifest.items():
            # Check if this EDI client has any documents
            if edi_ref in self.clients and self.clients[edi_ref]['pages']:
                self.logger.info(f"Processing EDI client: {edi_ref} - {edi_name}")
                
                # Ensure we use the EDI name as authoritative
                self.clients[edi_ref]['info'] = (edi_ref, edi_name)
                
                success = self.merge_client_documents(edi_ref, self.clients[edi_ref])
                if success:
                    edi_clients_processed += 1
            else:
                self.logger.warning(f"No documents found for EDI client: {edi_ref} - {edi_name}")
        
        # Close all opened documents
        for doc in opened_docs:
            doc.close()
        
        self.logger.info(f"✅ Process complete! Check the '{self.output_folder.name}' folder for merged PDFs.")
        self.logger.info(f"📊 EDI clients: {len(self.manifest)} | Processed: {edi_clients_processed}")

def parse_command_line():
    """Parse command line arguments with optimization options"""
    parser = argparse.ArgumentParser(description='PDF Merger - Merge shipping documents by client')
    
    # Required arguments
    parser.add_argument('--input-folder', required=True,
                       help='Folder containing PDF files to merge')
    parser.add_argument('--output-folder', required=True,
                       help='Folder to save merged PDF files')
    
    # Optional arguments for manifest
    parser.add_argument('--edi-file',
                       help='EDI Excel file (.xls or .xlsx) for client manifest')
    parser.add_argument('--reference-doc',
                       help='Reference PDF document to extract client manifest')
    parser.add_argument('--manifest-file',
                       help='Existing CSV manifest file')
    
    # Optimization options
    parser.add_argument('--enable-optimization', action='store_true', default=True,
                       help='Enable PDF optimization (default: enabled)')
    parser.add_argument('--disable-optimization', action='store_true',
                       help='Disable PDF optimization')
    parser.add_argument('--target-size', type=float, default=1.2,
                       help='Target file size in MB (default: 1.2)')
    parser.add_argument('--quality', type=int, default=85,
                       help='Image quality 0-100 (default: 85)')
    
    # Optional settings
    parser.add_argument('--job-id',
                       help='Job ID for web application processing')
    parser.add_argument('--json-output', action='store_true',
                       help='Output results as JSON (for web application)')
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_command_line()
    
    # Set up logging FIRST
    logger = setup_logging(args.job_id)
    
    # Check if input folder exists
    if not Path(args.input_folder).exists():
        logger.error(f"Input folder does not exist: {args.input_folder}")
        print(f"❌ Error: Input folder does not exist: {args.input_folder}")
        sys.exit(1)
    
    # Determine optimization settings
    enable_optimization = args.enable_optimization and not args.disable_optimization
    
    # Create PDF merger with command line arguments
    try:
        logger.info("Creating PDF merger instance")
        pdf_merger = PDFMerger(
            input_folder=args.input_folder,
            output_folder=args.output_folder,
            edi_file=args.edi_file,
            reference_doc=args.reference_doc,
            enable_optimization=enable_optimization,
            target_size_mb=args.target_size
        )
        
        # Load manifest file if specified
        if args.manifest_file:
            logger.info(f"Loading manifest file: {args.manifest_file}")
            pdf_merger.load_manifest(args.manifest_file)
        
        # Process documents
        logger.info("Starting document processing")
        pdf_merger.process_all_documents()
        
        # Get final statistics
        total_clients = len(pdf_merger.clients)
        
        # Include optimization stats in output
        result_stats = {
            'processed_files': len(list(Path(args.input_folder).glob("*.pdf"))),
            'merged_clients': total_clients,
            'optimization': pdf_merger.optimization_stats if enable_optimization else None
        }
        
        # Simple success message
        if args.json_output:
            import json
            result = {
                'success': True,
                'message': 'Processing completed successfully',
                'output_folder': args.output_folder,
                'stats': result_stats
            }
            print(json.dumps(result))
        else:
            print(f"\n✅ Processing complete! Check the '{args.output_folder}' folder for merged PDFs.")
            
            if enable_optimization:
                opt_stats = pdf_merger.optimization_stats
                print(f"🗜️ Optimization Summary:")
                print(f"   Files optimized: {opt_stats['files_optimized']}")
                print(f"   Total space saved: {opt_stats['total_savings_mb']:.2f} MB")
                if opt_stats['files_optimized'] > 0:
                    print(f"   Average compression: {opt_stats['average_compression_ratio']:.2f}x")
            
        logger.info("=== PDF Merger Completed Successfully ===")
    
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error(error_msg)
        logger.error("=== PDF Merger Failed ===")
        
        if args.json_output:
            import json
            print(json.dumps({'success': False, 'error': error_msg}))
        else:
            print(f"❌ {error_msg}")
        sys.exit(1)
