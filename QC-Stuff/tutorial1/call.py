import time
import random
from typing import List
from zugbruecke import CtypesSession
ctypes = CtypesSession(arch = 'win64')

_dll = ctypes.windll.LoadLibrary('demo.dll')
_bubblesort = _dll.bubblesort
_bubblesort.argtypes = (ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.POINTER(ctypes.c_double))
_bubblesort.memsync = [
    dict(
        pointer = [0], # pointer argument
        length  = [1], # length argument
        type = ctypes.c_double, # array element type
    ),
    dict(
        pointer = [2], # pointer argument
        length  = [1], # length argument
        type = ctypes.c_double, # array element type
    )
]

def bubblesort(valuesIn: List[ctypes.c_double], valuesOut: List[ctypes.c_double]):
    "user-facing wrapper around DLL function"
    double_arrayIn = ((ctypes.c_double)*len(valuesIn))(*valuesIn)
    pointer_firstelementIn = ctypes.cast(ctypes.pointer(double_arrayIn), ctypes.POINTER(ctypes.c_double))
    double_arrayOut = ((ctypes.c_double)*len(valuesOut))(*valuesOut)
    pointer_firstelementOut = ctypes.cast(ctypes.pointer(double_arrayOut), ctypes.POINTER(ctypes.c_double))

    _bubblesort(pointer_firstelementIn, len(valuesIn), pointer_firstelementOut) # call into DLL
    valuesOut[:] = double_arrayOut[:]

def make_vec(self):
    for i in range(0,10):
        self[i] = float("{:.2f}".format((random.random()*10)))

in_vector = [None]*10
out_vector = [0,0,0,0,0,0,0,0,0,0]

make_vec(in_vector)
print(in_vector)
bubblesort(in_vector, out_vector)
print(out_vector)
print("")
