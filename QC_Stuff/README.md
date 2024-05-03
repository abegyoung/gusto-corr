# Tutorial #1
example of calling a windows DLL.

A bubblesort algorithm is coded in ANSI C under Windows 10 using mingw 64 bit gcc and a DLL is made.

The Python script call.py in this directory imports the zugbruecke ctypes library and accesses the DLL through a 64 bit wine install.

The void function prototype is:
```
__stdcall __declspec(dllimport) bubblesort(double *, int, double *)
```

Compile with i686-w64-mingw32-gcc to get a 64 bit DLL.
```
i686-w64-mingw32-gcc -o demo.obj -c -O2 -mms-bitfields demo.c
i686-w64-mingw32-gcc -o demo.dll -shared demo.obj
```

## Call program
```
python3 call.py
```

The library function takes three arguments.  First arugment is a pointer to an a C array of type double of unsorted values, the second the size of the input array as a C integer, and the third is a pointer to a C array of type double which will hold the newly sorted values.

This function call mirrors how the Omnisys Quantization Correction function works.

Make sure zugbruecke is in your Python library, and that demo.dll is in the current directory.

## Zugbruecke
```
pip install zugbruecke
```

## Wine
Install winehq-stable and wine-stable-64 using apt from winehq.org

# Tutorial 2
Now we will call the Python zugbruecke ctypes library from a compiled c program.  This is a step closer to getting QuantCorrDLL64.dll into corrspec.

The python function is simple, takes two numbers ```a, b``` and returns the addition.

The function ```my_python_function()``` is defined in the python script file ```my_python_module.py``` and is in the current working directory.

Install the Python headers and library with ```apt install python3-dev```

Adjust the location of Python.h headers and libraries installed on your system.  It should be somewhere like ```/usr/include/python3.10```.  Also adjust the shared library name, again including the major and minor revision numbers in the Makefile.

Run the program: 
```./prog
Sent: 7 and 1
Result of call: 8
```

