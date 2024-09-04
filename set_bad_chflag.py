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
CHANNEL_FLAG = data['CHANNEL_FLAG']
npix   = hdu[0].header['NPIX']
nrow   = len(spec)

# Look through all of the spectra to set row_flags for noisy data
for i in range(nrow-1):
    for j in range(npix-1):
        CHANNEL_FLAG[i][j] = 0
    CHANNEL_FLAG[i][65]  = 1
    CHANNEL_FLAG[i][134] = 1
    CHANNEL_FLAG[i][135] = 1
    CHANNEL_FLAG[i][202] = 1
    CHANNEL_FLAG[i][333] = 1

# Write the change back to the fits file
hdu.flush()
