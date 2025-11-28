import shutil
from pathlib import Path
from PIL import Image
import replace_images

def test_image_resizing():
    # Create a dummy large image
    large_img_path = Path("test_large_image.png")
    output_img_path = Path("test_output_image.png")
    
    width, height = 2000, 1500
    img = Image.new("RGB", (width, height), color="red")
    img.save(large_img_path)
    
    print(f"Created large image: {large_img_path} ({width}x{height})")
    
    # Run the conversion
    replace_images.ImageConverter.save_as_png(large_img_path, output_img_path)
    
    # Verify the output
    with Image.open(output_img_path) as out_img:
        out_width, out_height = out_img.size
        print(f"Output image size: {out_width}x{out_height}")
        
        assert out_width <= 1024 and out_height <= 1024, "Image was not resized correctly"
        assert out_width == 1024, "Width should be 1024"
        expected_height = int(1500 * (1024 / 2000))
        assert out_height == expected_height, f"Height should be {expected_height}, got {out_height}"
        
    print("Test passed: Image resized correctly.")
    
    # Cleanup
    if large_img_path.exists():
        large_img_path.unlink()
    if output_img_path.exists():
        output_img_path.unlink()

if __name__ == "__main__":
    test_image_resizing()
