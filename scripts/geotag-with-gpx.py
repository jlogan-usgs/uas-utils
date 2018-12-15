# -*- coding: utf-8 -*-
"""
Created on Wed Nov  7 13:42:23 2018

Script to geotag UAS imagery with GPX file created from Mission Planner from data flash BIN file from 3DR Solo.

example: runfile('geotag-with-gpx.py', args='-dir=D:/temp/testrename -f=2 -utc=0 -sepdir')
@author: jlogan
"""

#NOT FUNCTIONAL.


import argparse
import sys
from pathlib import Path
import shutil
from tqdm import tqdm
from datetime import datetime, timedelta
import exifread
import numpy as np
from lxml import etree
import pandas as pd
import utm

PYEXIFTOOLPATH = r'D:/jloganPython/pyexiftool'
#append path with pyexiftool
sys.path.append(PYEXIFTOOLPATH)

gpxdirstr = 'T:/UAS/2018-676-FA/tlogs/yellow/aircraft/gpx'
imgdirstr = 'D:/temp/testrename/jpg'

gpxdir = Path(gpxdirstr)
imgdir = Path(imgdirstr)

ftypes = ['JPG', 'DNG']  #file types to geotag
max_gps_err_per_sec_meters = 25 #cutoff to determine if there are overlapping gpx files in gpx batch
max_time_offset = 10 #max acceptable difference between GPX time and image time

cam_to_utc_adjust_sec = 0 #Number of seconds (+-) to adjust camera time to get to accurate UTC time

#using exifread which works for DNG and JPG
def get_dt_original(fn):
    '''Gets DateTimeOriginal value from EXIF'''
    with open(fn, 'rb') as i:
        tags = exifread.process_file(i)
    dt_orig = str(tags.get('EXIF DateTimeOriginal'))
    return dt_orig

def m_per_deg_lat(latdeg):
    '''Calculates meters per degree of latitude at latdeg
       from: https://en.wikipedia.org/wiki/Geographic_coordinate_system#Expressing_latitude_and_longitude_as_linear_units
    '''
    m_at_lat = 111132.954 - 559.822 * np.cos(np.deg2rad(2.0 * latdeg)) + 1.175 * np.cos(np.deg2rad(4.0 * latdeg)) - 0.0023 * np.cos(np.deg2rad(6.0 * latdeg))
    return m_at_lat

def m_per_deg_lon(latdeg):
    '''Calculates meters per degree of longitude at latdeg
       from: https://en.wikipedia.org/wiki/Geographic_coordinate_system#Expressing_latitude_and_longitude_as_linear_units
    '''
    m_at_lon = 111412.84 * np.cos(np.deg2rad(latdeg)) - 93.5 * np.cos(np.deg2rad(3.0 * latdeg)) + 0.118 * np.cos(np.deg2rad(5.0 * latdeg))
    return m_at_lon   


#def getUTMs(row):
#    '''Get UTM coords from lat,lon using utm library.
#       from: https://stackoverflow.com/questions/30014684/pandas-apply-utm-function-to-dataframe-columns
#    '''
#    tup = utm.from_latlon(row['lat'], row['lon'])
#    return pd.Series(tup[:2])


def nearest(items, pivot):
    #from: https://stackoverflow.com/questions/32237862/find-the-closest-date-to-a-given-date
    return min(items, key=lambda x: abs(x - pivot))

def nearest_ind(items, pivot):
    #from: https://stackoverflow.com/questions/32237862/find-the-closest-date-to-a-given-date
    time_diff = np.abs([date - pivot for date in items])
    return time_diff.argmin(0)


def mp_gpx_tag_to_pdseries(tree, namespace, tag):
    """
    from: https://github.com/sackerman-usgs/UAS_processing/blob/master/UAS_GPXandJPG_processing.ipynb
    # Extract tag value from GPX file as pandas series
    First, get the element list.
    """
    elist = tree.xpath('./def:trk//def:trkpt//def:'+tag, namespaces=namespace)
    ser = pd.Series([e.text for e in elist], name=tag)
    return(ser)
    
def mp_gpx_to_df(gpxfile, namespace):
    """
    Adapted from: https://github.com/sackerman-usgs/UAS_processing/blob/master/UAS_GPXandJPG_processing.ipynb
    """
    # Parse GPX
    tree = etree.parse(gpxfile)
    
    # Extract latitude and longitude to initialize GPX dataframe
    namespace = {'def': namespace}
    elist = tree.xpath('./def:trk//def:trkpt',namespaces=namespace)
    gpxdf = pd.DataFrame([e.values() for e in elist], columns=['lat', 'lon']).apply(pd.to_numeric)
    
    # Extract each tag (including time) and add to dataframe
    taglist = ['time', 'ele', 'course', 'roll', 'pitch', 'mode']
    for tag in taglist:
        gpxdf = gpxdf.join(pd.to_numeric(mp_gpx_tag_to_pdseries(tree, namespace, tag), errors='ignore'))
    
    return(gpxdf)
    
#instatiate empty df to store all gpx data
gpxdf = pd.DataFrame()

#load all gpx file in gpxdir into one df
for fn in gpxdir.glob('*.gpx'):
    print('Loading ' + str(fn.resolve()) + ' ...')
    gpxdf = pd.concat([gpxdf, mp_gpx_to_df(str(fn.resolve()), 'http://www.topografix.com/GPX/1/1')])
    
#convert datetime to pandas datetime dtype in UTC, drop orig time column.
#UTC conversion happens automatically
gpxdf['dt'] = pd.to_datetime(gpxdf['time'], format='%Y-%m-%dT%H:%M:%S')
gpxdf.drop(columns=['time'])

#gpx files have > 1 row per second (duplicate time stamps).  
##project lat/lon to utm to determine how close points with duplicate time stamp are in meters
#gpxdf[['easting','northing']] = gpxdf.apply(getUTMs , axis=1)

#ensure that duplicates are close together spatially, 
#then calc mean lat/long/elev for each
latdf = gpxdf.groupby('dt')['lat'].agg(['max','min'])
latdf['diff_deg'] = np.abs(latdf['max']-latdf['min'])
#calc approx. dist. in meters 
latdf['diff_m'] = latdf['diff_deg'] * m_per_deg_lat(latdf['max'])

londf = gpxdf.groupby('dt')['lon'].agg(['max','min'])
londf['diff_deg'] = np.abs(londf['max']-londf['min'])
#calc approx. dist. in meters
londf['diff_m'] = londf['diff_deg'] * m_per_deg_lon(londf['max'])

#ensure that neither lat or lon change more than 'max_gps_err_per_sec_meters' in each 
#second.  If they do, this indicates that there may be overlapping gpx files (from two GPS units?)
if any(i >= max_gps_err_per_sec_meters for i in [latdf.diff_m.abs().max(), londf.diff_m.abs().max()]):
    raise ValueError(f'Coordinates in gpx files varied by more than {max_gps_err_per_sec_meters} meters within one second interval. Possible overlapping gpx files. Stopping execution.')
    
# if all good, groupby dt and derive mean coordinates into new 1 Hz df
gpx1hzdf = gpxdf.groupby('dt', as_index=False).mean()

#instatiate new dataframe to hold image name, lat, long, etc
geotagdf = pd.DataFrame(columns=['imagepath','imagename','imagedt', 'imagedt_adj','gpxtime','timediff','gpxlat','gpxlon','gpxele', 'gpxheading','gpxroll','gpxpitch'])

#loop through ftypes
for ftype in ftypes:
#loop through files and write data to pandas df
    #for fn in tqdm(imgdir.glob('*.' + ftype)):
    for fn in imgdir.glob('*.' + ftype):
        #Load image datetime from exif
        imgdt = datetime.strptime(get_dt_original(fn), '%Y:%m:%d %H:%M:%S')
        
        #adjust image time
        adjimgdt = imgdt + timedelta(seconds=cam_to_utc_adjust_sec)
                          
        #find nearest dt stamp in gpx1hzdf
        idx = nearest_ind(gpx1hzdf['dt'], adjimgdt)
        gpxtime = gpx1hzdf.loc[idx]['dt'].to_pydatetime()
        gpxlat = gpx1hzdf.loc[idx]['lat']
        gpxlon = gpx1hzdf.loc[idx]['lon']
        gpxele = gpx1hzdf.loc[idx]['ele']
        #check if exceeds max time offset
        abs_actual_offset = np.abs((imgdt - gpxtime).total_seconds())
        if abs_actual_offset > max_time_offset:
            print(f'No GPS data found within {max_time_offset} seconds of adjusted image time for image {fn}, skipping geotag operation.')
            geotagdf = geotagdf.append({
                    'imagepath': fn,
                    'imagename': fn,
                    'imagedt': imgdt,
                    'imagedt_adj' : adjimgdt,
                    'gpxtime': gpxtime,
                    'timediff': abs_actual_offset,
                    'gpxlat': np.NaN,
                    'gpxlon': np.NaN,
                    'gpxele': np.NaN,
                    'gpxheading': np.NaN,
                    'gpxroll': np.NaN,
                    'gpxpitch': np.NaN,
                    }, ignore_index=True)
        else:
            geotagdf = geotagdf.append({
                    'imagepath': fn,
                    'imagename': fn,
                    'imagedt': imgdt,
                    'imagedt_adj' : adjimgdt,
                    'gpxtime': gpxtime,
                    'timediff': abs_actual_offset,
                    'gpxlat': gpx1hzdf.loc[idx]['lat'],
                    'gpxlon': gpx1hzdf.loc[idx]['lon'],
                    'gpxele': gpx1hzdf.loc[idx]['ele'],
                    'gpxheading': gpx1hzdf.loc[idx]['course'],
                    'gpxroll': gpx1hzdf.loc[idx]['roll'],
                    'gpxpitch': gpx1hzdf.loc[idx]['pitch'],
                    }, ignore_index=True)

#Loop through df and run exiftool

    #using pyexiftool?
            
                
            
    