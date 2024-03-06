#!/usr/bin/env python3
import numpy
from astropy import units as u
from astropy.coordinates import SkyCoord

table=numpy.genfromtxt("udp.txt", usecols=(-3,-2))

for line in table[:6700000:100]:
  c = SkyCoord(ra=line[0]*u.degree, dec=line[1]*u.degree, frame='icrs')
  print(f'{c.galactic.l.value} {c.galactic.b.value}')

