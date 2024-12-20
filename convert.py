#!/usr/bin/env python3
import sys
import numpy
from astropy import units as u
from astropy.coordinates import SkyCoord

if (len(sys.argv)==1):
    table=numpy.genfromtxt("udp.txt", usecols=(-3,-2), max_rows=6800000)
    for line in table[:6800000:1]:
      c = SkyCoord(ra=line[0]*u.degree, dec=line[1]*u.degree, frame='icrs')
      print(f'{c.galactic.l.value} {c.galactic.b.value}')
else:
    c = SkyCoord(ra=float(sys.argv[1])*u.degree, dec=float(sys.argv[2])*u.degree, frame='icrs')
    print(f'{c.galactic.l.value} {c.galactic.b.value}')
            

