from zugbruecke import CtypesSession
ctypes = CtypesSession(arch = 'win64')

def my_relpower_function(a, b, corrtime):
   dll = ctypes.windll.LoadLibrary('QuantCorrDLL64.dll')
   relpower = dll.relpower
   relpower.argtypes = (ctypes.c_double, ctypes.c_double)
   relpower.restype  = ctypes.c_double

   return relpower(a/corrtime, b/corrtime)

