import os
import re
import fitz  # PyMuPDF
import csv
from pathlib import Path
from collections import defaultdict

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

class PDFMerger:
    def __init__(self, input_folder, output_folder, reference_doc=None, edi_file=None):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.output_folder.mkdir(exist_ok=True)
        self.clients = defaultdict(lambda: {'info': None, 'pages': []})
        self.manifest = {}
        self.reference_doc = reference_doc
        self.edi_file = edi_file
        
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
            print(f"EDI file not found: {edi_file_path}")
            return
        
        if not EXCEL_AVAILABLE:
            print("Excel libraries not available. Please install openpyxl or xlrd.")
            return
        
        print(f"Creating manifest from EDI file: {edi_file_path}")
        
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
                            
                            # Debug output
                            print(f"Processing: '{ref_clean}' -> '{name_clean}'")
                            
                            if ref_clean and name_clean:
                                if self.is_valid_name(name_clean):
                                    manifest_data[ref_clean] = name_clean
                                    print(f"✅ Added: {ref_clean} -> {name_clean}")
                                else:
                                    print(f"❌ Rejected (invalid name): {ref_clean} -> {name_clean}")
            
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
                            
                            # Debug output
                            print(f"Processing: '{ref_clean}' -> '{name_clean}'")
                            
                            if ref_clean and name_clean:
                                if self.is_valid_name(name_clean):
                                    manifest_data[ref_clean] = name_clean
                                    print(f"✅ Added: {ref_clean} -> {name_clean}")
                                else:
                                    print(f"❌ Rejected (invalid name): {ref_clean} -> {name_clean}")
            
            # Save to CSV file
            csv_path = "client_manifest.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ConsigneeRef', 'FullName'])  # Header
                
                for ref, name in sorted(manifest_data.items()):
                    writer.writerow([ref, name])
            
            print(f"✅ Created manifest CSV with {len(manifest_data)} clients: {csv_path}")
            
            # Load the created manifest into memory
            self.manifest = manifest_data
            
        except Exception as e:
            print(f"Error creating manifest from EDI file: {e}")
            print("Falling back to reference document or existing CSV...")
            if self.reference_doc:
                self.create_manifest_from_reference(self.reference_doc)
            else:
                self.load_manifest("client_manifest.csv")

    def create_manifest_from_reference(self, reference_doc_path):
        """Create CSV manifest from reference PDF document"""
        reference_path = Path(reference_doc_path)
        if not reference_path.exists():
            print(f"Reference document not found: {reference_doc_path}")
            return
        
        print(f"Creating manifest from reference document: {reference_doc_path}")
        
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
                        print(f"Found: {consignee_ref} -> {name}")
            
            doc.close()
            
            # Save to CSV file
            csv_path = "client_manifest.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ConsigneeRef', 'FullName'])  # Header
                
                for ref, name in sorted(manifest_data.items()):
                    writer.writerow([ref, name])
            
            print(f"✅ Created manifest CSV with {len(manifest_data)} clients: {csv_path}")
            
            # Load the created manifest into memory
            self.manifest = manifest_data
            
        except Exception as e:
            print(f"Error creating manifest from reference: {e}")
    
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
            print(f"No existing manifest file found: {manifest_file}")
            return
        
        try:
            print(f"Loading existing manifest from: {manifest_file}")
            with open(manifest_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        consignee_ref = row[0].strip()
                        full_name = row[1].strip()
                        self.manifest[consignee_ref] = full_name
                        
            print(f"Loaded {len(self.manifest)} clients from manifest")
        except Exception as e:
            print(f"Error loading manifest: {e}")
    
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
        """Extract consignee reference and get name from manifest - prioritize reference number"""
        consignee_ref = None
        full_name = None
        
        # PRIORITY 1: Find consignee reference first
        ref_patterns = [
            r'BL\s*No\s*:\s*(\d{3}/\d{3}/\d{3})',  # Bill of Lading format
            r'Consignee\s*Reference:\s*(\d{3}/\d{3}/\d{3})',  # Advice of Arrivals format
            r'Cust\s*Ref:\s*(\d{3}/\d{3}/\d{3})',  # Customer reference format
            r'(\d{3}/\d{3}/\d{3})'  # General format (last resort)
        ]
        
        for pattern in ref_patterns:
            match = re.search(pattern, text)
            if match:
                consignee_ref = match.group(1) if len(match.groups()) > 0 else match.group(0)
                break
        
        if consignee_ref:
            # PRIORITY 2: Always check manifest first (this is our reliable source)
            manifest_name = self.get_name_from_manifest(consignee_ref)
            if manifest_name:
                return consignee_ref, manifest_name
            
            # PRIORITY 3: If not in manifest, try document extraction as fallback
            print(f"Warning: {consignee_ref} not found in manifest, attempting document extraction...")
            
            # For Bill of Lading - look for name in consignee section
            if "Bill of Lading" in text or "BL No" in text:
                full_name = self.extract_name_from_bill_of_lading(text)
            
            # For Advice of Arrivals - look for name in consignee section  
            elif "Advice of Arrival" in text:
                full_name = self.extract_name_from_advice_of_arrival(text)
            
            # For Customer Documents - different structure
            else:
                full_name = self.extract_name_from_customer_doc(text)
            
            # If we found a name through extraction, validate it first
            if full_name and self.is_valid_name(full_name):
                return consignee_ref, full_name
            
            # If extraction failed or gave invalid name, use reference number
            print(f"Could not find valid name for {consignee_ref}, using reference number")
            return consignee_ref, f"Client_{consignee_ref.replace('/', '_')}"
        
        return None, None
    
    def extract_name_from_bill_of_lading(self, text):
        """Extract name specifically from Bill of Lading structure"""
        # For Bills of Lading, look for the BL No first, then find the consignee name
        bl_match = re.search(r'BL\s*No\s*:\s*(\d{3}/\d{3}/\d{3})', text)
        if not bl_match:
            return None
            
        bl_number = bl_match.group(1)
        
        # Look for consignee name patterns specifically for Bills of Lading
        patterns = [
            # Pattern: "Consignee: Name" or "Consignee\nName"
            r'Consignee[:\s]*\n?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+[A-Z][a-z]+))\s*(?:\n|$)',
            # Pattern: Look for name before address/building names
            r'Consignee[^\n]*\n\s*([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)\s*\n',
            # Pattern: Name followed by address components
            r'([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)\s*\n.*(?:\d+|Apt |Unit |Building)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                potential_name = match.group(1).strip()
                if self.is_valid_name(potential_name):
                    return potential_name
        
        return None
    
    def extract_name_from_advice_of_arrival(self, text):
        """Extract name specifically from Advice of Arrival structure"""
        patterns = [
            # Look for consignee name pattern
            r'Consignee[^\n]*\n\s*([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)',
            r'Consignee[^\n]*\n\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            # Agent section might have the name
            r'Agent[^\n]*\n\s*([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)',
            r'Agent[^\n]*\n\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if self.is_valid_name(name):
                    return name
        return None
    
    def extract_name_from_customer_doc(self, text):
        """Extract name from customer document"""
        patterns = [
            r'Name[^:]*:\s*([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)',
            r'Name[^:]*:\s*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'Applicant[^:]*:\s*([A-Z][a-z]+ [A-Z][a-z]+ [A-Z][a-z]+)',
            r'Applicant[^:]*:\s*([A-Z][a-z]+ [A-Z][a-z]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if self.is_valid_name(name):
                    return name
        return None
    
    def is_valid_name(self, name):
        """Check if extracted text is a valid person name"""
        if not name:
            return False
        
        # Clean up the name - remove extra spaces and handle commas
        name_cleaned = re.sub(r'\s+', ' ', name.strip())  # Replace multiple spaces with single space
        
        # Split on comma if present (handle names like "Ivan, Asoka Welaratne")
        if ',' in name_cleaned:
            name_cleaned = name_cleaned.replace(',', ' ')
            name_cleaned = re.sub(r'\s+', ' ', name_cleaned.strip())
        
        # Must have at least 2 words
        words = name_cleaned.split()
        if len(words) < 2:
            return False
        
        # Exclude common business/location terms
        exclude_terms = [
            'Seven Seas', 'Hong Kong', 'Dublin Port', 'Advice of', 'Bill of',
            'Ever Gain', 'Notify Party', 'New South', 'Old Hospital', 
            'Little Lonsdale', 'Maunganui Road', 'Grange Manor',
            'Fengxinyuan Fenghuang', 'Tak Wai', 'Vehicle Registration',
            'Transfer of', 'Application and', 'Wanamaker House', 'Xavier House',
            'Haliday House', 'Rose Park', 'Mill Road', 'Station Road',
            'Caviar Court', 'Riverside Park', 'Gables Kill', 'Westcourt',
            'Casimir Road', 'Jinkou Road', 'Cheong Lok', 'Personal Public Service',
            'Public Service', 'Revenue Commissioners', 'Department of', 'Passport Office'
        ]
        
        if any(term in name_cleaned for term in exclude_terms):
            return False
        
        # Skip if contains numbers or common non-name words
        if re.search(r'\d|Street|Road|Avenue|Building|Plaza|Unit|Apartment|House|Court|Park|Lane|Drive', name_cleaned):
            return False
        
        # Check if it looks like a real person's name (proper capitalization)
        # Allow for some flexibility with names like "O'Brien"
        for word in words:
            if len(word) == 0:
                continue
            # Allow words that start with capital and have apostrophes
            if not (word[0].isupper() and (word[1:].islower() or "'" in word)):
                return False
        
        return True
    
    def process_multi_client_document(self, pdf_path, doc_type):
        """Process Advice of Arrivals or Bills of Lading - extract pages for each client"""
        print(f"\n--- Processing Multi-Client Document: {pdf_path.name} ---")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"Document has {total_pages} pages")
        
        # Analyze each page to find which client it belongs to
        for page_num in range(total_pages):
            text = self.extract_text_from_page(doc, page_num)
            consignee_ref, full_name = self.find_client_info_on_page(text)
            
            if consignee_ref and full_name:
                print(f"Page {page_num + 1}: {consignee_ref} - {full_name}")
                
                # Store client info and page reference
                client_key = consignee_ref
                if not self.clients[client_key]['info']:
                    self.clients[client_key]['info'] = (consignee_ref, full_name)
                
                # Add this page to the client's collection
                self.clients[client_key]['pages'].append({
                    'source_doc': pdf_path,
                    'page_num': page_num,
                    'doc_type': doc_type,
                    'doc_obj': doc  # Keep reference to the document object
                })
            else:
                print(f"Page {page_num + 1}: Could not identify client")
        
        # Don't close the document yet - we need it for page extraction
        return doc
    
    def process_customer_document(self, pdf_path):
        """Process individual customer document"""
        print(f"\n--- Processing Customer Document: {pdf_path.name} ---")
        
        # Extract consignee reference from filename if possible
        filename = pdf_path.name
        ref_match = re.search(r'(\d{3}[-/]\d{3}[-/]\d{3})', filename)
        
        if ref_match:
            consignee_ref = ref_match.group(1).replace('-', '/')
            
            # Also extract client info from document content
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            
            _, full_name = self.find_client_info_on_page(text)
            
            print(f"Customer Doc: {consignee_ref} - {full_name}")
            
            # Store customer document info - ONLY for this specific client
            client_key = consignee_ref
            if not self.clients[client_key]['info']:
                self.clients[client_key]['info'] = (consignee_ref, full_name)
            
            # Add all pages of customer document to ONLY this client
            for page_num in range(len(doc)):
                self.clients[client_key]['pages'].append({
                    'source_doc': pdf_path,
                    'page_num': page_num,
                    'doc_type': 'Customer Document',
                    'doc_obj': doc
                })
            
            return doc
        else:
            print(f"Could not extract reference from filename: {filename}")
            return None
    
    def merge_client_documents(self, client_key, client_data):
        """Merge all documents for a specific client in the correct order"""
        consignee_ref, full_name = client_data['info']
        if not consignee_ref:
            print(f"Missing consignee reference for {client_key}")
            return
        
        # If no name, create a default one
        if not full_name:
            full_name = f"Client_{consignee_ref.replace('/', '_')}"
        
        print(f"\n--- Merging documents for: {consignee_ref} - {full_name} ---")
        
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
        
        print(f"Found: {len(advice_pages)} Advice pages, {len(bill_pages)} Bill pages, {len(customer_pages)} Customer pages")
        
        # Create merged PDF in correct order: Advice → Bills → Customer
        merged_doc = fitz.open()  # Create new empty document
        
        # Add Advice of Arrivals pages
        for page_info in advice_pages:
            source_doc = page_info['doc_obj']
            page_num = page_info['page_num']
            merged_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
        
        # Add Bill of Lading pages
        for page_info in bill_pages:
            source_doc = page_info['doc_obj']
            page_num = page_info['page_num']
            merged_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
        
        # Add Customer Document pages
        for page_info in customer_pages:
            source_doc = page_info['doc_obj']
            page_num = page_info['page_num']
            merged_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
        
        # Save merged document
        # Clean filename: Name first, then reference number
        safe_ref = consignee_ref.replace('/', '-')
        safe_name = re.sub(r'[^\w\s-]', '', full_name).strip()
        
        # Format: {FullName}_{ConsigneeNumber}.pdf
        output_filename = f"{safe_name}_{safe_ref}.pdf"
        output_path = self.output_folder / output_filename
        
        merged_doc.save(str(output_path))
        merged_doc.close()
        
        print(f"✅ Saved: {output_filename}")
        print(f"   Total pages: {len(advice_pages) + len(bill_pages) + len(customer_pages)}")
        return True
    
    def process_all_documents(self):
        """Main process: analyze all PDFs and merge by client"""
        pdf_files = list(self.input_folder.glob("*.pdf"))
        
        if not pdf_files:
            print("No PDF files found!")
            return
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
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
                doc = self.process_customer_document(pdf_path)
                if doc:
                    opened_docs.append(doc)
        
        # Now merge documents for each client
        print(f"\n{'='*60}")
        print(f"MERGING DOCUMENTS FOR {len(self.clients)} CLIENTS")
        print(f"{'='*60}")
        
        for client_key, client_data in self.clients.items():
            self.merge_client_documents(client_key, client_data)
        
        # Close all opened documents
        for doc in opened_docs:
            doc.close()
        
        print(f"\n✅ Process complete! Check the '{self.output_folder.name}' folder for merged PDFs.")

# Example usage
if __name__ == "__main__":
    # Option 1: Auto-create manifest from EDI Excel file (RECOMMENDED)
    pdf_merger = PDFMerger("input_pdf", "output_pdf", edi_file="EDI.xls")
    
    # Option 2: Use existing CSV manifest
    # pdf_merger = PDFMerger("input_pdf", "output_pdf")
    
    # Option 3: Auto-create manifest from reference PDF document
    # pdf_merger = PDFMerger("input_pdf", "output_pdf", reference_doc="reference_manifest.pdf")
    
    # Option 4: No manifest at all (rely on document extraction only)
    # pdf_merger = PDFMerger("input_pdf", "output_pdf", None)
    
    # Process all documents
    pdf_merger.process_all_documents()
