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


gpxdirstr = 'T:/UAS/2018-676-FA/tlogs/yellow/aircraft/gpx'
imgdirstr = 'D:/temp/testrename'

gpxdir = Path(gpxdirstr)
imgdir = Path(imgdirstr)


#file types to geotag
ftypes = ['JPG', 'DNG']

#using exifread which works for DNG and JPG
def get_dt_orignal(fn):
    '''Gets DateTimeOriginal value from EXIF'''
    with open(fn, 'rb') as i:
        tags = exifread.process_file(i)
    dt_orig = str(tags.get('EXIF DateTimeOriginal'))
    return dt_orig

def nearest(items, pivot):
    #from: https://stackoverflow.com/questions/32237862/find-the-closest-date-to-a-given-date
    return min(items, key=lambda x: abs(x - pivot))

def nearest_ind(items, pivot):
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
#ensure that duplicates are close together spatially, then calc mean lat/long/elev for each
latdf = gpxdf.groupby('dt')['lat'].agg(['max','min'])
latdf['diff_deg'] = latdf['max']-latdf['min']
#calc approx. dist. in meters (from http://www.esri.com/news/arcuser/0400/wdside.html)
latdf['diff_m'] = latdf['diff_deg'] * 30.87

londf = gpxdf.groupby('dt')['lon'].agg(['max','min'])
londf['diff_deg'] = londf['max']-londf['min']
#calc approx. dist. in meters
londf['diff_m'] = londf['diff_deg'] * np.cos(np.deg2rad(londf['max']))

#join to compute dist
lldf = pd.merge(latdf, londf, on='dt', how='outer')
lldf['maxdist_m'] = np.sqrt(np.square(lldf['diff_m_x']) + np.square(lldf['diff_m_y']))


    