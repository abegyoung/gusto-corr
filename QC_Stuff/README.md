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

#Tutorial 2


