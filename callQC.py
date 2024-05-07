import warnings
import numpy as np
import random
from zugbruecke import CtypesSession
warnings.simplefilter("ignore")
ctypes = CtypesSession(arch = 'win64')

dll = ctypes.windll.LoadLibrary('QuantCorrDLL64.dll')
_qc = dll.qc
_qc.argtypes = (
           ctypes.c_double, # XmonL
           ctypes.c_double, # XmonH
           ctypes.c_double, # YmonL
           ctypes.c_double, # YmonH
           ctypes.POINTER(ctypes.c_double),  # XYin
           ctypes.c_int,                     # nElem
           ctypes.POINTER(ctypes.c_double))  # XYqc
_qc.restype = ctypes.c_int
_qc.memsync = [
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
_relpower = dll.relpower
_relpower.argtypes = (ctypes.c_double, ctypes.c_double)
_relpower.restype  = ctypes.c_double


def relpower(monL, monH):

    return  _relpower(monL, monH)

def qc(XmonL, XmonH, YmonL, YmonH, XY):

    nElem = len(XY)
    XYin  = (ctypes.c_double * nElem)()
    XYout = (ctypes.c_double * nElem)()
    for i in range(0,nElem):
        XYin[i] = XY[i]

    _qc(XmonL, XmonH, YmonL, YmonH, XYin, nElem, XYout)

    return [value for value in XYout]

