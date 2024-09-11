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

def doStuff(scan):
    hdu    = fits.open(scan, mode='update')
    data   = hdu[1].data
    spec   = data['spec'] 
    CHANNEL_FLAG = data['CHANNEL_FLAG']
    ROW_FLAG = data['ROW_FLAG']
    npix   = hdu[0].header['NPIX']
    nrow   = len(spec)
    mixer  = data['MIXER']
    scanID = data['scanID']
    spec   = data['spec']
    THOT   = data['THOT']
    scan_type = data['scan_type']

    # Known spikes
    # LO Interference
    # MHz   Channel
    # 317-342   65, 66, 67, 68
    # 649-659   133, 134
    # 972       198, 199
    #
    # Iridium
    # 1610      329, 330
    # Look through all of the spectra to set row_flags for noisy data
    for i in range(nrow-1):
        for j in range(npix-1):
            CHANNEL_FLAG[i][j]   = 0
        CHANNEL_FLAG[i][66:70]   = 1    # LO 1 330 MHz
        CHANNEL_FLAG[i][134:136] = 1    # LO 2 656 MHz
        CHANNEL_FLAG[i][201:203] = 1    # LO 3 980 MHz
        CHANNEL_FLAG[i][331:335] = 1    # Iridium 1 1616-1625 MHz

    # Write the change back to the fits file
    hdu.flush()


directory = "./"
partial = sys.argv[1]
search_files = sorted(glob.glob(f"{directory}/{partial}.fits"))
for file in (search_files):
    doStuff(file)


