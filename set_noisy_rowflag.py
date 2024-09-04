import os
import sys
import glob
import shutil
import matplotlib.pyplot as plt
from astropy.io import fits
import numpy as np
from pybaselines import Baseline, utils
from astropy import constants as const

scan = './ACS3_09000.fits'

hdu    = fits.open(scan, mode='update')
data   = hdu[1].data
spec   = data['spec'] 
ROW_FLAG = data['ROW_FLAG']

# Look through all of the spectra to set row_flags for noisy data
xdata = np.arange(0,25)
data  = np.zeros(25)
for i in range(len(spec)):
    ydata = spec[i][25:50]
    z = np.polyfit(xdata, ydata, 5)
    p = np.poly1d(z)
    for j in range(25):
       data[j] = ydata[j] - p(j)
    if(np.std(data)>0.00025):
        ROW_FLAG[i] = 1
    else:
        ROW_FLAG[i] = 0

# Write the change back to the fits file
hdu.flush()
