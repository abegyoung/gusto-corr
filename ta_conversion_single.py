import os
import sys
import glob
import shutil
import matplotlib.pyplot as plt
from astropy.io import fits
import numpy as np
from pybaselines import Baseline, utils
from astropy import constants as const


tsky = 45.

scan = './ACS3_09000.fits'


hdu    = fits.open(scan)
data   = hdu[1].data
mixer  = data['MIXER']
scanID = data['scanID']
spec   = data['spec'] 
ra     = data['RA']
dec    = data['DEC']
THOT   = data['THOT']
scan_type = data['scan_type']
ROW_FLAG = data['ROW_FLAG']
CHANNEL_FLAG = data['CHANNEL_FLAG']

npix   = hdu[0].header['NPIX']
nrow   = len(spec)
IF_pix = hdu[0].header['CRPIX1']
IF_val = hdu[0].header['CRVAL1']
IF_del = hdu[0].header['CDELT1']
IF_freq = (np.arange(npix)-IF_pix)*IF_del+IF_val

IF_vlsr0  = hdu[0].header['IF0']
line_freq = hdu[0].header['LINEFREQ']
vlsr = (IF_vlsr0 - IF_freq)/line_freq*const.c.value/1.e3 # Vlsr in km/s

otf_scan = int(scan[7:12])
hot_scan = otf_scan
ref_scan = sorted(scanID[np.logical_and(mixer==2, scan_type=='REF')])[-1]
print(otf_scan, hot_scan, ref_scan)

# mask for pixel 8, otf, hot, ref, row_flag
otf_mask_mix = np.logical_and(np.logical_and(np.logical_and(scanID == otf_scan, mixer == 8), scan_type == 'OTF'), ROW_FLAG == 0)
hot_mask_mix = np.logical_and(np.logical_and(np.logical_and(scanID == hot_scan, mixer == 8), scan_type == 'HOT'), ROW_FLAG == 0)
ref_mask_mix = np.logical_and(np.logical_and(np.logical_and(scanID == ref_scan, mixer == 8), scan_type == 'REF'), ROW_FLAG == 0)


# Apply Channel flags to mask spectra
mask = np.ones(1024, dtype=bool)
for i in range(nrow-1):
    for j in range(npix-1):
        if(CHANNEL_FLAG[i][j] == 1):
            spec[i][j] = 0

# average HOT and REF scans
spec_hot_avg_mix =  spec[hot_mask_mix,:].sum(axis=0)/len(spec[hot_mask_mix,:])
spec_ref_avg_mix =  spec[ref_mask_mix,:].sum(axis=0)/len(spec[ref_mask_mix,:])
THOT_avg = THOT[hot_mask_mix].sum(axis=0)/len(THOT[hot_mask_mix])

# estimate Tsys for each Device
y_factor  = spec_hot_avg_mix/spec_ref_avg_mix
tsys_mix = (THOT_avg - tsky*y_factor[:])/(y_factor[:] - 1.)

# conversion to Ta
spec_OTF_dev = spec[otf_mask_mix,:] 
n_OTF_dev = len(spec_OTF_dev)

ta_mix = np.zeros(spec_OTF_dev.shape)
print(n_OTF_dev)
for i0 in range(n_OTF_dev):
    ta_mix[i0,:] = 2.*tsys_mix[:] * (spec_OTF_dev[i0,:] - spec_ref_avg_mix[:])/spec_ref_avg_mix

#
#

x = np.arange(1024)

# Plot the region where lines may appear
# Baseline calculation as well
# Plot the baseline corrected lines
xlow  = 100
xhigh = 250

base = np.zeros([n_OTF_dev,xhigh-xlow])
baseline_fitter = Baseline(x_data=x[xlow:xhigh])
fig, ax = plt.subplots(figsize=(10, 6))
for i0 in range(n_OTF_dev):
    spec_to_draw = ta_mix[i0,xlow:xhigh]- np.median(ta_mix[i0,xlow:xhigh])
    spec_new = spec_to_draw - base[i0,0:(xhigh-xlow)]
    base2 = baseline_fitter.aspls(spec_new, 1e5)
    ax.plot(vlsr[xlow:xhigh], spec_new - base2[0])
ax.set_xlabel(r'V$_{lsr}$ [km/s]')
ax.set_ylabel('Ta')
ax.set_xlim([vlsr[xlow],vlsr[xhigh]])
ax.set_ylim([-20,30])
plt.tight_layout()
plt.show()
