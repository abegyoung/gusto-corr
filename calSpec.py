#!/usr/bin/env python3
import sys
import time
import ctypes
import socket
import struct
import argparse
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="HIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.1.201")
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

#AUTO CAL              CMD LEN              DEV    NUM
cmd=b'\x0b\x00\x00\x00\x87\x02\x00\x00\x00'+DEV+b'\x14\x00\x00\x00\x00'
s.send(cmd)
time.sleep(1)
data=s.recv(100)
VIhi = struct.unpack("<f", data[11:15])
VQhi = struct.unpack("<f", data[15:19])
VIlo = struct.unpack("<f", data[19:23])
VQlo = struct.unpack("<f", data[23:27])
print('VIhi = {:.3f}'.format(VIhi[0]))
print('VQhi = {:.3f}'.format(VQhi[0]))
print('VIlo = {:.3f}'.format(VIlo[0]))
print('VQlo = {:.3f}'.format(VQlo[0]))

s.close()
