import sys
import csv
from datetime import datetime
from influxdb import InfluxDBClient

# Example usage:
f = open(str(sys.argv[1]), 'r')
c = csv.reader(f)
for row in c: 
  if(row[0] == "name"):
    # row is column names
    pass
  else:
    if ("ACS" in row[0]):
      #      name    time    scanID   volt
      name = row[0]
      time_cap = datetime.fromtimestamp(int(row[1])/1000000000).strftime("%Y-%m-%dT%H:%M:%SZ")
      try: 
        scanID = int(row[6])
      except:
        scanID = int(row[7])

      try:
        volt = float(row[10])
      except:
        volt = float(row[11])

      json_body = [
         {
            "measurement": "{}".format(name),
            "tags": {
               "scanID": "{}".format(scanID)
            },
            "time": "{}".format(time_cap),
            "fields": {
               "volt": float(volt)
            }
         }
      ]

      print(json_body)
      client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')
      client.write_points(json_body)

