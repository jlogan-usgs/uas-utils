"""
Created on Tue May  31 16:38:07 2018

Script to rename imagery with flight prefix and UTC time/date from EXIF

exampled: runfile('renameUASimages.py', args='-dir=D:/temp/testrename -f=2 -utc=0 -sepdir')
@author: jlogan
"""
import argparse
import sys
from pathlib import Path
import shutil
from tqdm import tqdm
from datetime import datetime, timedelta
import exifread

#file types to process
ftypes = ['JPG', 'DNG']

#using exifread which works for DNG and JPG
def get_dt_orignal(fn):
    '''Gets DateTimeOriginal value from EXIF'''
    with open(fn, 'rb') as i:
        tags = exifread.process_file(i)
    dt_orig = str(tags.get('EXIF DateTimeOriginal'))
    return dt_orig

def new_image_name(img, utcoffset, fltnum):
    '''Formats new image name.'''
    #get image time stamp
    #PIL doesn't work for DNG
    #imgdt = datetime.strptime(Image.open(img)._getexif()[36867], '%Y:%m:%d %H:%M:%S')  
    #using exifread instead
    imgdt = datetime.strptime(get_dt_orignal(img), '%Y:%m:%d %H:%M:%S')
    #add UTC offset to get UTC time
    imgutcdt = imgdt + timedelta(hours=utcoffset)
    #format output utc dt, using ISO 8601 format
    #imgutcdtlabel = datetime.strftime(imgutcdt, '%Y%m%d-%H%M%S')
    imgutcdtlabel = datetime.strftime(imgutcdt, '%Y%m%dT%H%M%SZ')
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

#set var
fltnum = args.fltnum
indir = Path(args.indir)
sepdir = args.sep_files_dir
utcoffset = args.utcoffset

#Show sample rename to user
ftype = ftypes[0]
fsample = next(indir.glob('*.' + ftype))
print('Image ' + fsample.name + ' has time stamp: ' + 
      str(datetime.strptime(get_dt_orignal(fsample), '%Y:%m:%d %H:%M:%S')) +
      '\n' + 'Image ' + fsample.name + ' will be renamed to: ' + 
      new_image_name(fsample, utcoffset, fltnum)+ '\n')

#Get confirmation to continue
if user_prompt('Do you want to rename this and all images in this directory following this pattern?'):
    #loop through ftypes
    for ftype in ftypes:
        #loop through files
        for fn in tqdm(indir.glob('*.' + ftype)):
            fn.rename(Path(fn.parent, Path(new_image_name(fn, utcoffset, fltnum))))
else:
    print('Terminating script.')
    sys.exit()
                
            
#move to separate directories if specified
if sepdir:
    for ftype in ftypes:
        newdir = Path(indir, ftype.lower())
        newdir.mkdir()
        for fn in indir.glob('*.' + ftype):
            shutil.move(fn, Path(newdir, fn.name))
        
    