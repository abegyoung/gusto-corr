#!/usr/bin/python3
import sys
import time
import ctypes
import socket
import struct
import argparse

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

#ABORT_ACS             CMD LEN              DEV
cmd=b'\x0a\x00\x00\x00\x84\x01\x00\x00\x00'+DEV+b'\x00\x00\x00\x00'
s.send(cmd)
time.sleep(1)
data=s.recv(100)
print(data)

s.close()
