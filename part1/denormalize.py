#
# denormalize.py : Apply a rotation and scaling to an image
#
# D. Crandall, Jan 2024
#

from PIL import Image
from PIL import ImageFilter
import math
import sys
import random
import copy

if __name__ == '__main__':

    if(len(sys.argv) < 2):
        raise Exception("error: please give an input and output image filename as parameters, as well as rotation angle (in degrees) and a scaling factor: \n"
                     "python3 pichu_devil.py [input] [output] [angle] [factor]")
    
    # Load an image 
    im = Image.open(sys.argv[1]).convert('RGB')
    angle = float(sys.argv[3])
    factor = float(sys.argv[4])

    im = im.resize((int(im.width*factor), int(im.height*factor)), resample=Image.BICUBIC)
    im = im.rotate(angle, expand=True, resample=Image.BICUBIC,  fillcolor=(255,255,255), center=(int(im.width/2), int(im.height/2)))
    
    # Save the image
    im.save(sys.argv[2])
