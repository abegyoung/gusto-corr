import numpy as np
from astropy.io import fits
from scipy import interpolate

'''
data_cube.shape
(102, 94, 170)
ra.shape
(73328,)
dec.shape
(73328,)
vlsr.shape
(73328, 102)
Ta.shape
(73328, 102)
'''

def regrid(ra, dec, T, beam):
   # Ready rotation
   RotRad = -0.7
   RotMatrix = np.array([[np.cos(RotRad), np.sin(RotRad)],
                         [-np.sin(RotRad), np.cos(RotRad)]])

   # Calculate the range of ra and dec values
   ra_min , ra_max = np.min(ra) , np.max(ra)
   dec_min, dec_max= np.min(dec), np.max(dec)

   # Calculate number of grid points
   N_ra = int(np.ceil((ra_max - ra_min) / beam))
   N_dec = int(np.ceil((dec_max - dec_min) / beam))

   # Create meshgrid
   ra_grid, dec_grid = np.meshgrid(np.linspace(ra_min, ra_max, N_ra),np.linspace(dec_min, dec_max, N_dec))
   #ra_grid, dec_grid = np.einsum('ji, mni -> jmn', RotMatrix, np.dstack([ra_grid, dec_grid]))

   # Initialize array
   avg_T = interpolate.griddata((ra, dec), T, (ra_grid, dec_grid), method='nearest')

   return ra_grid, dec_grid, avg_T

ra  =np.fromfile('ra.dat',   dtype=np.float64)
dec =np.fromfile('dec.dat',  dtype=np.float64)
vlsr=np.fromfile('vlsr.dat', dtype=np.float64).reshape((73328,102))
Ta  =np.fromfile('Ta.dat',   dtype=np.float64).reshape((73328,102))

# Beam size (deg)
beam = 0.02

# Calculate the range of ra and dec values
dec_min, dec_max= np.min(dec), np.max(dec)
ra_min , ra_max = np.min(ra) , np.max(ra)
# Calculate number of grid points
N_Ta = len(Ta[0])
N_dec = int(np.ceil((dec_max - dec_min) / beam))
N_ra = int(np.ceil((ra_max - ra_min) / beam))

# Create an empty data_cube and fill with regridded data
data_cube = np.zeros([N_Ta, N_dec, N_ra])
for i in range(0, N_Ta):
   ra_grid, dec_grid, avg_T = regrid(ra, dec, Ta[:,i], beam)
   data_cube[i] = avg_T

# Do some WCS stuff
# Find the fiducial pixel (center of the regridded image)
ra_fid = ra_grid[int(ra_grid.shape[0]/2)][int(ra_grid.shape[1]/2)]
dec_fid = dec_grid[int(dec_grid.shape[0]/2)][int(dec_grid.shape[1]/2)]


# open a new blank FITS file
hdr = fits.Header()
hdr['NAXIS']   = 3
hdr['OBJECT']  = 'NGC6334     '
hdr['DATAMIN'] = min([min(min_list) for min_list in Ta])
hdr['DATAMAX'] = max([max(max_list) for max_list in Ta])
hdr['BUNIT']   = 'K (Ta*)     '

hdr['CTYPE1']  = 'RA          '
hdr['CRVAL1']  = ra_fid
hdr['CDELT1']  = 0.016              # 1 arcmin beam
hdr['CRPIX1']  = 0                  # reference pixel array index
hdr['CROTA1']  = 0
hdr['CUNIT1']  = 'deg         '

hdr['CTYPE2']  = 'DEC         '
hdr['CRVAL2']  = dec_fid
hdr['CDELT2']  = 0.016              # 1 arcmin beam
hdr['CRPIX2']  = 0                  # reference pixel array index
hdr['CROTA2']  = 0
hdr['CUNIT2']  = 'deg         '

hdr['CTYPE3']  = 'VLSR        '
hdr['CRVAL3']  = vlsr[0][0]
hdr['CDELT3']  = 0.771              # 771 m/s spectral resolution
hdr['CRPIX3']  = 0                  # reference pixel array index
hdr['CROTA3']  = 0
hdr['CUNIT3']  = 'm/s         '

hdr['OBJECT']  = 'NGC6334     '
hdr['RADESYS'] = 'FK5         '
hdr['RA']      = 260                # Fiducial is arbitrarily (ra,dec) min
hdr['DEC']     = -35
hdr['EQUINOX'] = 2000
hdr['LINE']    = 'C+          '
hdr['RESTFREQ']= 1900.5369          # GHz
hdr['VELOCITY']= 0


# Write the data cube and header to a FITS file
hdu = fits.PrimaryHDU(data=data_cube, header=hdr)
hdu.writeto('my_data_cube.fits', overwrite=True)

