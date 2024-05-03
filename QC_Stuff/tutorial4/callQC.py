import warnings
import numpy as np
import random
from zugbruecke import CtypesSession
ctypes = CtypesSession(arch = 'win64')

warnings.simplefilter("ignore")

dll = ctypes.windll.LoadLibrary('QuantCorrDLL64.dll')
qc = dll.qc
qc.argtypes = (
               ctypes.c_double, # ImonL
               ctypes.c_double, # ImonH
               ctypes.c_double, # QmonL
               ctypes.c_double, # QmonH
               ctypes.POINTER(ctypes.c_double),  # XYin
               ctypes.c_int,                     # nElem
               ctypes.POINTER(ctypes.c_double))  # XYqc
qc.restype = ctypes.c_int
qc.memsync = [
    dict(
        pointer = [4],
        length = [5],
        type = ctypes.c_double
    ),
    dict(
        pointer = [6],
        length = [5],
        type = ctypes.c_double
    )
]

relpower = dll.relpower
relpower.argtypes = (ctypes.c_double, ctypes.c_double)
relpower.restype  = ctypes.c_double

# use for REF
txtfile = f'./QClags/ACS3_REF_14766_DEV4_INDX0000_NINT002.txt'
txtdata = np.genfromtxt(txtfile, dtype=str, max_rows=25, usecols=[0,1])
lagfile = f'./QClags/ACS3_REF_14766_DEV4_INDX0000_NINT002.lag'
lagdata = np.loadtxt(lagfile, skiprows=0)
fileout = f'./QClags/ACS3_REF_14766_DEV4_INDX0000_NINT002_QC.lag'

# use for OTF
#txtfile = f'./QClags/ACS3_OTF_14767_DEV4_INDX0000_NINT002.txt'
#txtdata = np.genfromtxt(txtfile, dtype=str, max_rows=25, usecols=[0,1])
#lagfile = f'./QClags/ACS3_OTF_14767_DEV4_INDX0000_NINT002.lag'
#lagdata = np.loadtxt(lagfile, skiprows=0)
#fileout = f'./QClags/ACS3_OTF_14767_DEV4_INDX0000_NINT002_QC.lag'

# use for HOT
#txtfile = f'./QClags/ACS3_HOT_14767_DEV4_INDX0000_NINT002.txt'
#txtdata = np.genfromtxt(txtfile, dtype=str, max_rows=25, usecols=[0,1])
#lagfile = f'./QClags/ACS3_HOT_14767_DEV4_INDX0000_NINT002.lag'
#lagdata = np.loadtxt(lagfile, skiprows=0)
#fileout = f'./QClags/ACS3_HOT_14767_DEV4_INDX0000_NINT002_QC.lag'

f = open(fileout, 'w')

data_dict = {}
for row in txtdata:
    key, value = row
    data_dict[key] = float(value) if '.' in value else int(value)
 
corrtime = data_dict.get('CORRTIME')*5000*1e6/256
ImonH = data_dict.get('IHI')/corrtime
QmonH = data_dict.get('QHI')/corrtime
ImonL = data_dict.get('ILO')/corrtime
QmonL = data_dict.get('QLO')/corrtime
nElem = 512

# Lag file format from corrspec is II, QI, IQ, QQ
IIin = (ctypes.c_double * nElem)()
QIin = (ctypes.c_double * nElem)()
IQin = (ctypes.c_double * nElem)()
QQin = (ctypes.c_double * nElem)()
for i in range(0,nElem):
  IIin[i] = lagdata[i,1] / corrtime
  QIin[i] = lagdata[i,2] / corrtime
  IQin[i] = lagdata[i,3] / corrtime
  QQin[i] = lagdata[i,4] / corrtime

IIqc = (ctypes.c_double * nElem)()
QIqc = (ctypes.c_double * nElem)()
IQqc = (ctypes.c_double * nElem)()
QQqc = (ctypes.c_double * nElem)()

qc(ImonL, ImonH, ImonL, ImonH, IIin, nElem, IIqc)
qc(QmonL, QmonH, ImonL, ImonH, QIin, nElem, QIqc)
qc(ImonL, ImonH, QmonL, QmonH, IQin, nElem, IQqc)
qc(QmonL, QmonH, QmonL, QmonH, QQin, nElem, QQqc)

Ipwr = relpower(ImonL, ImonH)
Qpwr = relpower(ImonL, ImonH)

f.write(str('Ipwr\t{:.6f}\n'.format(Ipwr)))
f.write(str('Qpwr\t{:.6f}\n'.format(Qpwr)))

for i in range(nElem):
    f.write(str('{:d}\t{:.6f}'.format(i,IIqc[i])
                  + '\t{:.6f}'.format(QIqc[i])
                  + '\t{:.6f}'.format(IQqc[i])
                  + '\t{:.6f}\n'.format(QQqc[i])))

f.close()
