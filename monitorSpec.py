#!/usr/bin/env python3
import sys
import time
import ctypes
import socket
import struct
import argparse
from datetime import datetime
import subprocess
from collections import namedtuple

parser = argparse.ArgumentParser()
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.1.201")
args = parser.parse_args()

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

#READ CAL              CMD LEN             SUF
cmd=b'\x09\x00\x00\x00\x0C\x00\x00\x00\x00\x00\x00\x00\x00'
s.send(cmd)
bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little')
data=recv_len(s, bytes_to_get)
off=5

N=80
corrhk=[None]*N
corrhk=["Input5p0V", "", "Input5p0I", "", "Input3p6V", "", "Input3p6I", "", \
        "Input3p0V", "", "Input3p0I", "", "Input2p1V", "", "Input2p1I", "", \
        "Local1p2V", "", "Local1p2I", "", "Local1p8V", "", "Local1p8I", "", \
        "Local2p5V", "", "Local2p5I", "", "Local3p3V", "", "Local3p3I", "", \

        "HIFAS_1_1p8V", "", "HIFAS_2_1p8V", "", "HIFAS_3_1p8V", "", "HIFAS_4_1p8V", "", \
        "HIFAS_1_1p8I", "", "HIFAS_2_1p8I", "", "HIFAS_3_1p8I", "", "HIFAS_4_1p8I", "", \
        "HIFAS_1_2p5V", "", "HIFAS_2_2p5V", "", "HIFAS_3_2p5V", "", "HIFAS_4_2p5V", "", \
        "HIFAS_1_2p5I", "", "HIFAS_2_2p5I", "", "HIFAS_3_2p5I", "", "HIFAS_4_2p5I", "", \

        "ADC_1_VCC",  "", "ADC_2_VCC",  "", "ADC_3_VCC",  "", "ADC_4_VCC",  "", \
        "ADC_1_TEMP", "", "ADC_2_TEMP", "", "ADC_3_TEMP", "", "ADC_4_TEMP", ""]

j=0
for i in range(0,N,2):
  corrhk[i+1]=str(struct.unpack("<f",data[(j*4)+off:(j*4+4)+off]))
  j=j+1

Volts = namedtuple('Volts', corrhk[::2])
v = Volts._make(corrhk[1::2])

for i in range(0,N,2):
  print("{}".format(corrhk[i]), "{:.3f}".format(float(corrhk[i+1][1:-2])))



s.close()
