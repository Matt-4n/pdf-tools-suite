#!/usr/bin/env python3
"""
PDF Merger Script for Node.js Integration
Simplified version of the enhanced merger for command-line usage
"""

import os
import re
import sys
import json
import argparse
import logging
from pathlib import Path
from collections import defaultdict

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplePDFMerger:
    def __init__(self, input_folder, output_folder, manifest_file=None):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True, parents=True)
        
        self.clients = defaultdict(lambda: {'info': None, 'pages': []})
        self.manifest = {}
        self.stats = {
            'files_processed': 0,
            'unique_clients_found': 0,
            'clients_merged_successfully': 0,
            'merge_errors': 0,
            'total_client_pages': 0
        }
        
        if manifest_file and Path(manifest_file).exists():
            self.load_manifest(manifest_file)
    
    def load_manifest(self, manifest_file):
        """Load client manifest from CSV file"""
        try:
            import csv
            with open(manifest_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 2:
                        self.manifest[row[0].strip()] = row[1].strip()
            logger.info(f"Loaded {len(self.manifest)} clients from manifest")
        except Exception as e:
            logger.error(f"Error loading manifest: {e}")
    
    def validate_client_reference(self, ref):
        """Validate client reference format"""
        if not ref:
            return False
        pattern = r'^\d{3}/\d{3}/\d{3}
        return bool(re.match(pattern, ref))
    
    def extract_client_info(self, text):
        """Extract client information from PDF text"""
        # Find consignee reference
        ref_patterns = [
            r'BL\s*No\s*:\s*(\d{3}/\d{3}/\d{3})',
            r'Consignee\s*Reference:\s*(\d{3}/\d{3}/\d{3})',
            r'Cust\s*Ref:\s*(\d{3}/\d{3}/\d{3})',
            r'(\d{3}/\d{3}/\d{3})'
        ]
        
        consignee_ref = None
        for pattern in ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_ref = match.group(1) if len(match.groups()) > 0 else match.group(0)
                if self.validate_client_reference(potential_ref):
                    consignee_ref = potential_ref
                    break
        
        if not consignee_ref:
            return None, None
        
        # Get name from manifest or use reference
        full_name = self.manifest.get(consignee_ref, f"Client_{consignee_ref.replace('/', '_')}")
        
        return consignee_ref, full_name
    
    def determine_document_type(self, filename):
        """Determine document type from filename"""
        filename_lower = filename.lower()
        if 'advice' in filename_lower:
            return 'Advice of Arrivals'
        elif 'bill' in filename_lower or 'lading' in filename_lower:
            return 'Bill of Lading'
        else:
            return 'Customer Document'
    
    def process_document(self, pdf_path):
        """Process a single PDF document"""
        try:
            doc = fitz.open(pdf_path)
            doc_type = self.determine_document_type(pdf_path.name)
            
            logger.info(f"Processing {doc_type}: {pdf_path.name}")
            
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    text = page.get_text()
                    
                    consignee_ref, full_name = self.extract_client_info(text)
                    
                    if consignee_ref and full_name:
                        client_key = consignee_ref
                        if not self.clients[client_key]['info']:
                            self.clients[client_key]['info'] = (consignee_ref, full_name)
                        
                        self.clients[client_key]['pages'].append({
                            'source_doc': pdf_path,
                            'page_num': page_num,
                            'doc_type': doc_type
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1} of {pdf_path}: {e}")
            
            doc.close()
            self.stats['files_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing document {pdf_path}: {e}")
    
    def merge_client_documents(self, client_key, client_data):
        """Merge all documents for a specific client"""
        try:
            consignee_ref, full_name = client_data['info']
            
            logger.info(f"Merging documents for: {consignee_ref} - {full_name}")
            
            # Group pages by document type
            pages_by_type = defaultdict(list)
            for page_info in client_data['pages']:
                pages_by_type[page_info['doc_type']].append(page_info)
            
            # Create merged PDF in order: Advice → Bills → Customer
            merged_doc = fitz.open()
            
            for doc_type in ['Advice of Arrivals', 'Bill of Lading', 'Customer Document']:
                for page_info in pages_by_type[doc_type]:
                    try:
                        source_doc = fitz.open(page_info['source_doc'])
                        merged_doc.insert_pdf(source_doc, 
                                            from_page=page_info['page_num'], 
                                            to_page=page_info['page_num'])
                        source_doc.close()
                    except Exception as e:
                        logger.error(f"Error adding page: {e}")
            
            # Save merged document
            safe_ref = consignee_ref.replace('/', '-')
            safe_name = re.sub(r'[^\w\s-]', '', full_name).strip()
            output_filename = f"{safe_name}_{safe_ref}.pdf"
            output_path = self.output_folder / output_filename
            
            merged_doc.save(str(output_path))
            merged_doc.close()
            
            total_pages = sum(len(pages) for pages in pages_by_type.values())
            logger.info(f"✅ Saved: {output_filename} ({total_pages} pages)")
            
            self.stats['clients_merged_successfully'] += 1
            self.stats['total_client_pages'] += total_pages
            
            return True
            
        except Exception as e:
            logger.error(f"Error merging documents for {client_key}: {e}")
            self.stats['merge_errors'] += 1
            return False
    
    def process_all_documents(self):
        """Main processing function"""
        pdf_files = list(self.input_folder.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning("No PDF files found!")
            return self.get_results()
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        # Process each PDF
        for pdf_path in pdf_files:
            self.process_document(pdf_path)
        
        self.stats['unique_clients_found'] = len(self.clients)
        
        # Merge documents for each client
        logger.info(f"Merging documents for {len(self.clients)} clients")
        
        for client_key, client_data in self.clients.items():
            self.merge_client_documents(client_key, client_data)
        
        return self.get_results()
    
    def get_results(self):
        """Get processing results"""
        return {
            'success': True,
            'files_processed': self.stats['files_processed'],
            'unique_clients_found': self.stats['unique_clients_found'],
            'clients_merged_successfully': self.stats['clients_merged_successfully'],
            'merge_errors': self.stats['merge_errors'],
            'total_client_pages': self.stats['total_client_pages'],
            'manifest_entries': len(self.manifest),
            'output_directory': str(self.output_folder)
        }

def main():
    parser = argparse.ArgumentParser(description='PDF Document Merger')
    parser.add_argument('--input-folder', required=True, help='Input folder containing PDF files')
    parser.add_argument('--output-folder', required=True, help='Output folder for merged files')
    parser.add_argument('--manifest-file', help='CSV manifest file')
    parser.add_argument('--job-id', help='Job ID for tracking')
    parser.add_argument('--naming-format', default='name_ref', help='Output naming format')
    parser.add_argument('--page-order', default='advice_bill_customer', help='Page ordering')
    
    args = parser.parse_args()
    
    try:
        # Initialize merger
        merger = SimplePDFMerger(
            input_folder=args.input_folder,
            output_folder=args.output_folder,
            manifest_file=args.manifest_file
        )
        
        # Process documents
        results = merger.process_all_documents()
        
        # Output results as JSON for Node.js
        print(json.dumps(results))
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'files_processed': 0,
            'unique_clients_found': 0,
            'clients_merged_successfully': 0,
            'merge_errors': 1
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == '__main__':
    main()
