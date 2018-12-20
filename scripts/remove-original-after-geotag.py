# -*- coding: utf-8 -*-
"""
Created on Thu Dec 20 11:12:41 2018

Removes *_original files after 'geotag-with-gpx.py'

example: runfile('geotag-with-gpx.py', args='-dir=D:/temp/testrename -f=2 -utc=0 -sepdir')
@author: jlogan
"""

import argparse
from pathlib import Path
import subprocess

