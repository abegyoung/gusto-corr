
from influxdb_client import InfluxDBClient, Point


    # Python influxdb_client with library backward v1.8
    username = ''
    password = ''
    database = 'gustoDBlp'
    retention_policy = 'autogen'
    bucket = f'{database}/{retention_policy}'

    client = InfluxDBClient(url='http://192.168.1.11:8086', token=f'{username}:{password}', org='-')

