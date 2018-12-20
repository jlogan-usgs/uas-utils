# -*- coding: utf-8 -*-
"""
Created on Thu Dec 20 11:12:41 2018

Removes *.*_original files after 'geotag-with-gpx.py'

example: runfile('geotag-with-gpx.py', args='-dir=D:/temp/testrename -f=2 -utc=0 -sepdir')
@author: jlogan
"""

import argparse
from pathlib import Path
import os


#Inputs (these will be used if not entered in command line)
imgdirstr = 'D:/temp/test_geotag'

# ===========================  BEGIN ARGUMENT PARSER ==============================
descriptionstr = ('  Script to remove "*.*_original" files after "geotag-with-gpx.py"')
parser = argparse.ArgumentParser(description=descriptionstr, 
                                 epilog='example: run remove-original-after-geotag.py '
                                         '-imgdir=D:/mydir/data/images ')
#input image directory arg
parser.add_argument('-imgdir', '--image_directory', dest='imgdir_arg',  
                    required=False,
                    help='input directory with image files or directories of images')

#parse
args = parser.parse_args()
# ===========================  END ARGUMENT PARSER ==============================

#if arguments supplied via command line, use values to set inputs, otherwise use
#inputs set in script above
if args.imgdir_arg is not None:
    imgdirstr = args.imgdir_arg

#Set path objects
imgdir = Path(imgdirstr)

#check that paths exist
try:
    if not imgdir.exists():
        raise Exception(f'{str(imgdir.absolute())} dir does not exist, stopping execution')
except:
        raise Exception(f'{str(imgdir.absolute())} dir does not exist, stopping execution')

n = 0

#recursively delete *_original files
for fn in imgdir.glob('**/*.*_original'):
    try:
        print(f'Deleting {fn}')
        os.remove(fn)
        n += 1
    except OSError:  
        pass

print(f'Deleted {n} files.')


    
    