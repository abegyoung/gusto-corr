import sys
import numpy
from datetime import datetime
from influxdb import InfluxDBClient


# Script to get UDP pointing data into an Influx Database from GUSTO series_*_*.tar.gz files

dtype = [('col1', 'i4'),('col2', 'i4'),('col3', 'i4'),('col4', 'f8'),('col5', 'i4'),('col6', 'U10')]

table=numpy.genfromtxt(str(sys.argv[1]), usecols=(0,1,2,3,4,5), dtype=dtype)
for line in table: 
    #      name    time    scanID   volt
    name = "tuning"
    time_cap = datetime.fromtimestamp(float(line[0])).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    B1IF   = float(line[1])
    B2IF   = float(line[2])
    VLSR   = float(line[3])
    scanID =   int(line[4])
    target =   str(line[5])

    json_body = [
        {
        "measurement": "{}".format(name),
            "tags": {
                "scanID": "{}".format(scanID)
            },
        "time": "{}".format(time_cap),
            "fields": {
                "B1IF":   int(B1IF),
                "B2IF":   int(B2IF),
                "VLSR":   float(VLSR),
                "TARGET": target
            }
        }
    ]

    #print(json_body)
    client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')
    client.write_points(json_body)
