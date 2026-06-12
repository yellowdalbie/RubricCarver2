import sys
from PIL import Image

def main():
    img_path = "그림1_절차흐름도.png"
    img = Image.open(img_path).convert("L")
    w, h = img.size
    
    # Calculate row-wise darkness (number of pixels < 250)
    row_darkness = []
    for y in range(h):
        dark_pixels = sum(1 for x in range(w) if img.getpixel((x, y)) < 240)
        row_darkness.append(dark_pixels)
    
    # Find the text block
    text_start = -1
    for y in range(h):
        if row_darkness[y] > 10:
            text_start = y
            break
            
    if text_start == -1:
        print("No dark pixels found.")
        return
        
    text_end = -1
    for y in range(text_start + 1, h):
        if row_darkness[y] <= 5: # gap
            text_end = y
            break
            
    diagram_start = -1
    for y in range(text_end + 1, h):
        if row_darkness[y] > 10:
            diagram_start = y
            break
            
    if diagram_start != -1 and text_end != -1:
        print(f"Text block: {text_start} to {text_end}")
        print(f"Diagram starts at: {diagram_start}")
        crop_y = (text_end + diagram_start) // 2
        print(f"Cropping at y={crop_y}")
        
        orig = Image.open(img_path)
        cropped = orig.crop((0, crop_y, w, h))
        cropped.save("figure_1.png") # save as the final figure_1.png
        print("Successfully cropped and saved as figure_1.png")
    else:
        print("Could not find clear separation between text and diagram.")
        print(f"text_start={text_start}, text_end={text_end}, diagram_start={diagram_start}")
        
if __name__ == "__main__":
    main()
