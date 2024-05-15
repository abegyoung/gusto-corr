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

   myquery = 'SELECT last(*) FROM "HK_TEMP11" WHERE "scanID"=~/({:s})/'.format(str(scanID))
   points = client.query(myquery).get_points()
   for point in points:
       T_CAL = point.get('last_temp')

   # Find suitable calibration files
   # OTF HOT will have the same scanID as the OTF.  Just find the nearest
   deltat = 1000
   hot_file_pattern = f'./spectra/ACS3_HOT_{str(scanID-1)}_DEV4_INDX*'
   search_files = glob.glob(hot_file_pattern)
   #print("found HOT files: ", search_files)
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
   #print("found REF files: ", search_files)
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
   Ta_rms  = (1.0*Tsys_mean)/math.sqrt(5000000*0.3)	# Radiometer Equation
   Ta_std = np.std(Ta[x0:x1], axis=0)		# std deviation of data

   if (Ta_std > Ta_rms*2):
      return

   print("T_sys\t\t{:.1f}".format(Tsys_mean))
   print("Calculated Ta_rms\t{:.1f}".format(Ta_rms))
   print("Spectral mean\t\t{:.1f}\n".format(Ta_std))
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
   plt.plot(x_flat, y_flat, drawstyle='steps', linewidth=2)
   #plt.plot((SRC_data[:,0]-1100)*0.158, Ta, drawstyle='steps', linewidth=1)
   plt.hlines(np.mean(Ta[x0:x1])+Ta_std, -100, 100)
   plt.hlines(np.mean(Ta[x0:x1])-Ta_std, -100, 100)
   plt.xlim((-50,80))
   plt.ylim((-2,20))

   a = plt.gca()
   # Compute and display 1 sigma and radiometer eqn.
   plt.text(0.7, 0.92, r"$\frac{{T_{{sys}}}} {{\sqrt{{\Delta\nu \star t_{{int}}}}}}$ {:.1f}".format(Ta_rms), transform=a.transAxes)
   plt.text(0.7, 0.85, "Ta_std {:.1f}".format(Ta_std), transform=a.transAxes)
    


file_pattern = f'./spectra/ACS3_OTF_1463*_DEV4_INDX000*_NINT0*'
search_files = glob.glob(file_pattern)
plt.figure()
for file in search_files:
    #print("trying OTF file: ", file)
    doStuff(file)

plt.show()

