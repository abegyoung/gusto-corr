#!/usr/bin/env python3
import sys
import numpy
from astropy import units as u
from astropy.coordinates import SkyCoord

if (len(sys.argv)==1):
    table=numpy.genfromtxt("udp.txt", usecols=(-3,-2), max_rows=10)
else:
    table=[[sys.argv[1], sys.argv[2]]]
            
for line in table[:6700000:100]:
  print(line[0], line[1])
  c = SkyCoord(ra=line[0]*u.degree, dec=line[1]*u.degree, frame='icrs')
  print(f'{c.galactic.l.value} {c.galactic.b.value}')

