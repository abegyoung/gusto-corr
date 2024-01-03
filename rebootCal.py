#!/opt/local/bin/python3.10
import ctypes
import sys
import time
import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--lags", help="number of lags", default="128")
parser.add_argument("-d", "--dev", help="HIFAS #", default="1")
parser.add_argument("-ip", "--serverip", help="correlator IP address", default="192.168.1.203")
parser.add_argument("-tftp", "--tftp", help="tftp IP address", default="192.168.1.20")
args = parser.parse_args()

lags=args.lags
dev=args.dev
serverip=args.serverip
tftp=args.tftp

#connect socket
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((serverip, 9734))

#REBOOT_ACS            CMD LEN              
cmd=b'\x0a\x00\x00\x00\xa1\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
bytes_to_get=int.from_bytes(recv_len(s, 4), byteorder='little')
data=recv_len(s, bytes_to_get)
print(data)

s.close()
