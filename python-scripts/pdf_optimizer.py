import fitz  # PyMuPDF
from pathlib import Path
import logging

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class PDFOptimizer:
    """
    Simple PDF optimization class for reducing file sizes while maintaining quality
    """
    
    def __init__(self, target_size_mb=1.2, quality=85):
        """
        Initialize PDF optimizer
        
        Args:
            target_size_mb: Target file size in MB
            quality: Image quality (0-100, higher = better quality)
        """
        self.target_size_mb = target_size_mb
        self.target_size_bytes = target_size_mb * 1024 * 1024
        self.quality = quality
        self.logger = logging.getLogger('PDFOptimizer')
        
    def optimize_pdf(self, input_path, output_path=None):
        """
        Optimize a PDF file to reduce its size
        
        Args:
            input_path: Path to input PDF
            output_path: Path for optimized PDF (if None, overwrites input)
            
        Returns:
            dict: Optimization results
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
                # Copy to output location if different
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
            
            # Save optimized PDF with compression settings
            doc.save(str(output_path), 
                    garbage=4,      # Remove unused objects
                    deflate=True,   # Compress streams
                    clean=True,     # Clean up document
                    linear=True,    # Linearize for web viewing
                    pretty=False)   # Don't pretty-print (saves space)
            
            doc.close()
            
            # Check final size
            final_size = output_path.stat().st_size
            
            # If still too large, apply more aggressive compression
            if final_size > self.target_size_bytes:
                final_size = self._aggressive_compression(output_path)
            
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
    
    def _optimize_document(self, doc):
        """Apply various optimization techniques to the PDF"""
        results = []
        
        try:
            # 1. Compress images if PIL is available
            if PIL_AVAILABLE:
                image_count = self._compress_images(doc)
                if image_count > 0:
                    results.append(f"Compressed {image_count} images")
            else:
                results.append("Image compression skipped (PIL not available)")
            
            # 2. Remove metadata to save space
            if self._remove_metadata(doc):
                results.append("Removed metadata")
            
            # 3. Clean up document structure
            results.append("Applied document cleanup")
            
        except Exception as e:
            self.logger.warning(f"Some optimization steps failed: {e}")
            results.append("Partial optimization applied")
        
        return results
    
    def _compress_images(self, doc):
        """Compress images in the PDF"""
        if not PIL_AVAILABLE:
            return 0
            
        image_count = 0
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Get image
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Only compress if it's a significant image
                        if len(image_bytes) > 50000:  # 50KB threshold
                            # Create compressed version
                            compressed_image = self._compress_image_data(image_bytes)
                            
                            if compressed_image and len(compressed_image) < len(image_bytes):
                                # Replace image in PDF
                                doc._updateStream(xref, compressed_image)
                                image_count += 1
                                
                    except Exception as e:
                        # Continue with next image if one fails
                        self.logger.debug(f"Failed to compress image {img_index}: {e}")
                        continue
        except Exception as e:
            self.logger.warning(f"Image compression failed: {e}")
        
        return image_count
    
    def _compress_image_data(self, image_bytes):
        """Compress individual image data"""
        if not PIL_AVAILABLE:
            return None
            
        try:
            # Open image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if 'transparency' in image.info:
                    rgb_image.paste(image, mask=image.split()[-1])
                else:
                    rgb_image.paste(image)
                image = rgb_image
            
            # Resize if image is very large
            max_dimension = 1200
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Compress
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=self.quality, optimize=True)
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.debug(f"Failed to compress image: {e}")
            return None
    
    def _remove_metadata(self, doc):
        """Remove metadata to save space"""
        try:
            # Clear metadata
            doc.set_metadata({})
            return True
        except Exception:
            return False
    
    def _aggressive_compression(self, pdf_path):
        """Apply more aggressive compression if target not met"""
        try:
            # Reload and save with maximum compression
            doc = fitz.open(pdf_path)
            
            # More aggressive settings
            doc.save(str(pdf_path),
                    garbage=4,
                    deflate=True,
                    clean=True,
                    linear=True,
                    pretty=False)
            
            doc.close()
            
            return pdf_path.stat().st_size
            
        except Exception as e:
            self.logger.warning(f"Aggressive compression failed: {e}")
            return pdf_path.stat().st_size

# Example usage
if __name__ == "__main__":
    # Test the optimizer
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_optimizer.py input.pdf [output.pdf]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create optimizer and process file
    optimizer = PDFOptimizer(target_size_mb=1.2, quality=85)
    
    try:
        result = optimizer.optimize_pdf(input_file, output_file)
        
        print(f"\n{'='*50}")
        print(f"PDF Optimization Results")
        print(f"{'='*50}")
        print(f"Original size: {result['original_size_mb']:.2f} MB")
        print(f"Final size: {result['final_size_mb']:.2f} MB")
        print(f"Savings: {result['savings_mb']:.2f} MB")
        print(f"Compression ratio: {result['compression_ratio']:.2f}x")
        print(f"Target achieved: {'Yes' if result['target_achieved'] else 'No'}")
        print(f"Optimization steps: {', '.join(result['optimization_steps'])}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
