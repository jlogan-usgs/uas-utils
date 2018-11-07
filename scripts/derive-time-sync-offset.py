# -*- coding: utf-8 -*-
"""
Created on Wed Nov  7 11:02:36 2018

Script to speed up deriving camera time to UTC time offset.
Will loop through dir of images and create a csv file with imagename, 
datetime from exif.  User will need to add true utc time (from image content)
in a separate application/image viewer.

example: runfile('derive-time-sync-offset.py', args='-dir=T:/UAS/2018-676-FA/SfM_img/RA_TIMESYNC')

@author: jlogan
"""
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import exifread

#file types to use
ftypes = ['JPG']

#using exifread which works for DNG and JPG
def get_dt_orignal(fn):
    '''Gets DateTimeOriginal value from EXIF'''
    with open(fn, 'rb') as i:
        tags = exifread.process_file(i)
    dt_orig = str(tags.get('EXIF DateTimeOriginal'))
    return dt_orig

# ===========================  BEGIN PARSER ==============================
descriptionstr = ('  Script to rename images collected with UAS camera.')
parser = argparse.ArgumentParser(description=descriptionstr, 
                                 epilog='example: run derive-time-sync-offset.py '
                                         '-dir=D:/mydir/data/timesyncimages ')
#input directory arg
parser.add_argument('-dir', '--input_directory', dest='indir',  
                    required=True,
                    help='input directory with time sync images')

#parse
args = parser.parse_args()

#set var
indir = Path(args.indir)

#make dataframe
columns = ['IMAGENAME','CAMERATIME', 'UTCTIME', 'IMAGE_TO_UTC_OFFSET']
df = pd.DataFrame(columns=columns)


#loop through files, append to df
for ftype in ftypes:
    for fn in indir.glob('*.' + ftype):
        #get image taken datetime from exif
        imgdt = datetime.strptime(get_dt_orignal(fn), '%Y:%m:%d %H:%M:%S')
        
        df = df.append({
                'IMAGENAME': fn,
                'CAMERATIME':  imgdt,
                'UTCTIME': '',
                'IMAGE_TO_UTC_OFFSET':  '',
                }, ignore_index=True)
    
#write to csv (sort by name first)
df.sort_values('IMAGENAME').to_csv(indir.joinpath('cameratimeoffset.csv'), index=False)    
