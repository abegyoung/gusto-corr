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

import glob
import numpy as np
import datetime
from influxdb import InfluxDBClient
#from influxdb_client import InfluxDBClient

from astropy import units as u
from astropy.coordinates import SkyCoord

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


# Use influxdb for V1.0
# https://influxdb-python.readthedocs.io/en/latest/index.html
client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')
myquery = f'SELECT * FROM "udpPointing" WHERE RA<{(c.ra+size).deg} AND RA>{(c.ra-size).deg} \
                                      AND DEC<{(c.dec+size).deg} AND DEC>{(c.dec-size).deg}'
points = client.query(myquery).get_points()

files=[]
for point in points:
    time_string = point.get('time')
    nofrac, frac = time_string.rsplit('.')
    nofrac_dt = datetime.datetime.strptime(nofrac, '%Y-%m-%dT%H:%M:%S')
    dt = nofrac_dt.replace(microsecond=int(frac.strip('Z')))
  
    file_pattern = f'/home/young/Desktop/GUSTO-DATA/spectra/ACS3_OTF_{point.get("scanID")}_DEV4_INDX*'
    search_files = glob.glob(file_pattern)
    for file in search_files:
        fp = open(file, 'r')
        unixtime = fp.readline().split('\t')[1]
        fp.close()
        if(int(unixtime) == int(nofrac_dt.timestamp())):
            print(file)
            files.extend(glob.glob(file))

  

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



