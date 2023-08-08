#!/usr/bin/python3
import ctypes
import sys
import time
import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--lags", help="number of lags", default="128")
parser.add_argument("-d", "--dev", help="HIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.1.201")
parser.add_argument("-tftp", "--tftp", help="tftp IP address", default="192.168.1.20")
args = parser.parse_args()

lags=args.lags
dev=args.dev
serverip=args.serverip
tftp=args.tftp

#connect socket
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((serverip, 9734))

#Setup                    CMD LEN             DEV LAG FTP
s.send(b'\x0e\x00\x00\x00\x81\x05\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)
#Setup                    CMD LEN             DEV LAG FTP
s.send(b'\x0e\x00\x00\x00\x81\x05\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)
#Setup                    CMD LEN             DEV LAG FTP
s.send(b'\x0e\x00\x00\x00\x81\x05\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)
#Setup                    CMD LEN             DEV LAG FTP
s.send(b'\x0e\x00\x00\x00\x81\x05\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)

#ACS power                CMD LEN             DEV  ON
s.send(b'\x0e\x00\x00\x00\x88\x05\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)
#ACS power                CMD LEN             DEV  ON
s.send(b'\x0e\x00\x00\x00\x88\x05\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)
#ACS power                CMD LEN             DEV  ON
s.send(b'\x0e\x00\x00\x00\x88\x05\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)
#ACS power                CMD LEN             DEV  ON
s.send(b'\x0e\x00\x00\x00\x88\x05\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00')
time.sleep(0.5)
data=s.recv(100)
print(data)

s.close()
