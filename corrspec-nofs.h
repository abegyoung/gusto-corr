#include <math.h>
#include <it/math.h>
#include <fftw3.h>


// Make 4 structs for 128,256,384,512 FFT array lengths
struct Spectrum
{
   fftw_complex *in, *out;
   fftw_plan p;
};

extern struct Spectrum spec[4];

