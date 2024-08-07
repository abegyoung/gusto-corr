#
#
import os
import sys
import glob
import time
import math
import numpy as np
import datetime
from influxdb import InfluxDBClient

from astropy import units as u
from astropy.coordinates import SkyCoord

import matplotlib.pyplot as plt
from PyAstronomy import pyasl

from astropy.io import fits
from astropy.io.fits import Header
from astropy.table import Table

# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')



######################################################################################
def doStuff(self):
   SRC_file  = self
   INDX   = int(SRC_file.split("_")[4][4:])
   scanID = int(SRC_file.split("_")[2])

   fp = open(SRC_file, 'r')
   unixtime_otf = int(fp.readline().split('\t')[1])
   fp.close()

   myquery = 'SELECT last(*) FROM "HK_TEMP11" WHERE "scanID"=~/({:s})/'.format(str(scanID))
   points = client.query(myquery).get_points()
   for point in points:
       T_CAL = point.get('last_temp')

   # TODO: there is an error in sculptor's udpPointing database in timezone, offset -7hrs (25200secs)
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
   deltat = 1000
   hot_file_pattern = f'./spectra/ACS3_HOT_{str(scanID-1)}_DEV4_INDX*'
   search_files = glob.glob(hot_file_pattern)
   print("found HOT files: ", search_files)
   for file in search_files:
       fp = open(file, 'r')
       unixtime_hot = int(fp.readline().split('\t')[1])
       fp.close()
       if(abs(unixtime_otf-unixtime_hot)<deltat):
           HOT_file = file 
           best=abs(unixtime_otf-unixtime_hot)

   # Find suitable calibration files
   # OTF HOT will have the same scanID as the OTF.  Just find the nearest
   deltat = 1000
   ref_file_pattern = f'./spectra/ACS3_REF_{str(scanID-1)}_DEV4_INDX*'
   search_files = glob.glob(ref_file_pattern)
   print("found REF files: ", search_files)
   for file in search_files:
       fp = open(file, 'r')
       unixtime_ref = int(fp.readline().split('\t')[1])
       fp.close()
       if(abs(unixtime_otf-unixtime_hot)<deltat):
           REF_file = file 
           best=abs(unixtime_otf-unixtime_ref)

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
      return

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

   # Plot
   #plt.plot(x_flat, y_flat, drawstyle='steps', linewidth=2)
   #plt.plot((SRC_data[:,0]-1100)*0.158, Ta, drawstyle='steps', linewidth=1)
   #plt.hlines(np.mean(Ta[x0:x1])+Ta_std, -100, 100)
   #plt.hlines(np.mean(Ta[x0:x1])-Ta_std, -100, 100)
   #plt.xlim((-50,80))
   #plt.ylim((-2,20))

   #a = plt.gca()
   # Compute and display 1 sigma and radiometer eqn.
   #plt.text(0.7, 0.92, r"$\frac{{T_{{sys}}}} {{\sqrt{{\Delta\nu \star t_{{int}}}}}}$ {:.1f}".format(Ta_rms), transform=a.transAxes)
   #plt.text(0.7, 0.85, "Ta_std {:.1f}".format(Ta_std), transform=a.transAxes)
   #plt.show()

   data = (ra, dec, x_flat, y_flat)
   return data


# Point to raw data to use
file_pattern = f'./spectra/ACS3_OTF_14771_DEV4_INDX*_NINT*'
scanID = int(file_pattern.split("_")[2])
search_files = glob.glob(file_pattern)

# open a plt handle
#plt.figure()

# open a new blank FITS file
fits_filename = 'ACS3_{:s}_DEV4.fits'.format(str(scanID))
header = Header()
header.set('SIMPLE', True)
header.set('BITPIX', 8)
header.set('NAXIS', 0)
header.set('EXTEND', True)
header.set('ORIGIN', 'GUSTO'
hdu = fits.PrimaryHDU(header=header)
hdulist = fits.HDUList([hdu])
hdulist.writeto(fits_filename)

for file in search_files:
    # get ra, dec, and calibrated spectra from each OTF file
    print("trying OTF file: ", file)
    (ra, dec, vlsr, Ta) = doStuff(file)

    # assemble header from the returned OTF function
    header = Header()
    header.set('XTENSION', 'BINTABLE') # binary table extension
    header.set('BITPIX', 8)            # array data type
    header.set('NAXIS', 1)             # number of array dimensions
    header.set('NAXIS1', 102)          # length of dimension 1
    header.set('TFIELDS', 4)           # length of table fields
    header.set('TTYPE1', 'RA')         # Longitude - like axis
    header.set('TFORM1', 'D')
    header.set('TTYPE2', 'DEC')        # Latitude - like axis
    header.set('TFORM2', 'D')
    header.set('TTYPE3', 'vlsr')       # Velocity - like axis
    header.set('TFORM3', 'D')
    header.set('TDIM3', '(1024)')
    header.set('TTYPE4', 'Ta')
    header.set('TFORM4', 'D')
    header.set('TDIM4', '(1024)')

    # CORE columns
    header.set('TELESCOP', 'GUSTO')         # Designation of telescope
    header.set('BANDWID', 500000000.0)    # Total bandwidth (Hz)
    header.set('TTYPE5', 'OBJECT')          # TODO: Auto-fill from catalog
    header.set('TFORM5', '12A')
    header.set('TTYPE6', 'DATA-OBS')        # TODO: Auto-fill from catalog
    header.set('TFORM6', '10A')


    header.set('TTYPE7', 'CRPIX1')          # RA of reference pixel
    header.set('TFORM7', '1I')
    header.set('TTYPE8', 'CRPIX2')          # DEC of reference pixel
    header.set('TFORM8', '1I')
    header.set('TTYPE9', 'CRPIX3')          # Velocity of reference pixel
    header.set('TFORM9', '1I')
    header.set('CRPIX3', '-15774.1')        # m/s

    # write data and header to fits file
    new_table = fits.BinTableHDU.from_columns([
        fits.Column(name='vlsr', format='D', array=vlsr),
        fits.Column(name='Ta',   format='D', array=Ta),
    ])
    new_table.header['RA'] = ra
    new_table.header['DEC'] = dec
    hdul = fits.open(fits_filename, mode='update')
    hdul.append(new_table)
    hdul.close()

