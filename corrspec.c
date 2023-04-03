#include <math.h>
#include <sys/time.h>
#include <it/math.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <fftw3.h>
#include <arpa/inet.h>
#include <ctype.h>
#include <string.h>
#include "dict.h"
#include <libfswatch/c/libfswatch.h>

#define MAX_STR_LEN 32
#define PI 3.14159

struct Spectrum
{
   fftw_complex *in, *out;
   fftw_plan p;
};
struct Spectrum spec[4];

int i,N;
FILE *fin;
FILE *fout;
char *key;
char *value;
double P_I;
double P_Q;

struct corrType
{
   uint32_t corrtime;      //32 bit length of accumulation
   uint32_t Qhi;           //32 bit Qhi monitor
   uint32_t Ihi;           //32 bit Ihi monitor
   uint32_t Qlo;           //32 bit Qlo monitor
   uint32_t Ilo;           //32 bit Ilo monitor
   int32_t *QI;            //32 bit QI lag values
   int32_t *II;            //32 bit II lag values
   int32_t *QQ;            //32 bit QR lag values
   int32_t *IQ;            //32 bit IQ lag values
};

struct corrType corr;

void makeSpec(fsw_cevent const * const events,
         const unsigned int event_num,
         void * data)
{

  //timing
  struct timeval begin, hashdone, end;
  gettimeofday(&begin, 0);

   int NBYTES;

   float VQhi;
   float VIhi;
   float VQlo;
   float VIlo;

   int32_t *Rn;
   int32_t *Rn2;

   // read 27 lines of key value header
   HashTable *ht = create_table(CAPACITY);

   key = malloc(MAX_STR_LEN);
   value = malloc(MAX_STR_LEN);

   usleep(10000);
   fin = fopen("out.lags", "r");
   for(i=0; i<27; i++){
     fscanf(fin, "%s %s\n", key, value);
     ht_insert(ht, key, value);
   }

   // fill variables from hash table
   corr.corrtime = atoi(ht_search(ht, (char *) "CORRTIME"));
   NBYTES   = atoi(ht_search(ht, (char *) "NBYTES"));
   corr.Qhi = atoi(ht_search(ht, (char *) "Qhigh" ));
   corr.Ihi = atoi(ht_search(ht, (char *) "Ihigh" ));
   corr.Qlo = atoi(ht_search(ht, (char *) "Qlow"  ));
   corr.Ilo = atoi(ht_search(ht, (char *) "Ilow"  ));
   VQhi     = atof(ht_search(ht, (char *) "VQhi"  ));
   VIhi     = atof(ht_search(ht, (char *) "VIhi"  ));
   VQlo     = atof(ht_search(ht, (char *) "VQlo"  ));
   VIlo     = atof(ht_search(ht, (char *) "VIlo"  ));

   //timing
   gettimeofday(&hashdone, 0);

   usleep(1000);

   fout = fopen("out.spec", "w");

   //read human readable "Number of Lags"
   if (NBYTES==8256)
     N = 512;
   else if (NBYTES==6208)
     N = 384;
   else if (NBYTES==4160)
     N = 256;
   else if (NBYTES==2112)
     N = 128;
   printf("nlags=%d\n", N);
   int specA = (int) N/128 - 1;

   //First byte is Correlator STATUS
   corr.QI  = malloc(N*sizeof(int32_t));
   corr.II  = malloc(N*sizeof(int32_t));
   corr.QQ  = malloc(N*sizeof(int32_t));
   corr.IQ  = malloc(N*sizeof(int32_t));
   Rn  = malloc(2*N*sizeof(int32_t));
   Rn2 = malloc(4*N*sizeof(int32_t));

   // Read lags
   for(i  =0; i<N; i+=1){
     fscanf(fin, "%d %d %d %d\n", &corr.II[i], &corr.IQ[i], &corr.QI[i], &corr.QQ[i]);
   }
   fclose(fin);            

// Combine IQ lags into R[]
   for(i=0; i<(2*N); i++){
      if(i%2 == 0) Rn[i] = corr.II[i/2] + corr.QQ[i/2];
      if(i%2 == 1) Rn[i] = corr.IQ[(i-1)/2] + corr.QI[1+(i-1)/2];
   }
   Rn[2*N] = corr.IQ[(N-1)/2] + corr.QI[(N-1)/2];

// Mirror R[] symmetrically
   for(i=0; i<4*N; i++){
     if(i<(2*N-1)) Rn2[i] = Rn[(2*N-1)-i];
     else Rn2[i] = Rn[i-(2*N-1)];
   }

// Fill fft struct
   for(i=0; i<4*N-1; i++){
     spec[specA].in[i][0] = Rn2[i]*0.5*(1-cos(2*PI*i/((4*N)-2)));	//real with Hann window
     spec[specA] .in[i][1] = 0.;					//imag
   }

// Do FFT and print
   fftw_execute(spec[specA].p);

   P_I = pow((VIhi-VIlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Ihi/(double)corr.corrtime)) + (erfinv(1-2*(double)corr.Ilo/(double)corr.corrtime)),2);
   P_Q = pow((VQhi-VQlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Qhi/(double)corr.corrtime)) + (erfinv(1-2*(double)corr.Qlo/(double)corr.corrtime)),2);

   printf("etaQ %.3f\n", 1/sqrt(P_I*P_Q));

   //Print in counts per second (assuming 4700
   for(i=0; i<2*N; i++)
     fprintf(fout, "%d\t%lf\n", (4500*i)/(2*N), (4500.*1000000.)/(corr.corrtime*256.)*sqrt(P_I*P_Q)*sqrt(fabs(spec[specA].out[i][0]*(-1*spec[specA].out[i][1]))) );

// Cleanup

   free_table(ht);
   fclose(fout);
   free(key);
   free(value);

   gettimeofday(&end, 0);
   long seconds = hashdone.tv_sec - begin.tv_sec;
   long microseconds = hashdone.tv_usec - begin.tv_usec;
   double elapsed = seconds + microseconds*1e-6;
   printf("Hash table %.3f\n", elapsed);

   seconds = end.tv_sec - hashdone.tv_sec;
   microseconds = end.tv_usec - hashdone.tv_usec;
   elapsed = seconds + microseconds*1e-6;
   printf("FFTW %.3f\n\n", elapsed);

}

int main(int argc, char **argv){
  void* data;

// Setup possible FFTW array lengths
   for(i=0; i<4; i++){
     N=(i+1)*128;
     spec[i].in  = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].out = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].p = fftw_plan_dft_1d((4*N-1), spec[i].in, spec[i].out, FFTW_FORWARD, FFTW_PATIENT);
   }
   fftw_import_system_wisdom();


   /* Initialize fswatch */
   fsw_init_library();
   const FSW_HANDLE handle = fsw_init_session(fsevents_monitor_type);
   fsw_add_path(handle, "./out.lags");
   fsw_set_callback(handle, makeSpec, data);

   while(1){

     fsw_start_monitor(handle);

   }

   fftw_destroy_plan(spec[i].p);
   fftw_free(spec[i].in);
   fftw_free(spec[i].out);


}

