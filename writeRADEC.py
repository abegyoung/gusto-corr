import sys
import numpy
from datetime import datetime
from influxdb import InfluxDBClient


# Script to get UDP pointing data into an Influx Database from GUSTO series_*_*.tar.gz files

table=numpy.genfromtxt(str(sys.argv[1]), usecols=(0,4,5,6))
for line in table: 
    #      name    time    scanID   volt
    name = "udpPointing"
    time_cap = datetime.fromtimestamp(float(line[0])).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    ra     = float(line[1])
    dec    = float(line[2])
    scanID =   int(line[3])

    json_body = [
        {
        "measurement": "{}".format(name),
            "tags": {
                "scanID": "{}".format(scanID)
            },
        "time": "{}".format(time_cap),
            "fields": {
                "RA": float(ra),
                "DEC": float(dec)
            }
        }
    ]

    #print(json_body)
    client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')
    client.write_points(json_body)
