#
# Search RA,DEC and return scanIDs
#
import os
import glob
import time
import numpy as np
import datetime
from influxdb import InfluxDBClient
#from influxdb_client import InfluxDBClient
from tqdm import tqdm

from astropy import units as u
from astropy.coordinates import SkyCoord

import matplotlib.pyplot as plt
from PyAstronomy import pyasl

#################################################################################
global numi
global numj
numi = 0
numj = 0

username = ''
password = ''
database = 'gustoDBlp'
retention_policy = 'autogen'
bucket = f'{database}/{retention_policy}'

# Center of GUSTO 30 K line in NGC6334
ra_center  = '+17h22m10s'
dec_center = '-35d57m35s'

# center of Spitzer NGC6334 8um image
#ra_center = '+17h20m00s'
#dec_center = '-35d56m25s'

# half-beam size
size = 120*u.arcsec
c = SkyCoord(ra_center, dec_center, frame='icrs')

# half-image size
ra_img =  30*u.arcmin
dec_img = 30*u.arcmin

# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')

start_ra = c.ra.deg - ra_img.to(u.deg).value
end_ra   = c.ra.deg + ra_img.to(u.deg).value
N_ra     = int(ra_img.to(u.arcmin).value/size.to(u.arcmin).value)
ra_indx = np.linspace(start_ra, end_ra, N_ra)

start_dec = c.dec.deg - dec_img.to(u.deg).value
end_dec   = c.dec.deg + dec_img.to(u.deg).value
N_dec     = int(dec_img.to(u.arcmin).value/size.to(u.arcmin).value)
dec_indx = np.linspace(start_dec, end_dec, N_dec)

my_list=[]

for ra in tqdm(ra_indx):
    numi += 1
    numj = 0
    for dec in dec_indx:
        numj += 1
        #print('{:f}'.format(ra), '{:f}'.format(dec))
        # find all points in udpPointing where we pointed at ra, dec
        myquery = f'SELECT * FROM "udpPointing" WHERE RA<{(ra +size.to(u.deg).value)}  AND \
                                                      RA>{(ra -size.to(u.deg).value)}  AND \
                                                     DEC<{(dec+size.to(u.deg).value)}  AND \
                                                     DEC>{(dec-size.to(u.deg).value)}' 
        points = client.query(myquery).get_points()

        # For loop over all of these pointings
        # POINTS contains a (time, scanID) for each pointing at (ra,dec)
        for point in points:
            my_list.append(point.get("scanID"))


print(sorted(list(set(my_list))))
print(min(my_list))
print(max(my_list))



