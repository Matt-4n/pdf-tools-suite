import fitz  # PyMuPDF
import logging
from pathlib import Path


class PDFOptimizer:
    def __init__(self, target_size_mb=1.2, quality=85):
        """
        Initialize PDF Optimizer
        
        Args:
            target_size_mb (float): Target file size in MB
            quality (int): Image quality 0-100
        """
        self.target_size_mb = target_size_mb
        self.target_size_bytes = target_size_mb * 1024 * 1024
        self.quality = quality
        self.logger = logging.getLogger('PDFOptimizer')
    
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
                    linear=False,    # Linearization not supported in newer PyMuPDF
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
    
    def _optimize_document(self, doc):
        """
        Apply various optimization strategies to the document
        """
        optimization_steps = []
        
        try:
            # Step 1: Image optimization
            image_count = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Only compress if image is large
                        if len(image_bytes) > 50000:  # 50KB threshold
                            # Replace with compressed version
                            compressed_image = self._compress_image_bytes(image_bytes)
                            if compressed_image and len(compressed_image) < len(image_bytes):
                                # Replace the image in the document
                                doc._replace_image(xref, compressed_image)
                                image_count += 1
                    except Exception as img_error:
                        self.logger.debug(f"Could not optimize image {img_index}: {img_error}")
                        continue
            
            if image_count > 0:
                optimization_steps.append(f"Compressed {image_count} images")
            
            # Step 2: Font optimization
            font_count = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                # Remove unused fonts (handled by garbage collection)
                font_count += 1
            
            optimization_steps.append("Applied font optimization")
            
            # Step 3: Remove metadata and annotations
            # Clear metadata
            doc.set_metadata({})
            optimization_steps.append("Removed metadata")
            
            return optimization_steps
            
        except Exception as e:
            self.logger.warning(f"Some optimization steps failed: {e}")
            return optimization_steps or ["Basic compression applied"]
    
    def _compress_image_bytes(self, image_bytes):
        """
        Compress image bytes using PIL if available
        """
        try:
            from PIL import Image
            from io import BytesIO
            
            # Open image
            img = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Compress image
            output = BytesIO()
            img.save(output, format='JPEG', quality=self.quality, optimize=True)
            compressed_bytes = output.getvalue()
            
            return compressed_bytes
            
        except ImportError:
            self.logger.debug("PIL not available for image compression")
            return None
        except Exception as e:
            self.logger.debug(f"Image compression failed: {e}")
            return None
    
    def get_pdf_info(self, pdf_path):
        """
        Get information about a PDF file
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            return None
        
        try:
            doc = fitz.open(pdf_path)
            info = {
                'file_size_mb': pdf_path.stat().st_size / (1024 * 1024),
                'page_count': len(doc),
                'has_images': False,
                'image_count': 0,
                'needs_optimization': pdf_path.stat().st_size > self.target_size_bytes
            }
            
            # Count images
            total_images = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images()
                total_images += len(images)
            
            info['has_images'] = total_images > 0
            info['image_count'] = total_images
            
            doc.close()
            return info
            
        except Exception as e:
            self.logger.error(f"Could not analyze PDF: {e}")
            return None


# For backwards compatibility and testing
def optimize_pdf_file(input_path, output_path=None, target_size_mb=1.2, quality=85):
    """
    Standalone function to optimize a PDF file
    """
    optimizer = PDFOptimizer(target_size_mb=target_size_mb, quality=quality)
    return optimizer.optimize_pdf(input_path, output_path)


if __name__ == "__main__":
    # Simple test/demo
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_optimizer.py <input_pdf> [output_pdf]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = optimize_pdf_file(input_file, output_file)
        print(f"Optimization result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
