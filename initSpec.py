#!/usr/bin/env python3
import ctypes
import sys
import time
import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--lags", help="\tNumber of lags", default="512")
parser.add_argument("-d", "--dev", help="\tHIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="\tcorrelator IP address", default="192.168.1.201")
parser.add_argument("-i", "--intTime", help="\tintegration time (usec)", default="250000")
parser.add_argument("-p", "--path", help="\tPATH", default="/var/tmp")
parser.add_argument("-f", "--fname", help="\tFILENAME", default="default")
parser.add_argument("-off", "--off", help="\tturn off ACS PWR", action='store_true')
parser.add_argument("-s", "--save", help="\tSave spectra", default='0')
parser.add_argument("-t", "--tftp", help="\tUse TFTP", default='0')
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
fname=args.fname
save=args.save
tftp=args.tftp

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
  time.sleep(0.2)
  data=s.recv(100)
  print(data)


#ACS Setup
TFTP=int((int(tftp)<<1)+int(save)).to_bytes(1, byteorder='little')
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
  time.sleep(0.2)
  data=s.recv(100)
  print(data)


#Integration Time
TIME=int(intTime).to_bytes(4, byteorder='little')
for a in range(*devlist):
  DEV=a.to_bytes(1, byteorder='little')
  cmd=b'\x0e\x00\x00\x00'+b'\x82\x05\x00\x00\x00'+DEV+TIME+b'\x00\x00\x00\x00'
  s.send(cmd)
  time.sleep(0.2)
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
time.sleep(0.2)
data=s.recv(100)
print(data)


#Set output FILENAME
#CMD=b'\x90'
#FNAME=bytes(fname, 'utf-8')+b'\x00\x00'
#SUF=b'\x00\x00\x00\x00'
#LEN2=(len(FNAME)).to_bytes(4, byteorder='little')
#LEN1=(len(CMD)+len(LEN2)+len(FNAME)+len(SUF)).to_bytes(4, byteorder='little')
#cmd=LEN1+CMD+LEN2+FNAME+SUF
#s.send(cmd)
#time.sleep(0.2)
#data=s.recv(100)
#print(data)


s.close()
