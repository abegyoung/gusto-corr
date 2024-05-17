#
#
import os
import glob
import math
import random
import numpy as np
from scipy import interpolate
from influxdb import InfluxDBClient

from astropy import units as u

from astropy.io import fits
from astropy.io.fits import Header
from astropy.table import Table

# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')



################################################################################
def doStuff(self):
   SRC_file  = self
   INDX   = int(SRC_file.split("_")[4][4:])
   scanID = int(SRC_file.split("_")[2])

   fp = open(SRC_file, 'r')
   unixtime_otf = int(fp.readline().split('\t')[1])
   fp.close()

   T_CAL = None
   tryscanID = scanID
   while T_CAL is None:
      myquery = 'SELECT last(*) FROM "HK_TEMP11" WHERE "scanID"=~/({:s})/'.format(str(tryscanID))
      points = client.query(myquery).get_points()
      for point in points:
         T_CAL = point.get('last_temp')
      tryscanID = tryscanID + round(2*random.random()-1) # go up or down
         
   # TODO: there is an error in sculptor's udpPointing database in timezone
   #       Need to offset -7hrs (25200secs)
   # Set ra and dec to zero, just in case we don't find UNIXTIME at scanID
   # (This does happen, scanID 14787 in NGC6334 one spectra is 26s late)
   ra = 0
   dec = 0
   myquery = 'SELECT last(*) FROM "udpPointing" WHERE "scanID"=~/({:s})/'.format(str(scanID)) + ' AND time>{:d}'.format(int((unixtime_otf-0.5-25200)*1e9)) + ' AND time<{:d}'.format(int((unixtime_otf+0.5-25200)*1e9))
   print(myquery)
   points = client.query(myquery).get_points()
   for point in points:
       ra   = point.get('last_RA')
       dec  = point.get('last_DEC')
   print("ra   {:f}".format(ra))
   print("dec  {:f}".format(dec))

   # Find suitable calibration files
   # OTF HOT will have the same scanID as the OTF.  Just find the nearest
   HOT_file = None
   tryscanID = scanID
   while HOT_file is None:
      deltat = 1000
      hot_file_pattern = f'./spectra/ACS3_HOT_{str(tryscanID)}_DEV4_INDX*'
      search_files = glob.glob(hot_file_pattern)
      #print("found HOT files: ", search_files)
      for file in search_files:
         fp = open(file, 'r')
         unixtime_hot = int(fp.readline().split('\t')[1])
         fp.close()
         if(abs(unixtime_otf-unixtime_hot)<deltat):
            HOT_file = file 
            best=abs(unixtime_otf-unixtime_hot)
      tryscanID = tryscanID + round(2*random.random()-1)

   # Find suitable calibration files
   # OTF REF will have one scanID ahead or behind the OTF.
   REF_file = None
   tryscanID = scanID-1
   while REF_file is None:
      deltat = 1000
      ref_file_pattern = f'./spectra/ACS3_REF_{str(tryscanID)}_DEV4_INDX*'
      search_files = glob.glob(ref_file_pattern)
      #print("found REF files: ", search_files)
      for file in search_files:
         fp = open(file, 'r')
         unixtime_ref = int(fp.readline().split('\t')[1])
         fp.close()
         if(abs(unixtime_otf-unixtime_ref)<deltat):
            REF_file = file 
            best=abs(unixtime_otf-unixtime_ref)
      tryscanID = tryscanID + round(2*random.random()-1)  # go up or down

   SRC_data = np.loadtxt(SRC_file, skiprows=25)
   HOT_data = np.loadtxt(HOT_file, skiprows=25)
   REF_data = np.loadtxt(REF_file, skiprows=25)
   
   y = HOT_data[:,1] / REF_data[:,1]
   y = (y-1)/1.3 + 1	# 30% non-linearity in backend
   Thot = 273 + T_CAL	# T_CAL in Kelvin
   Tsky =  46		# Callen Welton temp at 1900 GHz for 3 K sky temp
   Tsys=2*((Thot-y*Tsky)/(y-1))
   Ta = Tsys*(SRC_data[:,1] - REF_data[:,1])/(REF_data[:,1]) 
   x_values = (SRC_data[:,0]-1100)*0.158

   x0= np.absolute(SRC_data[:,0]-1000).argmin()
   x1= np.absolute(SRC_data[:,0]-1500).argmin()
   Ta_mean   = np.mean(Ta[x0:x1],   axis=0)	# Ta mean
   Tsys_mean = np.mean(Tsys[x0:x1], axis=0)	# Tsys mean
   Ta_rms  = (1.0*Tsys_mean)/math.sqrt(5000000*0.33)	# Radiometer Equation
   Ta_std = np.std(Ta[x0:x1], axis=0)		# std deviation of data


   if (Ta_std > Ta_rms*2):
      return (0, 0, 0, 0)

   print("T_sys\t\t{:.1f}".format(Tsys_mean))
   print("Calculated Ta_rms\t{:.1f}".format(Ta_rms))
   print("Spectral mean\t\t{:.1f}".format(Ta_std))
   #print("{:.1f}\t{:.1f}\t{:.1f}".format(Tsys_mean, Ta_rms, Ta_std))

   
   # Remove DC offset from T_A*
   Ta = Ta - Ta_mean			

   ### Polynominal fit in small region around v=0 km/s
   z = np.polyfit(x_values[x0:x1], Ta[x0:x1], 3)
   p = np.poly1d(z)
   x_flat = np.zeros(x1-x0)
   y_flat = np.zeros(x1-x0)
   for i in range(x0-x0, x1-x0):
     x_flat[i] = x_values[i+x0]
     y_flat[i] = Ta[i+x0] - p(x_flat[i])

   # Return the current (ra,dec) position and fit VLSR and Ta* vectors
   data = (ra, dec, x_flat, y_flat)
   return data


def regrid(ra, dec, T, beam):
   # Calculate the range of ra and dec values
   ra_min , ra_max = np.min(ra) , np.max(ra)
   dec_min, dec_max= np.min(dec), np.max(dec)

   # Calculate number of grid points
   N_ra = int(np.ceil((ra_max - ra_min) / beam))
   N_dec = int(np.ceil((dec_max - dec_min) / beam))

   # Create meshgrid
   ra_grid, dec_grid = np.meshgrid(np.linspace(ra_min, ra_max, N_ra),np.linspace(dec_min, dec_max, N_dec))

   # Initialize array
   avg_T = interpolate.griddata((ra, dec), T, (ra_grid, dec_grid), method='nearest')

   return ra_grid, dec_grid, avg_T


################################################################################



# Point to raw data to use
file_pattern = f'./spectra/ACS3_OTF_14*_DEV4_INDX0000_NINT00*.txt'
search_files = sorted(glob.glob(file_pattern))

# Initialize empty lists to accumulate data
ra_list = []
dec_list = []
vlsr_list = []
Ta_list = []


for file in search_files:
    # get ra, dec, and calibrated spectra from each OTF file
    print("trying OTF file: ", file)
    (ra, dec, vlsr, Ta) = doStuff(file)

    if(ra!=0 and np.isnan(np.sum(Ta))!=True):
       ra_list.append(ra)
       dec_list.append(dec)
       vlsr_list.append(vlsr)
       Ta_list.append(Ta)


# Convert lists to numpy arrays
ra  = np.array(ra_list)
dec = np.array(dec_list)
vlsr= np.array(vlsr_list)
Ta  = np.array(Ta_list)



# open a new blank FITS file
hdr = fits.Header()
hdr['NAXIS']   = 3
hdr['OBJECT']  = 'My data cube'
hdr['DATAMIN'] = 0
hdr['DATAMAX'] = 1
hdr['BUNIT']   = 'K (Ta*)     '

hdr['CTYPE1']  = 'RA          '
hdr['CRVAL1']  = 260
hdr['CDELT1']  = 0.016              # 1 arcmin beam
hdr['CRPIX1']  = 0                  # reference pixel array index
hdr['CROTA1']  = 0
hdr['CUNIT1']  = 'deg         '

hdr['CTYPE2']  = 'DEC         '
hdr['CRVAL2']  = -35
hdr['CDELT2']  = 0.016              # 1 arcmin beam
hdr['CRPIX2']  = 0                  # reference pixel array index
hdr['CROTA2']  = 0
hdr['CUNIT2']  = 'deg         '

hdr['CTYPE3']  = 'VLSR        '
hdr['CRVAL3']  = -15
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

# Beam size (deg)
beam = 0.02

# Calculate the range of ra and dec values
#dec_min, dec_max= np.min(dec), np.max(dec)
#ra_min , ra_max = np.min(ra) , np.max(ra)
# Calculate number of grid points
#N_Ta = len(Ta[0])
#N_dec = int(np.ceil((dec_max - dec_min) / beam))
#N_ra = int(np.ceil((ra_max - ra_min) / beam))

# Create an empty data_cube and fill with regridded data
#data_cube = np.zeros([N_Ta, N_dec, N_ra])
#for i in range(0, N_Ta):
   #ra_grid, dec_grid, avg_T = regrid(ra, dec, Ta[:,i], beam)
   #data_cube[i] = avg_T

# Write the data cube and header to a FITS file
#hdu = fits.PrimaryHDU(data=data_cube, header=hdr)
#hdu.writeto('my_data_cube.fits', overwrite=True)



