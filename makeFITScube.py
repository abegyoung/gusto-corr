
import os
import sys
import glob
import time
import math
import random
import numpy as np
import scipy
from scipy import interpolate
from influxdb import InfluxDBClient

import matplotlib.pyplot as plt
from itertools import compress
from tqdm import tqdm

from astropy import units as u
from astropy.coordinates import SkyCoord

from astropy.io import fits
from astropy.io.fits import Header
from astropy.table import Table
from astropy import wcs

# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')

global Tstart
global start_ra, end_ra
global start_dec, end_dec


###########################  FUNCTIONS  ########################################

# helper function to 
def contains_number_in_range(filename):
    # Extract all 5-digit numbers from the filename
    digits = [filename[i:i+5] for i in range(len(filename) - 4) if filename[i:i+5].isdigit()]
    # Check if any of the extracted numbers fall within the range
    for number in digits:
        if min_number <= int(number) <= max_number:
            return True
    return False



def get_unixtime(file, unixtime_otf):
   fp = open(file, 'r')
   unixtime = int(fp.readline().split('\t')[1])
   corrtime = float(fp.readline().split('\t')[1])
   fp.close()
   return(file, unixtime-unixtime_otf, corrtime)


def doStuff(self):
   global Tstart
   global start_ra, end_ra
   global start_dec, end_dec
   # Get scanID and INDX from filename
   SRC_file  = self
   INDX   = int(SRC_file.split("_")[4][4:])
   scanID = int(SRC_file.split("_")[2])

   # debug output files
   fsys = open("Tsys.txt", "a")
   ferr = open("err.txt",  "a")

   # Get timestamp
   fp = open(SRC_file, 'r')
   unixtime_otf = int(fp.readline().split('\t')[1])
   corrtime_otf = float(fp.readline().split('\t')[1])
   fp.close()

   # There is an error in sculptor's udpPointing database in timezone
   # Need to offset -7hrs (25200secs)
   # Also set ra and dec to zero, just in case we don't find UNIXTIME at scanID
   ra=0; dec=0
   myquery = 'SELECT last(*) FROM "udpPointing" WHERE "scanID"=~/({:s})/'.format(str(scanID)) + ' AND time>{:d}'.format(int((unixtime_otf-0.5-25200)*1e9)) + ' AND time<{:d}'.format(int((unixtime_otf+0.5-25200)*1e9))
   points = client.query(myquery).get_points()
   for point in points:
       ra   = point.get('last_RA')
       dec  = point.get('last_DEC')


   # Are RA,DEC within our requested range?
   if( (ra<start_ra) or (ra>end_ra) or (dec<start_dec) or (dec>end_dec) ):
     return (0, 0, 0, 0)

   tqdm.write("trying OTF file: {:s}".format(SRC_file))

   # If we're in the box, then check the OTF for ringing
   # Polynomial fit of 122-239 MHz
   xdata=np.arange(0,25)
   ydata = np.loadtxt(SRC_file, skiprows=50, max_rows=25, usecols=1) / corrtime_otf
   z = np.polyfit(xdata, ydata, 5)
   p = np.poly1d(z)
   data = np.zeros(25)
   for i in range(25):
      data[i] = ydata[i] - p(i)  # Apply polynominal fit
   print("OTF {:.1f}".format(np.std(data)), file=open("std.txt","a"))
   if(np.std(data)>4000):
      tqdm.write("OTF ringing {:s}\t{:.1f}".format(SRC_file, np.std(data)))
      print("{:d} {:.3f} {:.3f} OTFr".format(scanID, ra, dec), file=ferr)
      os.rename(SRC_file, SRC_file.replace('txt','bad'))  # never use it again
      return (0,0,0,0)    # And don't proceed


   # If we're continuing on, please find recent T_CAL
   # 
   T_CAL = None
   tryscanID = scanID
   while T_CAL is None:
      myquery = 'SELECT last(*) FROM "HK_TEMP11" WHERE "scanID"=~/({:s})/'.format(str(tryscanID))
      points = client.query(myquery).get_points()
      for point in points:
         T_CAL = point.get('last_temp')
      if (T_CAL == None):
         tryscanID = tryscanID + round(2*random.random()-1) # go up or down
         print("{:d} {:.3f} {:.3f} TCALsearch".format(scanID, ra, dec), file=ferr)



   # Find suitable calibration files
   # OTF HOT will have the same scanID as the OTF.  Just find the nearest
   HOT_file = None
   while HOT_file is None:
      hot_file_pattern0 = f'./spectra/ACS3_HOT_{str(scanID)}_DEV3_INDX*.txt'
      hot_file_pattern1 = f'./spectra/ACS3_HOT_{str(scanID+1)}_DEV3_INDX*.txt'
      hot_file_pattern2 = f'./spectra/ACS3_HOT_{str(scanID-1)}_DEV3_INDX*.txt'
      search_files = glob.glob(hot_file_pattern0) + glob.glob(hot_file_pattern1) + glob.glob(hot_file_pattern2)

      # take this list returned from glob, and SORT based on unixtime since otf
      file_info_list = sorted([get_unixtime(filename, unixtime_otf) for filename in search_files], key=lambda sublist: abs(sublist[1]))

      # debug
      #for info in file_info_list:
      #   tqdm.write(info)

      for info in file_info_list:
         file = info[0]
         unixtime_hot = info[1] + unixtime_otf
         corrtime_hot = info[2]
         Thot = abs(info[1])
         # Check for ringing HOT spectra
         xdata=np.arange(0,25)
         ydata = np.loadtxt(file, skiprows=50, max_rows=25, usecols=1) / corrtime_hot
         z = np.polyfit(xdata, ydata, 5)
         p = np.poly1d(z)
         data = np.zeros(25)
         for i in range(25):
            data[i] = ydata[i] - p(i)  # Apply polynominal fit
         print("HOT {:.1f}".format(np.std(data)), file=open("std.txt","a"))
         if(np.std(data)>1500):
            tqdm.write("HOT ringing {:s}\t{:.1f}".format(file, np.std(data)))
            os.rename(file, file.replace('txt','bad'))  # never use it again
         else:
            HOT_file=file  # use this file
            break          # and don't check the rest of the list
   tqdm.write("using {:s} {:d}".format(HOT_file, abs(Thot)))


   # Shits and giggles.  for DEBUG purposes, let's keep a record of ra,dec of the HOT we used
   hotra=0; hotdec=0
   myquery = 'SELECT last(*) FROM "udpPointing" WHERE "scanID"=~/({:s})/'.format(str(scanID)) + ' AND time>{:d}'.format(int((unixtime_hot-0.5-25200)*1e9)) + ' AND time<{:d}'.format(int((unixtime_hot+0.5-25200)*1e9))
   points = client.query(myquery).get_points()
   for point in points:
       hotra   = point.get('last_RA')
       hotdec  = point.get('last_DEC')


   # Find suitable calibration files
   # OTF REF will have one scanID ahead or behind the OTF.
   REF_file = None
   while REF_file is None:
      ref_file_pattern1 = f'./spectra/ACS3_REF_{str(scanID-1)}_DEV3_INDX*.txt'
      ref_file_pattern2 = f'./spectra/ACS3_REF_{str(scanID+1)}_DEV3_INDX*.txt'
      search_files = glob.glob(ref_file_pattern1) + glob.glob(ref_file_pattern2)

      # take this list returned from glob, and SORT based on unixtime since otf
      file_info_list = sorted([get_unixtime(filename, unixtime_otf) for filename in search_files], key=lambda sublist: abs(sublist[1]))

      # debug
      #for info in file_info_list:
      #   tqdm.write(info)

      for info in file_info_list:
         file = info[0]
         unixtime_ref = info[1] + unixtime_otf
         corrtime_ref = info[2]
         Tref = abs(info[1])
         # Look for ringing HOT spectra
         xdata=np.arange(0,25)
         ydata = np.loadtxt(file, skiprows=50, max_rows=25, usecols=1) / corrtime_ref
         z = np.polyfit(xdata, ydata, 5)
         p = np.poly1d(z)
         data = np.zeros(25)
         for i in range(25):
            data[i] = ydata[i] - p(i)  # Apply polynominal fit
         print("REF {:.1f}".format(np.std(data)), file=open("std.txt","a"))
         if(np.std(data)>1000):
            tqdm.write("REF ringing {:s}\t{:.1f}".format(file, np.std(data)))
            os.rename(file, file.replace('txt','bad'))  # never use it again
         else:
            REF_file=file
            break          # and don't check the rest of the list
   tqdm.write("using {:s} {:d}".format(REF_file, abs(Tref)))


   # Open SRC, HOT, and REF to numpy arrays
   SRC_data = np.loadtxt(SRC_file, skiprows=25)
   HOT_data = np.loadtxt(HOT_file, skiprows=25)
   REF_data = np.loadtxt(REF_file, skiprows=25)
   if (np.any(np.isnan(SRC_data))==True):
      tqdm.write("OTF has nans")
      print("{:d} {:.3f} {:.3f} OTFnan".format(scanID, ra, dec), file=ferr)
      os.rename(SRC_file, SRC_file.replace('txt','nan'))  # never use it again
      return(0,0,0,0)
   if (np.any(np.isnan(HOT_data))==True):
      tqdm.write("HOT has nans")
      print("{:d} {:.3f} {:.3f} HOTnan".format(scanID, ra, dec), file=ferr)
      os.rename(HOT_file, HOT_file.replace('txt','nan'))  # never use it again
      return(0,0,0,0)
   if (np.any(np.isnan(REF_data))==True):
      tqdm.write("REF has nans")
      print("{:d} {:.3f} {:.3f} REFnan".format(scanID, ra, dec), file=ferr)
      os.rename(REF_file, REF_file.replace('txt','nan'))  # never use it again
      return(0,0,0,0)

   
   # Compute sensitivity
   # Use T_CAL and Tsky from nearest H/K write
   y    = HOT_data[:,1] / REF_data[:,1]
   y    = (y-1) / 1.3 + 1	                # 30% non-linearity in backend
   Thot =  273 + T_CAL	                    # T_CAL in Kelvin
   Tsky =   46		                        # Callen Welton temp at 1900 GHz
   Tsys =  2*( (Thot-y*Tsky) / (y-1) )
   Ta = Tsys*(SRC_data[:,1] - REF_data[:,1]) / (REF_data[:,1])  # (S-R) / R
   x_values = (SRC_data[:,0]-1100)*0.158    # Hz -> m/s

   # Define Region Of Interest
   x0= np.absolute(SRC_data[:,0]-1000).argmin()
   x1= np.absolute(SRC_data[:,0]-1500).argmin()

   # Compute expected rms and sensitivity and
   # extract actual std dev from spectra and compare
   Ta_mean   = np.mean(Ta[x0:x1],   axis=0)	     # Ta mean
   Tsys_mean = np.mean(Tsys[x0:x1], axis=0)	     # Tsys mean
   Ta_rms  = (1.0*Tsys_mean)/math.sqrt(5e6*0.33) # Radiometer Equation
   Ta_std = np.std(Ta[x0:x1], axis=0)		     # std dev of data

   Ta = Ta - Ta_mean

   # output statistics
   tqdm.write("T_sys\t\t{:.1f}".format(Tsys_mean))
   tqdm.write("Calculated Ta_rms\t{:.1f}".format(Ta_rms))
   tqdm.write("Spectral mean\t\t{:.1f}\n".format(Ta_std))
   Tnow=int(time.time()-Tstart)
   print("{:d} {:.3f} {:.3f} {:.3f} {:.3f} {:.1f} {:.1f} {:.1f}".format(Tnow, ra, dec, hotra, hotdec, Tsys_mean, Ta_rms, Ta_std), file=fsys)

   # Find peaks
   peaks, properties = scipy.signal.find_peaks(Ta[x0:x1], height=0, prominence=6.5, width=3)
   for i in range(len(peaks)):
     tqdm.write("velocity   {:.1f}".format(x_values[x0+peaks[i]]))
     tqdm.write("height     {:.1f}".format(properties["peak_heights"][i]))
     tqdm.write("prominence {:.1f}".format(properties["prominences"][i]))
     tqdm.write("width      {:.1f}\n".format(properties["width_heights"][i]))

   # Mask around peak(s)
   xdata=x_values[x0:x1]
   ydata=Ta[x0:x1]
   mask = (xdata>0) | (xdata<=0)  # If there are no peaks, mask is all True
   for i in range(102):
      if ((i in peaks) | ((i+1) in peaks) | ((i-1) in peaks) | ((i+2) in peaks) | ((i-2) in peaks) | ((i+3) in peaks) | ((i-3) in peaks) | ((i+4) in peaks) | ((i-4) in peaks)):
         mask[i] = False
      else:
         mask[i] = True

   # Polynomial fit region outside of peak(s)
   if any(mask):
      z = np.polyfit(xdata[mask], ydata[mask], 5)
      p = np.poly1d(z)
      x_flat = np.zeros(x1-x0)
      y_flat = np.zeros(x1-x0)
      for i in range(x0-x0, x1-x0):
         x_flat[i] = x_values[i+x0]
         y_flat[i] = Ta[i+x0] - p(x_flat[i])  # Apply polynominal fit
   else:
      tqdm.write("--------------- All Mask False ---------------") 
      print("{:d} {:.3f} {:.3f} MASK0".format(scanID, ra, dec), file=ferr)
      return (0, 0, 0, 0)


   # DEBUG #######################################
   if (y_flat >= 30).any():
      tqdm.write("--------------- has huge peak! ---------------") 
      print("{:d} {:.3f} {:.3f} HUGE".format(scanID, ra, dec), file=ferr)
      return (0, 0, 0, 0)
   if (len(peaks)>=8):
      tqdm.write("--------------- too many peaks ---------------") 
      print("{:d} {:.3f} {:.3f} NPEAKS".format(scanID, ra, dec), file=ferr)
      return (0, 0, 0, 0)
   if (Ta_std>6):
      tqdm.write("--------------- Tastd to large ---------------") 
      print("{:d} {:.3f} {:.3f} Ta_std".format(scanID, ra, dec), file=ferr)
      return (0, 0, 0, 0)
   #plt.ion()
   #plt.clf()
   #for i in range(len(peaks)):
   #  plt.vlines(x_values[x0+peaks[i]], Ta[x0+peaks[i]]-1, Ta[x0+peaks[i]]+1)
   #plt.step(x_values, Ta, 'b', linewidth=1)
   #plt.step(x_flat, y_flat, 'r', linewidth=1)
   #plt.plot(x_flat, mask)

   #plt.xlim((-40, 90))
   #plt.ylim((-5, 30))
   #plt.show()
   #plt.pause(.05)
   # DEBUG #######################################

   # close the debug files
   fsys.close()
   ferr.close()

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


global suffix
suffix='_06-06-001'

def saveArrays(ra, dec, vlsr, Ta):
   global suffix

   filename='ra{:s}.dat'.format(suffix)
   with open(filename,'wb') as FileToWrite:
       np.asarray(ra, dtype=np.float64).tofile(FileToWrite)
   filename='dec.dat'
   filename='dec{:s}.dat'.format(suffix)
   with open(filename,'wb') as FileToWrite:
       np.asarray(dec, dtype=np.float64).tofile(FileToWrite)
   filename='vlsr{:s}.dat'.format(suffix)
   with open(filename,'wb') as FileToWrite:
       np.asarray(vlsr, dtype=np.float64).tofile(FileToWrite)
   filename='Ta{:s}.dat'.format(suffix)
   with open(filename,'wb') as FileToWrite:
       np.asarray(Ta, dtype=np.float64).tofile(FileToWrite)



def openArrays():
   global suffix

   ra  =np.fromfile('ra{:s}.dat'.format(suffix),    dtype=np.float64)
   dec =np.fromfile('dec{:s}.dat'.format(suffix),   dtype=np.float64)
   length=len(ra)

   vlsr=np.fromfile('vlsr{:s}.dat'.format(suffix),  dtype=np.float64).reshape((length,102))
   Ta  =np.fromfile('Ta{:s}.dat'.format(suffix),    dtype=np.float64).reshape((length,102))
   #cube=np.fromfile('cube-dev3.dat',  dtype=np.float64).reshape((102,94,170))

   return ra, dec, vlsr, Ta



global axes
def plotSpecMap(x,y,x_data,y_data):
   global axes
   global vlsr

   # select plot
   axes[x,y].step(x_data,y_data, linewidth=1)
   a = plt.gca()

   # set plot range
   axes[x,y].set_xlim(-15,25)  # km/s
   axes[x,y].set_ylim(-5,30)   # Kelvin

   # set visibility
   xax = axes[x,y].get_xaxis()
   xax = xax.set_visible(False)
   yax = axes[x,y].get_yaxis()
   yax = yax.set_visible(False)



def makeSpecMap(ra, dec, vlsr, Ta):
   # grid data again to make a smaller spectral map than the FITS cube


   global axes
   fig, axes = plt.subplots(30, 30)
   data_cube = np.zeros([102, 30, 30])

   beam = (np.max(ra)-np.min(ra))/30
   for i in range(0, 102):
      ra_grid, dec_grid, avg_T = regrid(ra, dec, Ta[:,i], beam)
      data_cube[i] = avg_T
   print("data regridded!")

   for x in range(0,30):
      for y in range(0,30):
          plotSpecMap(x,y,vlsr[0],data_cube[:,x,y])
   print("map made")

   #fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=None)
   fig.subplots_adjust(wspace=None, hspace=None)
   plt.show()

################################################################################

# if we're just making spectral maps from existing data, do that and quit
if (sys.argv[1]=='mosaic'):
    # get the data
    ra, dec, vlsr, Ta = openArrays()
    print("got the data files!")

    #
    makeSpecMap(ra, dec, vlsr, Ta)

    sys.exit()


# if we're making FITS cubes from existing data, skip the doStuff() loop
if (sys.argv[1]=='existing'):
    # get the data
    ra, dec, vlsr, Ta = openArrays()
    print("got the data files!")

    #
    makeSpecMap(ra, dec, vlsr, Ta)

    sys.exit()


# Otherwise use the start and end scanIDs below and 
min_number = 14551
max_number = 15413

# ra, dec coordinates
ra_center  = '+17h22m10s'
dec_center = '-35d57m35s'

# center of Spitzer 8um
#ra_center  = '+17h20m00s'
#dec_center = '-35d56m25s'

# image size
ra_img  = 30*u.arcmin
dec_img = 30*u.arcmin

c = SkyCoord(ra_center, dec_center, frame='icrs')

start_ra = c.ra.deg - ra_img.to(u.deg).value
end_ra   = c.ra.deg + ra_img.to(u.deg).value
start_dec = c.dec.deg - dec_img.to(u.deg).value
end_dec   = c.dec.deg + dec_img.to(u.deg).value

Tstart=time.time()


# Point to raw data to use
file_pattern = f'./spectra/ACS3_OTF_1[4-5]*_DEV3_INDX*_NINT*.txt'
all_files = sorted(glob.glob(file_pattern))
search_files = [filename for filename in all_files if contains_number_in_range(filename)]
print("Total # of files in glob: {:d}".format(len(search_files)))

# Make a random boolean mask of 10% True values
mask=np.full(len(search_files), False)
mask[:int(1.0*len(mask))] = True
np.random.shuffle(mask)

# Apply mask to select a random sampling of files
search_files = list(compress(search_files, mask))
print("Randomly selected files to run: {:d}".format(len(search_files)))

print("Starting...")
time.sleep(3)

# Initialize empty lists to accumulate data
ra_list   = []
dec_list  = []
vlsr_list = []
Ta_list   = []

for file in tqdm(search_files):
   try:
      # get ra, dec, and calibrated spectra from each OTF file
      # tqdm.write("trying OTF file: {:s}".format(file))
      (ra, dec, vlsr, Ta) = doStuff(file)

      if(ra!=0 and np.isnan(np.sum(Ta))!=True):
         ra_list.append(ra)
         dec_list.append(dec)
         vlsr_list.append(vlsr)
         Ta_list.append(Ta)
   except KeyboardInterrupt:
      print("exiting doStuff() loop early")
      break
       
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
hdu.writeto('my_data_cube_06-10-001.fits', overwrite=True)

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

