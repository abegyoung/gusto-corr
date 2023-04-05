#!/usr/bin/python3
import sys
import time
import ctypes
import socket
import struct
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="HIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.0.201")
args = parser.parse_args()

dev=int(args.dev)
DEV=dev.to_bytes(1, byteorder='little')
serverip=args.serverip

#connect socket
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((serverip, 9734))

def recv_len(the_socket, length):
  chunks = []
  bytes_recd = 0
  while bytes_recd < length:
    chunk = the_socket.recv(min(length - bytes_recd, 2048))
    if chunk == b'':
      raise RuntimeError("socket broken")
    chunks.append(chunk)
    bytes_recd = bytes_recd + len(chunk)
  return b''.join(chunks)

#READ CAL              CMD LEN             DEV
cmd=b'\x0a\x00\x00\x00\x07\x01\x00\x00\x00'+DEV+b'\x00\x00\x00\x00'
s.send(cmd)
bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little')
data=recv_len(s, bytes_to_get)
VIhi = struct.unpack("<f", data[ 7:11])
VQhi = struct.unpack("<f", data[11:15])
VIlo = struct.unpack("<f", data[15:19])
VQlo = struct.unpack("<f", data[19:23])

TRG=(1<<(dev-1)).to_bytes(1, byteorder='little')
#TRIGGER               CMD LEN              TRG
cmd=b'\x0a\x00\x00\x00\x83\x01\x00\x00\x00'+TRG+b'\x00\x00\x00\x00'
s.send(cmd)
bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little')
data=recv_len(s, bytes_to_get)

#wait until fifo available
fifo=0
while (fifo==0):
  #         LEN             CMD LEN            (==============)
  s.send(b'\x09\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00')
  time.sleep(.05)
  bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little')
  data=recv_len(s, bytes_to_get)
  print(data)
  fifo=int.from_bytes(data[6:10], byteorder='little')

#READ OUTPUT
#         LEN          CMD LEN              DEV
cmd=b'\x0a\x00\x00\x00\x06\x01\x00\x00\x00'+DEV+b'\x00\x00\x00\x00'
print(cmd)
s.send(cmd)
bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little') + 4
#read another 5 bytes 0x06 cmd readback data
data=recv_len(s, 5)
#read 8300 bytes of header and lags (for 512 lags)
data=recv_len(s, bytes_to_get-9)

#save binary output
#fp=open("lags.bin", "wb")
#fp.write(data)
#fp.close()

#save text output
fp=open("out.lags", "w")
print("FIFO",fifo,file=fp)

#remaining 8300 bytes are header and lags
UNIT=    int.from_bytes(data[ 0: 4], byteorder='little')
DEV=     int.from_bytes(data[ 4: 8], byteorder='little')
NINT=    int.from_bytes(data[ 8:12], byteorder='little')
UNIXTIME=int.from_bytes(data[12:20], byteorder='little')
CPU=     int.from_bytes(data[20:24], byteorder='little')
NBYTES=  int.from_bytes(data[24:28], byteorder='little')
CORRTIME=int.from_bytes(data[28:32], byteorder='little')
EMPTY0=  int.from_bytes(data[32:36], byteorder='little')
Ihigh=   int.from_bytes(data[36:40], byteorder='little')
Qhigh=   int.from_bytes(data[40:44], byteorder='little')
Ilow =   int.from_bytes(data[44:48], byteorder='little')
Qlow =   int.from_bytes(data[48:52], byteorder='little')
Ierr =   int.from_bytes(data[52:56], byteorder='little')
Qerr =   int.from_bytes(data[56:60], byteorder='little')
EMPTY1=  int.from_bytes(data[60:64], byteorder='little')
EMPTY2=  int.from_bytes(data[64:68], byteorder='little')
EMPTY3=  int.from_bytes(data[68:72], byteorder='little')
EMPTY4=  int.from_bytes(data[72:76], byteorder='little')
EMPTY5=  int.from_bytes(data[76:80], byteorder='little')
EMPTY6=  int.from_bytes(data[80:84], byteorder='little')
EMPTY7=  int.from_bytes(data[84:88], byteorder='little')
EMPTY8=  int.from_bytes(data[88:92], byteorder='little')
print("UNIT",UNIT, file=fp)
print("DEV",DEV, file=fp)
print("NINT",NINT, file=fp)
print("UNIXTIME",datetime.utcfromtimestamp(UNIXTIME/1000).strftime('%Y-%m-%d_%H:%M:%S.%f')[:-3],file=fp)
print("CPU",CPU,file=fp)
print("NBYTES",NBYTES,file=fp)
print("CORRTIME",CORRTIME,file=fp)
print("EMPTY0",EMPTY0,file=fp)
print("Ihigh",Ihigh,file=fp)
print("Qhigh",Qhigh,file=fp)
print("Ilow",Ilow,file=fp)
print("Qlow",Qlow,file=fp)
print("Ierr",Ierr,file=fp)
print("Qerr",Qerr,file=fp)
print("EMPTY1",EMPTY1,file=fp)
print("EMPTY2",EMPTY2,file=fp)
print("EMPTY3",EMPTY3,file=fp)
print("EMPTY4",EMPTY4,file=fp)
print("EMPTY5",EMPTY5,file=fp)
print("EMPTY6",EMPTY6,file=fp)
print("EMPTY7",EMPTY7,file=fp)
print("EMPTY8",EMPTY8,file=fp)
print('VIhi {:.3f}'.format(VIhi[0]),file=fp)
print('VQhi {:.3f}'.format(VQhi[0]),file=fp)
print('VIlo {:.3f}'.format(VIlo[0]),file=fp)
print('VQlo {:.3f}'.format(VQlo[0]),file=fp)

if(int(NBYTES)==8256):
  NLAGS=512
elif(int(NBYTES)==6208):
  NLAGS=384
elif(int(NBYTES)==4160):
  NLAGS=256
elif(int(NBYTES)==2112):
  NLAGS=128

for i in range(0,NLAGS):
  II = int.from_bytes(data[ 92+16*i: 96+16*i], byteorder='little')
  IQ = int.from_bytes(data[ 96+16*i:100+16*i], byteorder='little')
  QI = int.from_bytes(data[100+16*i:104+16*i], byteorder='little')
  QQ = int.from_bytes(data[104+16*i:108+16*i], byteorder='little')
  print(ctypes.c_int32(II).value, ctypes.c_int32(QI).value,ctypes.c_int32(IQ).value,ctypes.c_int32(QQ).value,file=fp)

s.close()
fp.close()
