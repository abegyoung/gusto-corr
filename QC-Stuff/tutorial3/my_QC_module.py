from zugbruecke import CtypesSession
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

def my_relpower_function(a, b, corrtime):
   return _relpower(a/corrtime, b/corrtime)

def my_qc_function(a,b,c,d,XY):

   nElem = 10
   
   for i in range(0,nElem):
      print('{:.6f} '.format(XY[i]), end='')
   print()

   XYin  = (ctypes.c_double * nElem)()
   XYout = (ctypes.c_double * nElem)()
   for i in range(0,nElem):
     XYin[i]  = XY[i]

   _qc(a, b, c, d, XYin, nElem, XYout)

   return [value for value in XYout]
