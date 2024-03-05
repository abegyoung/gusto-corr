import sys
import csv
from datetime import datetime
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
for point in points:
  print(point)



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

for record in tables[0].records:
  (f'{record.get_time()} {record.get_measurement()}: {record.get_value()}')

time_string = f'{get_time()}'.split('.')[0]
d = datetime.datetime.strptime(time_string, '7Y-%m-%d %H:%M:%S')
print(d)
'''



