def optimize_pdf(self, input_path, output_path=None):
    """
    Optimize a PDF file to reduce its size
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Get original file size
    original_size = input_path.stat().st_size
    
    if original_size <= self.target_size_bytes:
        # File already under target size
        if output_path != input_path:
            output_path.write_bytes(input_path.read_bytes())
        
        self.logger.info(f"PDF already optimized: {input_path.name} ({original_size / (1024*1024):.2f}MB)")
        
        return {
            'optimized': False,
            'reason': 'File already under target size',
            'original_size_mb': original_size / (1024 * 1024),
            'final_size_mb': original_size / (1024 * 1024),
            'compression_ratio': 1.0,
            'savings_mb': 0
        }
    
    try:
        self.logger.info(f"Optimizing PDF: {input_path.name} ({original_size / (1024*1024):.2f}MB)")
        
        # Open PDF document
        doc = fitz.open(input_path)
        
        # Apply optimization strategies
        optimization_steps = self._optimize_document(doc)
        
        # FIX: Use a temporary file instead of overwriting the original
        temp_path = output_path.with_suffix('.temp.pdf')
        
        # Save optimized PDF with compression settings
        doc.save(str(temp_path), 
                garbage=4,      # Remove unused objects
                deflate=True,   # Compress streams
                clean=True,     # Clean up document
                linear=True,    # Linearize for web viewing
                pretty=False)   # Don't pretty-print (saves space)
        
        doc.close()
        
        # Replace original with optimized version
        if temp_path.exists():
            temp_path.replace(output_path)
        
        # Check final size
        final_size = output_path.stat().st_size
        
        # Calculate results
        compression_ratio = original_size / final_size if final_size > 0 else 1
        savings_mb = (original_size - final_size) / (1024 * 1024)
        
        self.logger.info(f"Optimization complete: {final_size / (1024*1024):.2f}MB (saved {savings_mb:.2f}MB)")
        
        return {
            'optimized': True,
            'original_size_mb': original_size / (1024 * 1024),
            'final_size_mb': final_size / (1024 * 1024),
            'compression_ratio': compression_ratio,
            'savings_mb': savings_mb,
            'target_achieved': final_size <= self.target_size_bytes,
            'optimization_steps': optimization_steps
        }
        
    except Exception as e:
        self.logger.error(f"PDF optimization failed: {str(e)}")
        raise Exception(f"PDF optimization failed: {str(e)}")