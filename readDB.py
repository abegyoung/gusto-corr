#
# Currently, this script takes a coordinate in ra, dec
# 
# I've inserted all udp_*.txt files into my local gustoDBlp Influx Database.
#
# The Database is queried for any timestamps where we were pointing within `size` of ra,dec
#
# The timestamp and scanID is returned from the database
#
# search through all spectra files within that scanID that are within 1sec of the timestamp
#
# next turn these files over to coadd.py 
#
# TODO: need to find the nearest in time REF
#

import os
import glob
import time
import numpy as np
import datetime
from influxdb import InfluxDBClient
#from influxdb_client import InfluxDBClient

from astropy import units as u
from astropy.coordinates import SkyCoord

import matplotlib.pyplot as plt
from PyAstronomy import pyasl

doDespike = False

def read_and_average_files(files, n_lines_header=0):
    # Get a list of files that match the specified pattern
    #files = glob.glob(file_pattern)

    if not files:
        print(f"No files found matching the pattern: {file_pattern}")
        return None

    # Initialize lists to store first and second columns
    all_first_columns = []
    valid_second_columns = []

    i=0
    for file in files:
        # Read the data from the text file, skipping the specified number of header lines
        data = np.loadtxt(file, skiprows=n_lines_header)

        # Extract the first and second columns
        first_column = data[:, 0]
        second_column = data[:, 1]

        # Check if all values in the second column are zero or NaN
        if not (np.std(second_column[42:62])>35000 or np.all(second_column == 0) or np.any(np.isnan(second_column))):
            all_first_columns.append(first_column)
            valid_second_columns.append(second_column)
        else:
          print("Throwing out ", file, "with stddev ", np.std(second_column[42:62]))

    if not valid_second_columns:
        print("All second columns are zero or contain NaN values. No valid data for averaging.")
        return None

    # Convert the lists of arrays to NumPy arrays
    all_first_columns = np.array(all_first_columns)
    valid_second_columns = np.array(valid_second_columns)

    # Calculate the average along the rows (axis=0)
    average_first_column = np.mean(all_first_columns, axis=0)
    average_second_column = np.nanmean(valid_second_columns, axis=0)

    return average_first_column, average_second_column

def plot_subtraction_ratio(x_values, subtraction_ratio, x_limit, y_limit):
    global numi
    global numj
    global integrated_intensity
    #my_dpi=96
    #plt.figure(figsize=(120/my_dpi, 120/my_dpi), dpi=my_dpi)

    plt.figure()

    # Plot the subtraction ratio with the first column on the x-axis
    z = np.polyfit(x_values[185:267], subtraction_ratio[185:267], 3)
    p = np.poly1d(z)
    xp = np.linspace(1000, 1300, 10)

    # plot s-r/r and baseline fit
    #plt.step(x_values, subtraction_ratio)
    #plt.plot(xp, p(xp), '-')

    flatx = np.zeros(83)
    flaty = np.zeros(83)
    # make a baseline-subtracted spectra
    for i in range(0, 83):
        flatx[i] = x_values[i+185]
        flaty[i] = subtraction_ratio[i+185] - p(flatx[i]) 
    flaty[201-185] = 0 # blank bad freq
    flaty[202-185] = 0 # blank bad freq
    # x-axis scale (km/s)
    #     (1MHz/1900GHz) * c = 0.158 km/s
    # y-axis scale (K):
    #     for DSB: TA* ~= 2 * (T_hot) * y-factor * (s-r/r)
    #plt.plot((flatx-1100)*0.158, 2*(273+13)*1.4*flaty, drawstyle='steps', linewidth=3)
    # @ 1.1GHz, y=HOT/REF => Tsys=1.3*(273K-45K*y/(y-1)) = 800K with a 1.3 linearity factor
    plt.plot((flatx-1100)*0.158, 800*flaty, drawstyle='steps', linewidth=3)

    # remove non-zero
    flaty[flaty<0]=0
    integrated_intensity[numj-1, numi-1] = np.trapz(flaty)

    # more conventionally:
    # Tsys from T_HOT and T_Sky=45K
    # Ta = Tsys * ( S-R / R )
    # TODO: use the HOTs as REF only ratios can be up to ~ 12 minutes old
    plt.hlines(0, -30, 30, linestyle='--', color='black')

    #plt.xlabel('MHz')
    #plt.ylabel('(S-R) / R (+ DC offset)')
    plt.xlabel('km/s')
    plt.ylabel('$T^{*}_{A}$ (K)')
    a = plt.gca()

    # set visibility of x-axis as False
    xax = a.axes.get_xaxis()

    # set visibility of y-axis as False
    yax = a.axes.get_yaxis()

    # Set limits on the x and y axes
    plt.xlim(x_limit)
    plt.ylim(y_limit)

    plt.tight_layout()
    plt.text(0.8, 0.95, "{:02f}".format(integrated_intensity[numj-1, numi-1]), transform=a.transAxes)
    #plt.text(0.9, 0.95, "{:05d}".format(numi), transform=a.transAxes)
    #plt.text(0.9, 0.90, "{:05d}".format(numj), transform=a.transAxes)
    plt.savefig('NGC6334-{:05}-{:05}.png'.format(numi,numj))
    plt.close()

    #plt.show()


######################################################################################o
global numi
global numj
numi = 0
numj = 0


username = ''
password = ''
database = 'gustoDBlp'
retention_policy = 'autogen'
bucket = f'{database}/{retention_policy}'

# NGC6334 coordinates I
#Walsh 2007 MOPRA 12CO coordinates 5' x 5'
ra  = '+17h20m54s'
dec = '-35d46m12s'

# NGC6334 coordinates SOFIA 120K line
ra  = '+17h20m32s'
dec = '-35d51m20s'

# half-beam size
size = 25*u.arcsec
c = SkyCoord(ra, dec, frame='icrs')

# half-image size
ra_img =  30*u.arcmin
dec_img = 30*u.arcmin

# undersample map

# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')

start_ra = c.ra.deg - ra_img.to(u.deg).value
end_ra   = c.ra.deg + ra_img.to(u.deg).value
N_ra     = int(ra_img.to(u.arcmin).value/size.to(u.arcmin).value/9)
ra_indx = np.linspace(start_ra, end_ra, N_ra)

start_dec = c.dec.deg - dec_img.to(u.deg).value
end_dec   = c.dec.deg + dec_img.to(u.deg).value
N_dec     = int(dec_img.to(u.arcmin).value/size.to(u.arcmin).value/9)
dec_indx = np.linspace(start_dec, end_dec, N_dec)

global integrated_intensity
integrated_intensity = np.zeros(shape=(N_dec, N_ra))

for ra in ra_indx:
    numi += 1
    numj = 0
    for dec in dec_indx:
        numj += 1
        print('{:f}'.format(ra), '{:f}'.format(dec))
        # find all points in udpPointing where we pointed at ra, dec
        myquery = f'SELECT * FROM "udpPointing" WHERE RA<{(ra +size.to(u.deg).value)}  AND \
                                                      RA>{(ra -size.to(u.deg).value)}  AND \
                                                     DEC<{(dec+size.to(u.deg).value)}  AND \
                                                     DEC>{(dec-size.to(u.deg).value)}'
        points = client.query(myquery).get_points()

        scanID_indx_list=[[0]*2]

        src_files=[]
        ref_files=[]
        hot_files=[]

        # For loop over all of these pointings
        # POINTS contains a (time, scanID) for each pointing at (ra,dec)
        for point in points:
            # get a time object at a single pointing
            time_string = point.get('time')
            nofrac, frac = time_string.rsplit('.')
            nofrac_dt = datetime.datetime.strptime(nofrac, '%Y-%m-%dT%H:%M:%S')
            dt = nofrac_dt.replace(microsecond=int(frac.strip('Z')))
  
            # Find source files with same scanID within 1 second of that point
            # restrict spectra search to the current scanID
            # for ~ single beam spacing, usually results in ~ 10 spectra
            file_pattern = f'../GUSTO-DATA/spectra/ACS3_OTF_{point.get("scanID")}_DEV4_INDX*'
            search_files = glob.glob(file_pattern)
            for file in search_files:
                fp = open(file, 'r')
                unixtime = fp.readline().split('\t')[1]
                fp.close()
                # look through these spectra for matching times
                if(int(unixtime) == int(nofrac_dt.timestamp())):  # Find spectra within 1 sec
                    src_files.extend(glob.glob(file)) # add spectra filename to array

                    # Get scanIDs and INDX numbers of SRC files to limit REFs and HOTs
                    scanID_indx_list.append([int(point.get('scanID')), int(file.split("_")[4][4:])])

        # remove duplicates from scanID & INDX list
        seen=set()
        newlist=[]
        for item in scanID_indx_list:
            t = tuple(item)
            if t not in seen:
                newlist.append(item)
                seen.add(t)
        scanID_indx_list = newlist[1:]


        # Find suitable calibration files
        for scanID_indx in scanID_indx_list:
            ID   = str(scanID_indx[0])
            file_pattern = f'../GUSTO-DATA/spectra/ACS3_HOT_{ID}_DEV4_INDX*_'
            search_files = glob.glob(file_pattern)
            for file in search_files:
                fp = open(file, 'r')
                unixtime = fp.readline().split('\t')[1]
                fp.close()
                # look through these spectra for matching times
                if(int(unixtime) < int(nofrac_dt.timestamp())):  # Find spectra within 1 sec
                    hot_files.extend(glob.glob(file)) # add spectra filename to array


        # Find suitable reference files with + or -1 OTF scanID
        # TODO: base on time and select earlier OR later reference scan
        for scanID_indx in scanID_indx_list:
            ID   = str(scanID_indx[0])
            file_pattern = f'../GUSTO-DATA/spectra/ACS3_REF_{ID}_DEV4_INDX*'
            search_files = glob.glob(file_pattern)

            prev=-1
            while not ref_files:
                for file in search_files:
                    if( os.path.isfile(file) ):
                        ref_files.extend(glob.glob(file))
                curID = str(int(point.get("scanID"))+prev)
                file_pattern = f'../GUSTO-DATA/spectra/ACS3_REF_{curID}_DEV4_INDX*'
                search_files = glob.glob(file_pattern)
                prev+=2

        #print("waiting:")
        #time.sleep(3)

        if not src_files or not ref_files:
            print("no files")
            exit
        else:
            srcx, srcy = read_and_average_files(src_files, n_lines_header=25)   # Average SRC
           
            for srcf in src_files:
                print(srcf)
            for reff in ref_files:
                print(reff)
    
            refx, refy = read_and_average_files(ref_files, n_lines_header=25)   # Average REF
    
            subtraction_ratio = (srcy - refy ) / refy
            spec = subtraction_ratio - np.mean(subtraction_ratio[185:267])


            # combine src, hot, and ref from multiple scanIDs and plot
            plot_subtraction_ratio(srcx, spec, (-30, 30), (-1, 5))

plt.contour(integrated_intensity)
plt.savefig('NGC6334-contour.png')
#plt.show()



# Before we leave, get a current-ish CAL temperature
# TODO: pass this temp along to the plot T-A-star
#scans = f''
#scanID = int(point.get("scanID"))
#for i in range(1,6):
#    if(i!=5): scans = scans+'{:d}|'.format(scanID-2)
#    if(i==5): scans = scans+'{:d}'.format(scanID-2)
#    scanID+=1
#myquery = 'SELECT last(*) FROM "HK_TEMP11" WHERE "scanID"=~/({:s})/'.format(scans)
#points = client.query(myquery).get_points()
#for point in points:
#    T_CAL = point.get('last_temp')
#print(T_CAL)
#print("Cal temp is {:f}".format(T_CAL))
  

# Use influxdb_client for V2.0 (with V1.8 compatibility)
# https://influxdb-client.readthedocs.io/en/stable/#
'''
client = InfluxDBClient(url='http://127.0.0.1:8086', token=f'{username}:{password}', org='-')
query_api = client.query_api()
query = f'from(bucket: \"{bucket}\")\
             |> range(start: 0) \
             |> filter(fn: (r) => r["_measurement"] == "udpPointing") \
             |> filter(fn: (r) => r["_RA"] < \"{(c.ra+size).deg}\" AND   r["_RA"] > \"{(c.ra+size).deg}\") \
             |> filter(fn: (r) => r["_DEC"] < \"{(c.dec+size).deg}\" AND r["_DEC"] > \"{(c.dec+size).deg}\")'
                
tables = query_api.query(query)
# It's 106 miles to Chicago.  We got a full tank of gas, half a pack of cigarettes, it's dark, and we're wearing sunglasses.  
# Hit it.

for record in tables[0].records:
  (f'{record.get_time()} {record.get_measurement()}: {record.get_value()}')

time_string = f'{get_time()}'.split('.')[0]
d = datetime.datetime.strptime(time_string, '7Y-%m-%d %H:%M:%S')
print(d)
'''



