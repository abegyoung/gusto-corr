#!/opt/local/bin/python3.10
import ctypes
import sys
import time
import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--lags", help="number of lags", default="512")
parser.add_argument("-d", "--dev", help="HIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.0.201")
parser.add_argument("-i", "--intTime", help="integration time (usec)", default="1000000")
parser.add_argument("-path", "--path", help="PATH", default="/var/tmp")
parser.add_argument("-save", "--save", help="save flag", default="1")
parser.add_argument("-off", "--off", help="turn off ACS PWR", action='store_true')
args = parser.parse_args()

dev=int(args.dev)
if (dev==0):    #If DEV==0, step through all ACS 1-4
  devlist=[1,5]
else:
  devlist=[dev,dev+1]   #If DEV!=0, only Power up ACS

lags=args.lags
intTime=args.intTime
serverip=args.serverip
path=args.path

#connect socket
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((serverip, 9734))

#ACS Power
if args.off:
  ON=int(0).to_bytes(1, byteorder='little')
else:
  ON=int(1).to_bytes(1, byteorder='little')
for a in range(*devlist):
  DEV=a.to_bytes(1, byteorder='little')
  cmd=b'\x0b\x00\x00\x00'+b'\x88\x02\x00\x00\x00'+DEV+ON+b'\x00\x00\x00\x00'
  s.send(cmd)
  time.sleep(0.5)
  data=s.recv(100)
  print(data)


#ACS Setup
TFTP=int(3).to_bytes(1, byteorder='little')
if (int(lags)==512):
  LAG=b'\x0f'
elif (int(lags)==384):
  LAG=b'\x07'
elif (int(lags)==256):
  LAG=b'\x03'
elif (int(lags)==128):
  LAG=b'\x01'
for a in range(*devlist):
  DEV=a.to_bytes(1, byteorder='little')
  cmd=b'\x0c\x00\x00\x00'+b'\x81\x03\x00\x00\x00'+DEV+LAG+TFTP+b'\x00\x00\x00\x00'
  s.send(cmd)
  time.sleep(0.1)
  data=s.recv(100)
  print(data)


#Integration
TIME=int(intTime).to_bytes(4, byteorder='little')
for a in range(*devlist):
  DEV=a.to_bytes(1, byteorder='little')
  cmd=b'\x0e\x00\x00\x00'+b'\x82\x05\x00\x00\x00'+DEV+TIME+b'\x00\x00\x00\x00'
  s.send(cmd)
  time.sleep(0.1)
  data=s.recv(100)
  print(data)

#Set output PATH
CMD=b'\x91'
PATH=bytes(path, 'utf-8')+b'\x00\x00'
SUF=b'\x00\x00\x00\x00'
LEN2=(len(PATH)).to_bytes(4, byteorder='little')
LEN1=(len(CMD)+len(LEN2)+len(PATH)+len(SUF)).to_bytes(4, byteorder='little')
cmd=LEN1+CMD+LEN2+PATH+SUF
s.send(cmd)
time.sleep(0.1)
data=s.recv(100)
print(data)     #PRINT READBACK

#Get output PATH
CMD=b'\x11'
SUF=b'\x00\x00\x00\x00'
LEN2=(0).to_bytes(4, byteorder='little')
LEN1=(len(CMD)+len(LEN2)+len(SUF)).to_bytes(4, byteorder='little')
cmd=LEN1+CMD+LEN2+SUF
s.send(cmd)
time.sleep(0.1)
data=s.recv(100)
print(data)     #PRINT READBACK

#Set output FILENAME
#      LEN                 CMD LEN                   d   e   f   a   u   l   t PAD PAD
#cmd=b'\x12\x00\x00\x00'+b'\x90\x09\x00\x00\x00'+b'\x64\x65\x66\x61\x75\x6c\x74\x00\x00\x00\x00\x00\x00'
#s.send(cmd)
#time.sleep(0.2)
#data=s.recv(100)
#print(data)

s.close()
