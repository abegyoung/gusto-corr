#include <inttypes.h>
#include <sys/time.h>
#include <time.h>
#include <string.h>
#include "callback.h"
#include "corrspec.h"
#include <errno.h>
#include <curl/curl.h>
#include "influx.h"

#define PI 3.14159
#define BUFSIZE 128

void printDateTimeFromEpoch(time_t ts){

        struct tm *tm = gmtime(&ts);

        char buffer[26];
        strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", tm);
        printf("UTC Date and Time: %s\n", buffer);
}



// Callback function to process the file
// Function definition changes for FSWATCH or INOTIFY
#ifdef USE_FSWATCH

void const callback(const fsw_cevent *events,const unsigned int event_num, void *data){

   char *filename = events->path;

#endif

#ifdef USE_INOTIFY

void const callback(struct inotify_event *event, const char *directory){

   char filename[128];
   snprintf(filename, 128, "%s/%s", directory, event->name);

#endif

   // InfluxDB easy_curl objects
   CURL *curl;
   CURLcode res;
   char *query = malloc(BUFSIZ);
   char *query_list[] = {"_VIhi", "_VQhi", "_VIlo", "_VQlo"};

   //timing
   struct timeval begin, end;
   gettimeofday(&begin, 0);

   //correlator file objectsI
   int N;
   FILE *fp;
   FILE *fout;
   double P_I;
   double P_Q;
   struct corrType corr;

   uint64_t UNIXTIME;
   int NINT;
   int UNIT;
   int DEV;
   int NBYTES;
   int CPU;
   float dacV[4]; //0=VIhi, 1=VQhi, 2=VIlo, 3=VQlo
   float VIhi;
   float VQhi;
   float VIlo;
   float VQlo;

   int32_t *Rn;
   int32_t *Rn2;

   // notification
   printf("File changed: %s\n", filename);
   fp = fopen(filename, "r");

   // Find file type from filename
   // TODO: implement the UNKNOWN filetype and use tokens
   int i=0;
   char *ptr = NULL;
   char *prefix=malloc(6*sizeof(char));;
   const char *prefix_names[]={"SRC", "REF", "OTF", "HOT", "COLD", "FOC", "UNK"};
   while ( ptr==NULL ){
      ptr = strstr(filename, prefix_names[i]);
      i++;
   }
   int len = strlen(prefix_names[i-1]);
   strncpy(prefix, ptr, len);
   prefix[len] = '\0';
   printf("The type is %s\n", prefix);

   // Find scanID from filename
   // TODO: combine the file type and scanID from filename 
   int scanID;
   int dataN;
   char *token;
   int position = 0;

    // Use strtok to tokenize the filename using underscores as delimiters
    token = strtok(filename, "_");

    // Iterate through the tokens until reaching the 2nd position
    while (token != NULL ) {
        token = strtok(NULL, "_");

        if (position == 2 ) {      //get scanID
            scanID = atoi(token);
            printf("The scanID is: %d\n", scanID);
        }

        if (position == 3 ) {      //get scanID
            dataN = atoi(token);
            printf("The data file # is: %05d\n", dataN);
        }

        position++;
    }

   int32_t value;
   uint32_t value1;
   uint32_t value2;

   // figure out how many spectra in the file
   fseek(fp, 24, SEEK_SET);     // go to header position
   fread(&value, 4, 1, fp);
   int32_t bps = value;         // get bytes per spectra
   fseek(fp, 0L, SEEK_END);
   int sz = ftell(fp);          // get total bytes in file
   fseek(fp, 0L, SEEK_SET);     // go back to beginning of file
   printf("File has %.1f spectra\n", (float)sz/bps);

   int32_t header[22];
   const char *header_names[]={"UNIT", "DEV", "NINT", "UNIXTIME", "CPU", "NBYTES", "CORRTIME", "EMPTY", \
                "Ihigh", "Qhigh", "Ilow", "Qlow", "Ierr", "Qerr", \
                "EMPTY", "EMPTY","EMPTY","EMPTY","EMPTY","EMPTY","EMPTY","EMPTY"};

//////////////////////////////  LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////

   int j;

   for(j=0; j<(int)sz/bps; j++)
   {
      for(int i=0; i<22; i++){
         if(i==3){
            //UNIXTIME is 64 bits
            fread(&value1, 4, 1, fp); //Least significant 32 bits
            fread(&value2, 4, 1, fp); //Most significant 32 bis
            UNIXTIME = (((uint64_t)value2 << 32) | value1 ) / 1000.;

         }
         else{
            fread(&value, 4, 1, fp);
         }
         header[i] = (value);
      }

      // fill variables from header array
      UNIT          = header[0];
      DEV           = header[1];
      NINT          = header[2];
      //UNIXTIME      header[3]; 64 bits
      CPU           = header[4];
      NBYTES        = header[5];
      corr.corrtime = header[6];
      //EMPTY         header[7];
      corr.Ihi      = header[8];
      corr.Qhi      = header[9];
      corr.Ilo      = header[10];
      corr.Qlo      = header[11];

      // Initialize the Influx DB

      for (int k=0; k<4; k++){
         curl = init_influx();
         sprintf(query, "&q=SELECT * FROM \"ACS%d_DEV%d%s\" WHERE \"scanID\"='%d' ORDER BY time DESC LIMIT 1", \
                                  UNIT-1, DEV, query_list[k], scanID);

         dacV[k] = influxWorker(curl, query);
      }
      //free(query);

      VIhi = dacV[0];
      VQhi = dacV[1];
      VIlo = dacV[2];
      VQlo = dacV[3];
      printf("VIhi %.3f\tVQhi %.3f\tVIlo %.3f\tVQlo %.3f\n", VIhi, VQhi, VIlo, VQlo);

      // Build the spectra filename and put it in the spectra directory
      char filename[512] = "";

      sprintf(filename, "spectra/ACS%d_%s_%05d_DEV%d_NINT%03d.txt", UNIT-1, prefix, scanID, DEV, j);
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
         for(int i=0; i<(2*N)-1; i++){
            if(i%2 == 0) Rn[i] = corr.II[i/2] + corr.QQ[i/2];
            if(i%2 == 1) Rn[i] = corr.IQ[(i-1)/2] + corr.QI[1+(i-1)/2];
         }
         Rn[(2*N)-1] = corr.IQ[(N-1)/2] + corr.QI[(N-1)/2];
   
      // Mirror R[] symmetrically
         for(int i=0; i<4*N; i++){
           if(i<(2*N-1)) Rn2[i] = Rn[(2*N-1)-i];
           else Rn2[i] = Rn[i-(2*N-1)];
         }
   
      // Fill fft struct
         for(int i=0; i<4*N; i++){
           spec[specA].in[i][0] = Rn2[i]*0.5*(1-cos(2*PI*i/((4*N)-2)));     //real with Hann window
           spec[specA].in[i][1] = 0.;                                       //imag
         }
   
     // Do FFT and print
        fftw_execute(spec[specA].p);

        P_I = pow((VIhi-VIlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Ihi/(double)corr.corrtime)) + \
                                                (erfinv(1-2*(double)corr.Ilo/(double)corr.corrtime)),2);
        P_Q = pow((VQhi-VQlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Qhi/(double)corr.corrtime)) + \
                                                (erfinv(1-2*(double)corr.Qlo/(double)corr.corrtime)),2);
   
      //Print in counts per second (assuming 5000 MHz sampling freq)
      for(int i=0; i<2*N; i++){
         fprintf(fout, "%d\t%lf\n", (5000*i)/(2*N), \
                                      (5000.*1000000.)/(corr.corrtime*256.)*sqrt(P_I*P_Q)* \
                                      sqrt(fabs(spec[specA].out[i][0]*(-1*spec[specA].out[i][1]))) );
      }
   
   
      fclose(fout); //close single spectra file
      free(corr.QI);
      free(corr.II);
      free(corr.QQ);
      free(corr.IQ);
      free(Rn);
      free(Rn2);
   }


//////////////////////////////  LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////
   
      fclose(fp);   //close input file
		    
      //ouput stats for last spectra in file
      printf("\nUNIXTIME is %" PRIu64 "\n", UNIXTIME);
      printf("CORRTIME is %.6f\n", (corr.corrtime*256.)/(5000.*1000000.));
      printDateTimeFromEpoch((long long) UNIXTIME);
      printf("UNIT is %d\n", UNIT);
      printf("DEV  is %d\n",   DEV); 
      printf("NINT is %d\n", NINT);
      printf("%.2f %.2f %.2f %.2f\n",  (double)corr.Qhi/(double)corr.corrtime, \
                                       (double)corr.Ihi/(double)corr.corrtime, \
                                       (double)corr.Qlo/(double)corr.corrtime, \
                                       (double)corr.Ilo/(double)corr.corrtime);
      printf("nlags=%d\n", N);
      printf("etaQ %.3f\n", 1/sqrt(P_I*P_Q));

      //timing
      gettimeofday(&end, 0);
      int seconds = end.tv_sec - begin.tv_sec;
      int microseconds = end.tv_usec - begin.tv_usec;
      double elapsed = seconds + microseconds*1e-6;
      printf("AVG FFTW %.1f ms in %d spectra\n\n", 1000.*elapsed/(sz/bps), sz/bps);
      fflush(stdout);
   
}



