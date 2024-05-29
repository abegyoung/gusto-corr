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
from astropy.coordinates import SkyCoord

from astropy.io import fits
from astropy.io.fits import Header
from astropy.table import Table
from astropy import wcs

# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')

global start_ra
global end_ra
global start_dec
global start_dec
# ra, dec coordinates
ra_center  = '+17h20m03s'
dec_center = '-35d57m45s'

# image size
ra_img = 30*u.arcmin
dec_img = 30*u.arcmin

c = SkyCoord(ra_center, dec_center, frame='icrs')

start_ra = c.ra.deg - ra_img.to(u.deg).value
end_ra   = c.ra.deg + ra_img.to(u.deg).value
start_dec = c.dec.deg - dec_img.to(u.deg).value
end_dec   = c.dec.deg + dec_img.to(u.deg).value



###########################  FUNCTIONS  ########################################
def doStuff(self):
   global start_ra
   global end_ra
   global start_dec
   global start_dec
   # Get scanID and INDX from filename
   SRC_file  = self
   INDX   = int(SRC_file.split("_")[4][4:])
   scanID = int(SRC_file.split("_")[2])

   # Get timestamp
   fp = open(SRC_file, 'r')
   unixtime_otf = int(fp.readline().split('\t')[1])
   fp.close()

   # TODO: there is an error in sculptor's udpPointing database in timezone
   #       Need to offset -7hrs (25200secs)
   # Set ra and dec to zero, just in case we don't find UNIXTIME at scanID
   ra = 0
   dec = 0
   myquery = 'SELECT last(*) FROM "udpPointing" WHERE "scanID"=~/({:s})/'.format(str(scanID)) + ' AND time>{:d}'.format(int((unixtime_otf-0.5-25200)*1e9)) + ' AND time<{:d}'.format(int((unixtime_otf+0.5-25200)*1e9))
   points = client.query(myquery).get_points()
   for point in points:
       ra   = point.get('last_RA')
       dec  = point.get('last_DEC')
   #print("ra   {:f}".format(ra))
   #print("dec  {:f}".format(dec))


   # Are RA,DEC within our requested range?
   if( (ra<start_ra) or (ra>end_ra) or (dec<start_dec) or (dec>end_dec) ):
     #print("outside image ra  {:3f} > {:3f} > {:3f}".format(end_ra,  ra,  start_ra ))
     #print("outside image dec {:3f} > {:3f} > {:3f}".format(end_dec, dec, start_dec))
     return (0, 0, 0, 0)

   print("inside image ra  {:3f} < {:3f} < {:3f}".format(start_ra,  ra,  end_ra ))
   print("inside image dec {:3f} < {:3f} < {:3f}".format(start_dec, dec, end_dec))

   # If we're continuing on, please find recent T_CAL
   # 
   T_CAL = None
   tryscanID = scanID
   while T_CAL is None:
      myquery = 'SELECT last(*) FROM "HK_TEMP11" WHERE "scanID"=~/({:s})/'.format(str(tryscanID))
      points = client.query(myquery).get_points()
      for point in points:
         T_CAL = point.get('last_temp')
      tryscanID = tryscanID + round(2*random.random()-1) # go up or down


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

   # Open SRC, HOT, and REF to numpy arrays
   SRC_data = np.loadtxt(SRC_file, skiprows=25)
   HOT_data = np.loadtxt(HOT_file, skiprows=25)
   REF_data = np.loadtxt(REF_file, skiprows=25)
   
   # Compute sensitivity
   # Use T_CAL and Tsky from nearest H/K write
   y    = HOT_data[:,1] / REF_data[:,1]
   y    = (y-1) / 1.3 + 1	                # 30% non-linearity in backend
   Thot =  273 + T_CAL	                    # T_CAL in Kelvin
   Tsky =   46		                        # Callen Welton temp at 1900 GHz
   Tsys =  2*( (Thot-y*Tsky) / (y-1) )
   Ta = Tsys*(SRC_data[:,1] - REF_data[:,1]) / (REF_data[:,1])  # (S-R) / R
   x_values = (SRC_data[:,0]-1100)*0.158    # Hz -> m/s

   # Compute expected rms and sensitivity and
   # extract actual std dev from spectra and compare
   x0= np.absolute(SRC_data[:,0]-1000).argmin()
   x1= np.absolute(SRC_data[:,0]-1500).argmin()
   Ta_mean   = np.mean(Ta[x0:x1],   axis=0)	     # Ta mean
   Tsys_mean = np.mean(Tsys[x0:x1], axis=0)	     # Tsys mean
   Ta_rms  = (1.0*Tsys_mean)/math.sqrt(5e6*0.33) # Radiometer Equation
   Ta_std = np.std(Ta[x0:x1], axis=0)		     # std dev of data

   # Throw away spectra if stddev greater than expected
   # effectively catches ringing
   if (Ta_std > Ta_rms*2):
     print("Tstd out of range")
     return (0, 0, 0, 0)

   print("T_sys\t\t{:.1f}".format(Tsys_mean))
   print("Calculated Ta_rms\t{:.1f}".format(Ta_rms))
   print("Spectral mean\t\t{:.1f}\n".format(Ta_std))
   f = open("Tsys.txt", "a")
   print("histo {:.3f},{:.3f}\t{:.1f}\t{:.1f}\t{:.1f}".format(ra, dec,Tsys_mean, Ta_rms, Ta_std), file=f)

   # Remove DC offset from T_A*
   Ta = Ta - Ta_mean			

   ### Polynominal fit in small region around v=0 km/s
   ### TODO: find broad C[II] peak and limit fit around it
   z = np.polyfit(x_values[x0:x1], Ta[x0:x1], 3)
   p = np.poly1d(z)
   x_flat = np.zeros(x1-x0)
   y_flat = np.zeros(x1-x0)
   for i in range(x0-x0, x1-x0):
     x_flat[i] = x_values[i+x0]
     y_flat[i] = Ta[i+x0] - p(x_flat[i])

   # If there are NaNs, throw them out
   if(np.isnan(sum(y_flat))==True):
     return (0, 0, 0, 0)

   # Return the current (ra,dec) position and fit VLSR and Ta* vectors
   data = (ra, dec, x_flat, y_flat)
   return data



def regrid(ra, dec, T, beam):
   # FYI: This regridder does not do a spherical projection.
   # Linear approx TAN(phi) =/= phi for > 30 arcmin

   # Calculate the range of ra and dec values
   ra_min , ra_max = np.min(ra) , np.max(ra)
   dec_min, dec_max= np.min(dec), np.max(dec)

   # Calculate number of grid points
   N_ra = int(np.ceil((ra_max - ra_min) / beam))
   N_dec = int(np.ceil((dec_max - dec_min) / beam))

   # Create meshgrid
   ra_grid, dec_grid = np.meshgrid(np.linspace(ra_min, ra_max, N_ra),np.linspace(dec_min, dec_max, N_dec))

   # Initialize array
   avg_T = interpolate.griddata((ra, dec), T, (ra_grid, dec_grid), method='cubic')

   return ra_grid, dec_grid, avg_T



def saveArrays(ra, dec, vlsr, Ta):
   filename='ra.dat'
   with open(filename,'wb') as FileToWrite:
       np.asarray(ra, dtype=np.float64).tofile(FileToWrite)
   filename='dec.dat'
   with open(filename,'wb') as FileToWrite:
       np.asarray(dec, dtype=np.float64).tofile(FileToWrite)
   filename='vlsr.dat'
   with open(filename,'wb') as FileToWrite:
       np.asarray(vlsr, dtype=np.float64).tofile(FileToWrite)
   filename='Ta.dat'
   with open(filename,'wb') as FileToWrite:
       np.asarray(Ta, dtype=np.float64).tofile(FileToWrite)



def openArrays(length):
   ra  =np.fromfile('ra.dat',    dtype=np.float64)
   dec =np.fromfile('dec.dat',   dtype=np.float64)
   vlsr=np.fromfile('vlsr.dat',  dtype=np.float64).reshape((length,102))
   Ta  =np.fromfile('Ta.dat',    dtype=np.float64).reshape((length,102))
   #cube=np.fromfile('cube-dev3.dat',  dtype=np.float64).reshape((102,94,170))

   return ra, dec, vlsr, Ta, cube



################################################################################



# Point to raw data to use
file_pattern = f'./spectra/ACS3_OTF_1*_DEV4_INDX*_NINT*.txt'
search_files = sorted(glob.glob(file_pattern))

# Initialize empty lists to accumulate data
ra_list   = []
dec_list  = []
vlsr_list = []
Ta_list   = []

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

saveArrays(ra, dec, vlsr, Ta)

# FWHM beam diameter (deg)
beam = 0.01666   #  1 arcmin
beam = beam / 3  # Initial grid should be 1/3 of smoothed resolution

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
# Find the fiducial pixel or image center
ra_fid = ra_center
dec_fid = dec_center

# make a WCS from a dictionary
wcs_input_dict = {
        'CTYPE1': 'RA---TAN',
        'CUNIT1': 'deg',
        'CDELT1': beam, 
        'CRPIX1': int(N_ra/2),
        'CRVAL1': c.ra.deg,
        'NAXIS1': N_ra,

        'CTYPE2': 'DEC--TAN',
        'CUNIT2': 'deg',
        'CDELT2': beam,
        'CRPIX2': int(N_dec/2),
        'CRVAL2': c.dec.deg,
        'NAXIS2': N_dec
}
wcs_object_dict = wcs.WCS(wcs_input_dict)
# I don't do anything with this just yet.



# open a new blank FITS file
hdr = fits.Header()
hdr['NAXIS']   = 3
hdr['OBJECT']  = 'NGC6334     '
hdr['DATAMIN'] = min([min(min_list) for min_list in Ta])
hdr['DATAMAX'] = max([max(max_list) for max_list in Ta])
hdr['BUNIT']   = 'K (Ta*)     '

hdr['CTYPE1']  = 'RA---TAN    '
hdr['CRVAL1']  = c.ra.deg 
hdr['CDELT1']  = beam               # grid beam size
hdr['CRPIX1']  = int(N_ra/2)        # reference pixel array index
hdr['CROTA1']  = 0
hdr['CUNIT1']  = 'deg         '

hdr['CTYPE2']  = 'DEC--TAN    '
hdr['CRVAL2']  = c.dec.deg 
hdr['CDELT2']  = beam               # grid beam size
hdr['CRPIX2']  = int(N_dec/2)       # reference pixel array index
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
hdr['RA']      = c.ra.deg           # Fiducial is image center
hdr['DEC']     = c.dec.deg
hdr['EQUINOX'] = 2000
hdr['LINE']    = 'C+          '
hdr['RESTFREQ']= 1900.5369          # Rest frequency of C[II]
hdr['VELOCITY']= 0

# Write the data cube and header to a FITS file
hdu = fits.PrimaryHDU(data=data_cube, header=hdr)
hdu.writeto('my_data_cube_05-28.fits', overwrite=True)

# Text Abe to let home know the cube is done
os.system("/home/young/bin/code.pl 'done'")

'''
#code.pl
#!/usr/bin/perl

use Net::SMTP 3.03;
use Authen::SASL;

my $smtp = Net::SMTP->new('smtp.gmail.com',
    Port => 587,
    Debug => 0);

$smtp->starttls();
$smtp->auth(
  Authen::SASL->new(
    mechanism => 'PLAIN LOGIN',
    callback => { user => 'abeyoung996@gmail.com', pass => 'gtijcsfwremkompf' }
  )
);
$smtp->mail('abeyoung996@gmail.com');
$smtp->to('5202475055@tmomail.net');  #Abe
$smtp->data();
$smtp->datasend("\n$ARGV[0]");
$smtp->dataend();
$smtp->quit;
'''

