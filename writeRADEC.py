import sys
import numpy
from datetime import datetime
from influxdb import InfluxDBClient
from astropy.coordinates import EarthLocation, AltAz, SkyCoord
from astropy.time import Time
import astropy.units as u

# Script to get UDP pointing data into an Influx Database from GUSTO series_*_*.tar.gz files

table=numpy.genfromtxt(str(sys.argv[1]), usecols=(0,1,2,3,4,5,6))
for line in table: 
    #      name    time    scanID   volt
    name = "udpPointing"
    time_cap = datetime.utcfromtimestamp(float(line[0])).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    alt    = float(line[1])
    lat    = float(line[2])
    lon    = float(line[3])
    ra     = float(line[4])
    dec    = float(line[5])
    scanID =   int(line[6])

    location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=alt*u.m)
    observation_time = Time(time_cap)
    sky_coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg, frame='icrs')
    altaz_frame = AltAz(obstime=observation_time, location=location)
    altaz_coord = sky_coord.transform_to(altaz_frame)

    json_body = [
        {
        "measurement": "{}".format(name),
            "tags": {
                "scanID": "{}".format(scanID)
            },
        "time": "{}".format(time_cap),
            "fields": {
                "ALT": float(alt),
                "LAT": float(lat),
                "LON": float(lon),
                "RA":  float(ra),
                "DEC": float(dec),
                "AZ":  float(altaz_coord.az.deg),
                "EL":  float(altaz_coord.alt.deg)
            }
        }
    ]

    #print(json_body)
    client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')
    client.write_points(json_body)
