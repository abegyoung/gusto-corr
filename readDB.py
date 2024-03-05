import sys
import csv
from datetime import datetime
from influxdb import InfluxDBClient

# Example usage:

#x_name = sys.argv[1]
#y_name = sys.argv[2]

client = InfluxDBClient('localhost', 8086, '', '', 'gustoDBlp')

result = client.query('select * from LHE_LEVEL;')

print("Result: {0}".format(result))

