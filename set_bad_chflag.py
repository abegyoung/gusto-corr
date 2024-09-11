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

# See if our flags took effect by doing an S-R/R
'''
otf_mask = np.logical_and(np.logical_and(np.logical_and(scanID == 9000, mixer == 8), scan_type == 'OTF'), ROW_FLAG == 0)
hot_mask = np.logical_and(np.logical_and(np.logical_and(scanID == 9000, mixer == 8), scan_type == 'HOT'), ROW_FLAG == 0)
ref_mask = np.logical_and(np.logical_and(np.logical_and(scanID == 8999, mixer == 8), scan_type == 'REF'), ROW_FLAG == 0)
THOT_avg = THOT[hot_mask].sum(axis=0)/len(THOT[hot_mask])

spec_hot_avg = spec[hot_mask,:].sum(axis=0)/len(spec[hot_mask,:])
spec_ref_avg = spec[ref_mask,:].sum(axis=0)/len(spec[ref_mask,:])

y_factor = spec_hot_avg / spec_ref_avg
tsys     = (THOT_avg - 45*y_factor[:])/(y_factor[:] - 1.)

spec_otf     = spec[otf_mask,:]
ta = np.zeros(spec_otf.shape)
for i in range(len(spec_otf)):
    ta[i,:] = 2*tsys[:] * (spec_otf[i,:] - spec_ref_avg[:])/spec_ref_avg
'''

xdata = np.arange(0,5000,5000/npix)
#xdata = np.arange(npix)
baseline_fitter = Baseline(xdata)
for i in range(len(spec_otf)):
    base_calc = baseline_fitter.aspls(ta[i], 5e4)

'''
    plt.step(xdata, ta[i])
    plt.step(xdata, ta[i] - base_calc[0])
    plt.step(xdata,10*CHANNEL_FLAG[i]-10)
    #plt.xlim([0,400])
    plt.xlim([0,1953])
    plt.ylim([-50,50])
    plt.show()
'''
