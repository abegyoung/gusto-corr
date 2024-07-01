import glob
from astropy.io import fits

for fitsName in glob.glob('*.fits'):
    hdulist = fits.open(fitsName)
    hdr = hdulist[1].header
    print(fitsName, hdr['NAXIS2'])
