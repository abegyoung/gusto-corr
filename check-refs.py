import glob
import numpy as np
from astropy.io import fits
import gc

def doStuff(fits_file):
# Open file
    with fits.open(fits_file, memmap=True) as hdul:

        # Read in hdu[2] DATA_TABLE
        data = hdul['DATA_TABLE'].data

        # Mask of all REF type rows
        mask = data['scan_type']=='OTF'
        # All REF type scanID
        listOTF = hdul['DATA_TABLE'].data['scanID'][mask]
        if (len(list(set(listOTF))) == 1):
            otf = list(set(listOTF))[0]
        else:
            print(fits_file, "error more than one otf")
            return

        # Mask of all REF type rows
        mask = data['scan_type']=='REF'
        # All REF type scanID
        listREF = hdul['DATA_TABLE'].data['scanID'][mask]
        earliestREF = list(sorted(set(listREF)))[0]
        latestREF = list(sorted(set(listREF)))[len(list(set(listREF)))-1]

        if( earliestREF < otf < latestREF ):
            print(earliestREF, otf, latestREF, " OK", len(set(listREF)))
        else:
            print(earliestREF, otf, latestREF, " ERROR")

directory = "./"
fits_files = sorted(glob.glob(f"{directory}/ACS5_05*.fits"))

for fits_file in fits_files:
    doStuff(fits_file)
    gc.collect()


