import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
from pathlib import Path
import threading
from pdf_merger import PDFMerger  # Import your existing code

class PDFMergerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Merger - Seven Seas Worldwide")
        self.root.geometry("800x600")
        
        # Variables to store file paths
        self.edi_file_path = tk.StringVar()
        self.advice_file_path = tk.StringVar()
        self.bill_files = []
        self.customer_files = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="PDF Document Merger", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # EDI File Section
        ttk.Label(main_frame, text="1. Select EDI File (.xls):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.edi_file_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_edi_file).grid(row=1, column=2)
        
        # Advice of Arrival Section
        ttk.Label(main_frame, text="2. Select Advice of Arrival (.pdf):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.advice_file_path, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_advice_file).grid(row=2, column=2)
        
        # Bills of Lading Section
        ttk.Label(main_frame, text="3. Select Bills of Lading (.pdf files):").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # Bills of Lading listbox with scrollbar
        bill_frame = ttk.Frame(main_frame)
        bill_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        
        self.bill_listbox = tk.Listbox(bill_frame, height=4)
        bill_scrollbar = ttk.Scrollbar(bill_frame, orient=tk.VERTICAL, command=self.bill_listbox.yview)
        self.bill_listbox.configure(yscrollcommand=bill_scrollbar.set)
        
        self.bill_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        bill_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        bill_frame.columnconfigure(0, weight=1)
        
        # Bills of Lading buttons
        bill_btn_frame = ttk.Frame(main_frame)
        bill_btn_frame.grid(row=5, column=0, columnspan=3, pady=5)
        
        ttk.Button(bill_btn_frame, text="Add Bills of Lading", 
                  command=self.browse_bill_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(bill_btn_frame, text="Clear Bills List", 
                  command=self.clear_bill_files).pack(side=tk.LEFT, padx=5)
        
        # Customer Documents Section
        ttk.Label(main_frame, text="4. Select Customer Documents:").grid(row=6, column=0, sticky=tk.W, pady=(15, 5))
        
        # Customer files listbox with scrollbar
        customer_frame = ttk.Frame(main_frame)
        customer_frame.grid(row=7, column=0, columnspan=3, pady=5, sticky=(tk.W, tk.E))
        
        self.customer_listbox = tk.Listbox(customer_frame, height=6)
        customer_scrollbar = ttk.Scrollbar(customer_frame, orient=tk.VERTICAL, command=self.customer_listbox.yview)
        self.customer_listbox.configure(yscrollcommand=customer_scrollbar.set)
        
        self.customer_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        customer_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        customer_frame.columnconfigure(0, weight=1)
        
        # Customer documents buttons
        customer_btn_frame = ttk.Frame(main_frame)
        customer_btn_frame.grid(row=8, column=0, columnspan=3, pady=5)
        
        ttk.Button(customer_btn_frame, text="Add Customer PDFs", 
                  command=self.browse_customer_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(customer_btn_frame, text="Clear List", 
                  command=self.clear_customer_files).pack(side=tk.LEFT, padx=5)
        
        # Output directory section
        ttk.Label(main_frame, text="5. Output Directory:").grid(row=9, column=0, sticky=tk.W, pady=(20, 5))
        self.output_dir_path = tk.StringVar(value=str(Path.cwd() / "merged_output"))
        ttk.Entry(main_frame, textvariable=self.output_dir_path, width=50).grid(row=9, column=1, padx=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_output_dir).grid(row=9, column=2)
        
        # Process button
        self.process_btn = ttk.Button(main_frame, text="🚀 Merge Documents", 
                                     command=self.start_processing, style='Accent.TButton')
        self.process_btn.grid(row=10, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=11, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Status text
        self.status_text = tk.Text(main_frame, height=10, width=80)
        status_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.grid(row=12, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        status_scrollbar.grid(row=12, column=2, sticky=(tk.N, tk.S), pady=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(12, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def browse_edi_file(self):
        filename = filedialog.askopenfilename(
            title="Select EDI File",
            filetypes=[("Excel files", "*.xls *.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.edi_file_path.set(filename)
            
    def browse_advice_file(self):
        filename = filedialog.askopenfilename(
            title="Select Advice of Arrival PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.advice_file_path.set(filename)
            
    def browse_bill_files(self):
        filenames = filedialog.askopenfilenames(
            title="Select Bills of Lading PDFs",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        for filename in filenames:
            if filename not in self.bill_files:
                self.bill_files.append(filename)
                self.bill_listbox.insert(tk.END, Path(filename).name)
                
    def clear_bill_files(self):
        self.bill_files.clear()
        self.bill_listbox.delete(0, tk.END)
            
    def browse_customer_files(self):
        filenames = filedialog.askopenfilenames(
            title="Select Customer Documents",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        for filename in filenames:
            if filename not in self.customer_files:
                self.customer_files.append(filename)
                self.customer_listbox.insert(tk.END, Path(filename).name)
                
    def clear_customer_files(self):
        self.customer_files.clear()
        self.customer_listbox.delete(0, tk.END)
        
    def browse_output_dir(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir_path.set(dirname)
            
    def log_message(self, message):
        """Add message to status text box"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update()
        
    def validate_inputs(self):
        """Check if all required files are selected"""
        if not self.edi_file_path.get():
            messagebox.showerror("Error", "Please select an EDI file")
            return False
            
        if not self.advice_file_path.get():
            messagebox.showerror("Error", "Please select an Advice of Arrival PDF")
            return False
            
        if not self.bill_files:
            messagebox.showerror("Error", "Please select at least one Bills of Lading PDF")
            return False
            
        return True
        
    def start_processing(self):
        """Start the PDF processing in a separate thread"""
        if not self.validate_inputs():
            return
            
        # Disable the process button
        self.process_btn.config(state='disabled')
        self.progress.start()
        
        # Clear status text
        self.status_text.delete(1.0, tk.END)
        
        # Start processing in a separate thread
        thread = threading.Thread(target=self.process_documents)
        thread.daemon = True
        thread.start()
        
    def process_documents(self):
        """Main processing function"""
        try:
            self.log_message("🚀 Starting PDF processing...")
            
            # Create temporary working directories
            temp_input = Path("temp_input")
            output_dir = Path(self.output_dir_path.get())
            
            # Clean and create directories
            if temp_input.exists():
                shutil.rmtree(temp_input)
            temp_input.mkdir()
            output_dir.mkdir(exist_ok=True)
            
            self.log_message(f"📁 Created working directories")
            
            # Copy files to input directory
            self.log_message("📋 Copying input files...")
            
            # Copy EDI file to working directory
            edi_dest = Path(self.edi_file_path.get()).name
            shutil.copy2(self.edi_file_path.get(), edi_dest)
            self.log_message(f"   ✅ Copied EDI file: {edi_dest}")
            
            # Copy Advice of Arrival
            advice_dest = temp_input / "Advice_of_Arrival.pdf"
            shutil.copy2(self.advice_file_path.get(), advice_dest)
            self.log_message(f"   ✅ Copied Advice of Arrival")
            
            # Copy Bills of Lading files
            for i, bill_file in enumerate(self.bill_files):
                bill_dest = temp_input / f"Bill_of_Lading_{i+1}.pdf"
                shutil.copy2(bill_file, bill_dest)
                self.log_message(f"   ✅ Copied: {Path(bill_file).name}")
            
            # Copy customer documents
            for customer_file in self.customer_files:
                customer_dest = temp_input / Path(customer_file).name
                shutil.copy2(customer_file, customer_dest)
                self.log_message(f"   ✅ Copied: {Path(customer_file).name}")
            
            self.log_message("🔧 Initializing PDF Merger...")
            
            # Initialize PDF Merger with EDI file
            pdf_merger = PDFMerger(str(temp_input), str(output_dir), edi_file=edi_dest)
            
            self.log_message("⚙️ Processing documents...")
            
            # Redirect print statements to our log
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            try:
                # Process documents
                pdf_merger.process_all_documents()
                
                # Get the output
                output = sys.stdout.getvalue()
                
                # Restore stdout
                sys.stdout = old_stdout
                
                # Display the output
                for line in output.split('\n'):
                    if line.strip():
                        self.log_message(line)
                
            except Exception as e:
                sys.stdout = old_stdout
                raise e
            
            # Clean up temp directory
            shutil.rmtree(temp_input)
            if Path(edi_dest).exists():
                Path(edi_dest).unlink()
            
        self.log_message("✅ Processing complete!")
        self.log_message(f"📁 Output files saved to: {output_dir}")
        self.log_message("ℹ️ Note: Use your form filling app for completing customer documents")

        # Show completion message
        self.root.after(0, lambda: messagebox.showinfo(
            "Success", 
            f"PDF Merging complete!\n\nMerged PDFs saved to:\n{output_dir}\n\nUse your form filling app to complete customer documents."
            ))
            
        except Exception as e:
            error_msg = f"❌ Error during processing: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            
        finally:
            # Re-enable the button and stop progress bar
            self.root.after(0, self.finish_processing)
            
    def finish_processing(self):
        """Clean up after processing"""
        self.progress.stop()
        self.process_btn.config(state='normal')

def main():
    root = tk.Tk()
    app = PDFMergerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
