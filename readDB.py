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
import numpy as np
import datetime
from influxdb import InfluxDBClient
#from influxdb_client import InfluxDBClient

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.modeling import models, fitting

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
        if not (np.std(second_column[42:62])>40000 or np.all(second_column == 0) or np.any(np.isnan(second_column))):
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
    #my_dpi=96
    #plt.figure(figsize=(120/my_dpi, 120/my_dpi), dpi=my_dpi)

    plt.figure()

    # Plot the subtraction ratio with the first column on the x-axis
    #p1 = Polynomial1D(3)
    #pfit = fitting.LiearLSQFFitter()
    #new_model = 

    plt.step(x_values, subtraction_ratio)
    plt.xlabel('MHz')
    plt.ylabel('(S-R) / R (+ DC offset)')
    a = plt.gca()

    # set visibility of x-axis as False
    xax = a.axes.get_xaxis()

    # set visibility of y-axis as False
    yax = a.axes.get_yaxis()

    # Set limits on the x and y axes
    plt.xlim(x_limit)
    plt.ylim(y_limit)

    plt.tight_layout()
    plt.text(0.8, 0.9, "{:05d}".format(numi), transform=a.transAxes)
    plt.text(0.8, 0.8, "{:05d}".format(numj), transform=a.transAxes)
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

# NGC6334 coordinates
ra  = '+17h20m50s'
dec = '-36d06m54s'

# half-beam size
size = 20*u.arcsec
c = SkyCoord(ra, dec, frame='icrs')

# half-image size
ra_img = 5*u.arcmin
dec_img = 5*u.arcmin


# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')

start_ra = c.ra.deg - ra_img.to(u.deg).value
end_ra   = c.ra.deg + ra_img.to(u.deg).value
N_ra     = int(ra_img.to(u.arcmin).value/size.to(u.arcmin).value)
ra_indx = np.linspace(start_ra, end_ra, N_ra)

start_dec = c.dec.deg - dec_img.to(u.deg).value
end_dec   = c.dec.deg + dec_img.to(u.deg).value
N_dec     = int(dec_img.to(u.arcmin).value/size.to(u.arcmin).value)
dec_indx = np.linspace(start_dec, end_dec, N_dec)

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

        src_files=[]
        ref_files=[]
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

            # Find suitable reference files with equal or earlier scanID
            # TODO: base on time and select earlier OR later reference scan
            file_pattern = f'../GUSTO-DATA/spectra/ACS3_REF_{point.get("scanID")}_DEV4_INDX*'
            search_files = glob.glob(file_pattern)

            last=0
            while not ref_files:
                for file in search_files:
                    if( os.path.isfile(file) ):
                        ref_files.extend(glob.glob(file))
                file_pattern = f'../GUSTO-DATA/spectra/ACS3_REF_{str(int(point.get("scanID"))-last)}_DEV4_INDX*'
                search_files = glob.glob(file_pattern)
                last-=1
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
            spec = subtraction_ratio - np.mean(subtraction_ratio[205:410])
            plot_subtraction_ratio(srcx, spec, (900, 1300), (-.005, .015))

  

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



