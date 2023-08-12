#include <dirent.h>
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
#include <sys/types.h>
#include "corrspec.h"

#define MAX_STR_LEN 32
#define PI 3.14159

// Make 4 structs for 128,256,384,512 FFT array lengths
struct Spectrum
{
   fftw_complex *in, *out;
   fftw_plan p;
};
struct Spectrum spec[4];

int i,N;
FILE *fp;
FILE *fout;
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

#ifdef USE_FSWATCH
   void makeSpec(fsw_cevent const * const events,
         const unsigned int event_num,
         void * data)
#endif
#ifdef USE_INOTIFY
   makespec()
#endif
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

   //Open file and read header
   char str1[5];
   char str2[5];
   char last[80];
   char file_in_name[80];
   DIR *dp;
   struct dirent *ep;
   dp = opendir("/mnt/data/ACS3");
   if (dp != NULL) {
     while ((ep = readdir (dp)) != NULL){
       sprintf(last, "%s", ep->d_name);
       puts(ep->d_name);
     }

     closedir(dp);
   }
   else
   {
     perror("Couldn't open directory");
   }
   sprintf(file_in_name, "/mnt/data/ACS3/default_");
   strncpy(str1, last+8, 8);
   int num=atoi(str1);
   snprintf(str2, sizeof(str2), "%04d", num-1);

   strcat(file_in_name, str2);
   strcat(file_in_name, ".dat");

printf("opening %s\n", file_in_name);
    
   //Open file and read header
   fp = fopen(file_in_name, "r");
   int32_t value;
   int32_t header[21];
   const char *header_names[]={"UNIT", "DEV", "NINT", "UNIXTIME", "CPU", "NBYTES", "CORRTIME", "EMPTY", \
                "Ihigh", "Qhigh", "Ilow", "Qlow", "Ierr", "Qerr", \
                "EMPTY", "EMPTY","EMPTY","EMPTY","EMPTY","EMPTY","EMPTY","EMPTY"};

   for(int j=0; j<100; j++){

     for(int i=0; i<22; i++){
       if(i==3)
         fread(&value, 4, 2, fp); //UNIXTIME if 64 bits
       else
         fread(&value, 4, 1, fp);
  
       header[i] = (value);
       //printf("%s is %lu\n", header_names[i], header[i]);
     }
  
     // fill variables from header array
     NBYTES        = header[5];
     corr.corrtime = header[6];
     corr.Ihi = header[8];
     corr.Qhi = header[9];
     corr.Ilo = header[10];
     corr.Qlo = header[11];
     VQhi     = 2.0;
     VIhi     = 2.0;
     VQlo     = 1.0;
     VIlo     = 1.0;

     //timing
     gettimeofday(&hashdone, 0);

     //usleep(1000);

     char filename[80];
     sprintf(filename, "spectra_files/spec_UNIT%d_DEV%d_NINT%d.dat", header[0], header[1], header[2]);
     fout = fopen(filename, "w");

     //read human readable "Number of Lags"
     if (NBYTES==8256)
       N = 512;
     else if (NBYTES==6208)
       N = 384;
     else if (NBYTES==4160)
       N = 256;
     else if (NBYTES==2112)
       N = 128;
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
       fread(&value, 4, 1, fp);
       corr.II[i] = (value);
       fread(&value, 4, 1, fp);
       corr.IQ[i] = (value);
       fread(&value, 4, 1, fp);
       corr.QI[i] = (value);
       fread(&value, 4, 1, fp);
       corr.QQ[i] = (value);
     }

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


     //Print in counts per second (assuming 4700
     for(i=0; i<2*N; i++)
       fprintf(fout, "%d\t%lf\n", (4500*i)/(2*N), (4500.*1000000.)/(corr.corrtime*256.)*sqrt(P_I*P_Q)*sqrt(fabs(spec[specA].out[i][0]*(-1*spec[specA].out[i][1]))) );

     fclose(fout); //close single spectra file

   }

   fclose(fp);     //close ACS spectrometer lag file       

// Cleanup
   //DEBUG
   printf("UNIXTIME is %lu\n", 0);
   printf("UNIT is %lu\n", header[0]);
   printf("DEV is %lu\n", header[1]);
   printf("%.2f %.2f %.2f %.2f\n", (double)corr.Qhi/(double)corr.corrtime, (double)corr.Ihi/(double)corr.corrtime, (double)corr.Qlo/(double)corr.corrtime, (double)corr.Ilo/(double)corr.corrtime);
   printf("nlags=%lu\n", N);
   printf("etaQ %.3f\n", 1/sqrt(P_I*P_Q));


   
   gettimeofday(&end, 0);
   long seconds = hashdone.tv_sec - begin.tv_sec;
   long microseconds = hashdone.tv_usec - begin.tv_usec;
   double elapsed = seconds + microseconds*1e-6;
   printf("Hash table %.1f ms\n", 1000.*elapsed);

   seconds = end.tv_sec - hashdone.tv_sec;
   microseconds = end.tv_usec - hashdone.tv_usec;
   elapsed = seconds + microseconds*1e-6;
   printf("FFTW %.1f ms\n\n", 1000.*elapsed);

}

int main(int argc, char **argv){
  void* data;

  int fd;
  int wd;
  int length;
#ifdef USE_INOTIFY
  char buffer[EVENT_BUF_LEN];
#endif

// Setup all possible FFTW array lengths
   for(i=0; i<4; i++){
     N=(i+1)*128;
     spec[i].in  = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].out = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].p = fftw_plan_dft_1d((4*N-1), spec[i].in, spec[i].out, FFTW_FORWARD, FFTW_PATIENT);
   }
   fftw_import_system_wisdom();


   /* Initialize fswatch or inotify */
#ifdef USE_FSWATCH
   fsw_init_library();
   //const FSW_HANDLE handle = fsw_init_session(fsevents_monitor_type); //MacOSX
   //const FSW_HANDLE handle = fsw_init_session(inotify_monitor_type);  //Linux
   const FSW_HANDLE handle = fsw_init_session(kqueue_monitor_type);     //BSD
   fsw_add_path(handle, "/mnt/data/ACS3");
   fsw_set_callback(handle, makeSpec, data);
#endif
#ifdef USE_INOTIFY
   fd = inotify_init();
   wd = inotify_add_watch(fd, "/mnt/data/ACS3", IN_CLOSE_WRITE);
#endif

   while(1){

#ifdef USE_FSWATCH
     fsw_start_monitor(handle);
#endif
#ifdef USE_INOTIFY
     length = read(fd, buffer, EVENT_BUF_LEN);
     makeSpec();
#endif

   }

   for(i=0; i<4; i++){
     fftw_destroy_plan(spec[i].p);
     fftw_free(spec[i].in);
     fftw_free(spec[i].out);
   }

}

