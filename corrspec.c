// main.c
#include <unistd.h>
#include <sys/time.h>
#include <time.h>
#include <stdio.h>
#include <inttypes.h>
#include <stdlib.h>
#include <math.h>
#include <it/math.h>
#include <fftw3.h>
#include <inttypes.h>
#include <string.h>
#include <arpa/inet.h>
#include "corrspec.h"

#define PI 3.14159

int flag = 1<<2;
struct fsw_event_type_filter cevent_filter;

void printDateTimeFromEpoch(long long epochSeconds){
	time_t epochTime = (time_t)(&epochSeconds);
	struct tm *timeInfo = gmtime(&epochTime);

	char buffer[26];
	strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", timeInfo);
	printf("UTC Date and Time: %s\n", buffer);
}


// Make 4 structs for 128,256,384,512 FFT array lengths
struct Spectrum
{
   fftw_complex *in, *out;
   fftw_plan p;
};
struct Spectrum spec[4];

// structure to hold lag data
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


// Callback function to process the file
#ifdef USE_FSWATCH
   void const callback(const fsw_cevent *events,const unsigned int event_num, void *data){
#endif
#ifdef USE_INOTIFY
   void const callback(struct inotify_event *event, const char *directory){
#endif

   //timing
   struct timeval begin, end;
   gettimeofday(&begin, 0);

   int N;
   FILE *fp;
   FILE *fout;
   double P_I;
   double P_Q;

   uint64_t UNIXTIME;
   int NINT;
   int UNIT;
   int DEV;
   int NBYTES;
   float VQhi;
   float VIhi;
   float VQlo;
   float VIlo;

   int32_t *Rn;
   int32_t *Rn2;

#ifdef USE_FSWATCH
   const char *filename = events->path;
#endif
#ifdef USE_INOTIFY
   char filename[128];
   snprintf(filename, 128, "%s/%s", directory, event->name);
#endif
   printf("File changed: %s\n", filename);
   fp = fopen(filename, "r");


   int i=0;
   char *ptr= NULL;
   char *prefix;
   const char *prefix_names[]={"SRC", "REF", "OTF", "HOT", "COLD", "FOC"};
   while ( ptr==NULL ){
      ptr= strstr(filename, prefix_names[i]);
      i++;
   }
   int len = strlen(prefix_names[i-1]);
   strncpy(prefix, ptr, len);
   prefix[len] = '\0';
   printf("type is %s\n", prefix);


   int32_t value;
   uint64_t value64;

   // figure out how many spectra in the file
   fseek(fp, 24, SEEK_SET);     // go to header position
   fread(&value, 4, 1, fp);
   int32_t bps = value;         // get bytes per spectra
   fseek(fp, 0L, SEEK_END);
   int sz = ftell(fp);          // get total bytes in file
   fseek(fp, 0L, SEEK_SET);     // go back to beginning of file
   printf("File has %d spectra\n", sz/bps);

   int32_t header[22];
   const char *header_names[]={"UNIT", "DEV", "NINT", "UNIXTIME", "CPU", "NBYTES", "CORRTIME", "EMPTY", \
                "Ihigh", "Qhigh", "Ilow", "Qlow", "Ierr", "Qerr", \
                "EMPTY", "EMPTY","EMPTY","EMPTY","EMPTY","EMPTY","EMPTY","EMPTY"};


//////////////////////////////  LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////

   //for(int j=0; j<sz/bps; j++)
   for(int j=0; j<1; j++)
   {
      for(int i=0; i<22; i++){
         if(i==3){
            fread(&value64, 4, 2, fp); //UNIXTIME is 64 bits
            UNIXTIME = htonl(value64);
         }
         else{
            fread(&value, 4, 1, fp);
         }
         header[i] = (value);
      }

      // fill variables from header array
      UNIT     = header[0];
      DEV      = header[1];
      NINT     = header[2];
      NBYTES   = header[5];
      corr.corrtime = header[6];
      corr.Ihi = header[8];
      corr.Qhi = header[9];
      corr.Ilo = header[10];
      corr.Qlo = header[11];
      FILE *calf=fopen("cal.txt", "r");
      fscanf(calf, "%*s %*s %f\n", &VIhi);
      fscanf(calf, "%*s %*s %f\n", &VQhi);
      fscanf(calf, "%*s %*s %f\n", &VIlo);
      fscanf(calf, "%*s %*s %f\n", &VQlo);

      char filename[255];

      sprintf(filename, "%s_UNIT%d_DEV%d_NINT%d.txt", prefix, header[0], header[1], header[2]);
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
      corr.QI  = malloc(N*sizeof(int32_t)+1);
      corr.II  = malloc(N*sizeof(int32_t)+1);
      corr.QQ  = malloc(N*sizeof(int32_t)+1);
      corr.IQ  = malloc(N*sizeof(int32_t)+1);
      Rn  = malloc(2*N*sizeof(int32_t)+1);
      Rn2 = malloc(4*N*sizeof(int32_t)+1);

      // Read lags
      for(int i=0; i<N; i++){
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
        for(int i=0; i<(2*N); i++){
           if(i%2 == 0) Rn[i] = corr.II[i/2] + corr.QQ[i/2];
           if(i%2 == 1) Rn[i] = corr.IQ[(i-1)/2] + corr.QI[1+(i-1)/2];
        }
        Rn[2*N] = corr.IQ[(N-1)/2] + corr.QI[(N-1)/2];
   
     // Mirror R[] symmetrically
        for(int i=0; i<4*N; i++){
          if(i<(2*N-1)) Rn2[i] = Rn[(2*N-1)-i];
          else Rn2[i] = Rn[i-(2*N-1)];
        }
   
     // Fill fft struct
        for(int i=0; i<4*N-1; i++){
          spec[specA].in[i][0] = Rn2[i]*0.5*(1-cos(2*PI*i/((4*N)-2)));     //real with Hann window
          spec[specA].in[i][1] = 0.;                                       //imag
        }
   
     // Do FFT and print
        fftw_execute(spec[specA].p);

        P_I = pow((VIhi-VIlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Ihi/(double)corr.corrtime)) + \
                                                (erfinv(1-2*(double)corr.Ilo/(double)corr.corrtime)),2);
        P_Q = pow((VQhi-VQlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Qhi/(double)corr.corrtime)) + \
                                                (erfinv(1-2*(double)corr.Qlo/(double)corr.corrtime)),2);
   
      //Print in counts per second (assuming 4700
      for(int i=0; i<2*N; i++){
         fprintf(fout, "%d\t%lf\n", (5000*i)/(2*N), \
                                      (5000.*1000000.)/(corr.corrtime*256.)*sqrt(P_I*P_Q)* \
                                      sqrt(fabs(spec[specA].out[i][0]*(-1*spec[specA].out[i][1]))) );
      }
   
   
      fclose(fout); //close single spectra file
   }


//////////////////////////////  LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////
   
      fclose(fp);   //close input file
		    
      //ouput stats for last spectra in file
      printf("\nUNIXTIME is %" PRIu64 "\n", UNIXTIME);
      printf("CORRTIME is %d\n", (5000.*1000000.)/(corr.corrtime*256.));
      printDateTimeFromEpoch(UNIXTIME/1000.);
      printf("UNIT is %lu\n", header[0]);
      printf("DEV is %lu\n", header[1]);
      printf("NINT is %lu\n", header[2]);
      printf("%.2f %.2f %.2f %.2f\n",  (double)corr.Qhi/(double)corr.corrtime, \
                                       (double)corr.Ihi/(double)corr.corrtime, \
                                       (double)corr.Qlo/(double)corr.corrtime, \
                                       (double)corr.Ilo/(double)corr.corrtime);
      printf("nlags=%lu\n", N);
      printf("etaQ %.3f\n", 1/sqrt(P_I*P_Q));

      //timing
      gettimeofday(&end, 0);
      int seconds = end.tv_sec - begin.tv_sec;
      int microseconds = end.tv_usec - begin.tv_usec;
      double elapsed = seconds + microseconds*1e-6;
      printf("AVG FFTW %.1f ms in %d spectra\n\n", 1000.*elapsed/(sz/bps), sz/bps);
   
}


int main(int argc, char **argv) {
   
   void *data;
#ifdef USE_INOTIFY
   char buffer[EVENT_BUF_LEN];
#endif

   // Set the directory to monitor
   const char *directory = argv[1];

   printf("readying fft\n");

   // Setup all possible FFTW array lengths
   for(int i=0; i<4; i++){
     int N=(i+1)*128;
     spec[i].in  = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].out = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].p = fftw_plan_dft_1d((4*N-1), spec[i].in, spec[i].out, FFTW_FORWARD, FFTW_PATIENT|FFTW_PRESERVE_INPUT);
   }
   fftw_import_system_wisdom();

   printf("ready to start\n");

   /* Initialize fswatch or inotify */
#ifdef USE_FSWATCH
   // Initialize the session
   fsw_init_library();

   FSW_HANDLE fsw_handle = fsw_init_session(fsevents_monitor_type);  //MacOSX
   //FSW_HANDLE fsw_handle = fsw_init_session(inotify_monitor_type);     //Linux
   //FSW_HANDLE fsw_handle = fsw_init_session(kqueue_monitor_type);    //BSD

   // Set the callback function
   fsw_set_callback(fsw_handle, callback, data);

   // Add event types
   cevent_filter.flag= flag;
   fsw_add_event_type_filter(fsw_handle, cevent_filter);

   // Add a watch to the directory
   if (fsw_add_path(fsw_handle, directory) < 0) {
      perror("Error adding path");
      exit(EXIT_FAILURE);
   }

   // Start the event loop
   if (fsw_start_monitor(fsw_handle) < 0) {
      perror("Error starting monitor");
      exit(EXIT_FAILURE);
   }

   // Clean up
   fsw_destroy_session(fsw_handle);
#endif
#ifdef USE_INOTIFY
   int fd = inotify_init();
   int wd = inotify_add_watch(fd, directory, IN_CLOSE_WRITE);

   while(1){
      int length = read(fd, buffer, EVENT_BUF_LEN);
      struct inotify_event *event = (struct inotify_event *) &buffer;
      callback(event, directory);
   }
#endif

   for(int i=0; i<4; i++){
     fftw_destroy_plan(spec[i].p);
     fftw_free(spec[i].in);
     fftw_free(spec[i].out);
   }

   return 0;
}

