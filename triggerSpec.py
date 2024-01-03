#!/usr/bin/python3
import sys
import time
import ctypes
import socket
import struct
import argparse
from datetime import datetime
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dev", help="HIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.1.203")
parser.add_argument("-r", "--read", help="read back spectra <0|1>", default="1")
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

if (dev==0):
  MASK=(15).to_bytes(1, byteorder='little')
else:
  MASK=(1<<(dev-1)).to_bytes(1, byteorder='little')
#TRIGGER               CMD LEN              MASK
cmd=b'\x0a\x00\x00\x00\x83\x01\x00\x00\x00'+MASK+b'\x00\x00\x00\x00'
s.send(cmd)
bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little')
data=recv_len(s, bytes_to_get)

s.close()
