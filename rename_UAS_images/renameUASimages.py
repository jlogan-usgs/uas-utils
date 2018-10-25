"""
Created on Tue May  31 16:38:07 2018

Script to rename imagery with UTC time/date format

@author: jlogan
"""
import argparse
from pathlib import Path
from tqdm import tqdm
from datetime import datetime, timedelta
from PIL import Image
from PIL.ExifTags import TAGS

#file types to process
ftypes = ['JPG', 'DNG']

def get_exif(fn):
    ret = {}
    i = Image.open(fn)
    info = i._getexif()
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
    return ret

# ===========================  BEGIN PARSER ==============================
descriptionstr = ('  Script to rename images collected with UAS camera.')

parser = argparse.ArgumentParser(description=descriptionstr, 
                                 epilog='example: run renameUASimages.py '
                                         '-dir=D:/mydir/data/images -f=2 '
                                         '-utcoffset=-8 '
                                         '-sepdir')
#input directory arg
parser.add_argument('-dir', '--input_directory', dest='indir',  
                    required=True,
                    help='input directory with images')

#flight arg
parser.add_argument('-f', '--flight_number', dest='fltnum',  
                    type=int, required=True,
                    help='flight number')

#utc offset arg
parser.add_argument('-utc', '--utc_offset', dest='utcoffset',  
                    type=int, required=True,
                    help='image tzone to utc offset in hours [example: PST to UTC = 8]')

#arg to separate files into raw and jpg dir
parser.add_argument('-sepdir', '--sep_files_dir', help='separate raw and jpg into separate dir',
    action='store_true')

#parse
args = parser.parse_args()

##check required args
#if args.utcoffset is None:
#    raise ValueError('utcoffset must be provided')
#    
#if args.fltnum is None:
#    raise ValueError('flight number must be provided')

#set var
fltnum = args.fltnum
indir = Path(args.indir)
sepdir = args.sep_files_dir
utcoffset = args.utcoffset

def new_image_name(img, utcoffset, fltnum):
    '''Formats new image name.'''
    #get image time stamp
    imgdt = datetime.strptime(Image.open(img)._getexif()[36867], '%Y:%m:%d %H:%M:%S')
    #add UTC offset to get UTC time
    imgutcdt = imgdt + timedelta(hours=utcoffset)
    #format output utc dt
    imgutcdtlabel = datetime.strftime(imgutcdt, '%Y%m%d-%H%M%S')
    outname = 'F' + f'{fltnum:02}' + '_' + imgutcdtlabel + '_' + str(img.name)
    return outname

def user_prompt(question:str):
    """ Prompts a Yes/No questions. 
    https://stackoverflow.com/questions/3041986/apt-command-line-interface-like-yes-no-input"""
    import sys
    from distutils.util import strtobool

    while True:
        sys.stdout.write(question + " [y/n]: ")
        user_input = input().lower()
        try:
            result = strtobool(user_input)
            return result
        except ValueError:
            sys.stdout.write("Please use y/n or yes/no.\n")

#Show sample rename to user
ftype = ftypes[0]
fsample = next(indir.glob('*.' + ftype))
print('Image ' + fsample.name + ' has time stamp: ' + 
      str(datetime.strptime(Image.open(fsample)._getexif()[36867], '%Y:%m:%d %H:%M:%S')) +
      '\n' + 'Image ' + fsample.name + ' will be renamed to: ' + 
      new_image_name(fsample, utcoffset, fltnum)+ '\n')

#Get confirmation to continue
if user_prompt('Do you want to rename this and all images in this directory following this pattern?'):
    #loop through ftypes
    for ftype in ftypes:
        #loop through files
        for fn in tqdm(indir.glob('*.' + ftype)):
            fn.rename(Path(fn.parent, Path(new_image_name(fn, utcoffset, fltnum))))
    