#Import the Image and ImageFilter classes from PIL (Pillow)
from PIL import Image
from PIL import ImageFilter
import math
import sys
import random
import copy

if __name__ == '__main__':


    if(len(sys.argv) < 2):
        raise Exception("error: please give an input and output image filename as a parameter, as well as a tile size (in pixels), like this: \n"
                     "python3 pichu_devil.py [input] [output] [size]")
    
    # Load an image 
    im = Image.open(sys.argv[1]).convert("RGB")
    tile_size = int(sys.argv[3])

    # pad the image out to the nearest multiple of the tile size:
    new_height = math.ceil(float(im.height) / tile_size) * tile_size
    new_width = math.ceil(float(im.width) / tile_size) * tile_size
    
    # Create a new blank color image the same size as the input
    padded_im = Image.new(im.mode, (new_width, new_height), color=(255,255,255))
    padded_im.paste(im, (0,0))
    padded_im.save("padded.png")
    
    # now create scrambled image
    scrambled_im = Image.new(im.mode, (new_width, new_height))    
    coords = [ (x,y,x+tile_size,y+tile_size) for x in range(0, new_width, tile_size) for y in range(0, new_height, tile_size) ]
    orig_coords = copy.deepcopy(coords)
    random.shuffle(coords)
    for (d,s) in zip(coords, orig_coords):
        scrambled_im.paste(padded_im.crop(s), d)
    
    # Save the image
    scrambled_im.save(sys.argv[2])
