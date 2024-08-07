#include <inttypes.h>
#include <sys/time.h>
#include <time.h>
#include <string.h>
#include "callback.h"
#include "corrspec.h"
#include <errno.h>
#include <curl/curl.h>
#include "influx.h"

#include <Python.h>

#include <stdio.h>
#include <stdbool.h>
#include <fitsio.h>

#define PI 3.14159
#define BUFSIZE 256
#define DEBUG 0
#define DOQC 1


// Function to perform circular shift by -1  [UNUSED]
// functionally identical to the even/odd IQ[i+1] scheme
// when IQ[last] is set zero via Hann window
void circularShiftLeft(float arr[], int size) {
    if (size <= 1) return; // No shift needed for arrays of size 0 or 1

    float firstElement = arr[0]; // Store the first element

    // Shift all elements one position to the left
    for (int i = 0; i < size - 1; i++) {
        arr[i] = arr[i + 1];
    }

    // Place the first element at the end of the array
    arr[size - 1] = firstElement;
}


void get_git_commit_info(const char *filename, char *commit_info) {
    char command[BUFSIZ];
    FILE *fp;
    char hash[BUFSIZ], date[BUFSIZ];

    // Construct the command to get the commit hash
    snprintf(command, sizeof(command), "git log -1 --format=%%cd --date=format-local:'%%Y-%%m-%%d %%H:%%M:%%S %%Z' --pretty=format:\"Last commit %%h by %%an %%ad\" -- %s", filename);
    fp = popen(command, "r");
    if (fp == NULL) {
        perror("popen");
        exit(EXIT_FAILURE);
    }
    fgets(hash, sizeof(hash), fp);
    pclose(fp);
    hash[strcspn(hash, "\n")] = 0; // Remove trailing newline

    // Combine hash and date into the commit_info string
    snprintf(commit_info, BUFSIZ+sizeof(filename), "%s %s", filename, hash);
}


void append_to_fits_table(const char *filename, struct s_header *fits_header, double *array, int THOTID) {
    fitsfile *fptr;  // FITS file pointer
    int status = 0;  // CFITSIO status value MUST be initialized to zero!
    int hdutype;
    int array_length;
    long nrows;
    char extname[] = "DATA_TABLE";
    long n_elements = sizeof(array) / sizeof(array[0]);

    CURL *curl;
    char *query = malloc(BUFSIZ);
    char *buf;

    char commit_info[256];

    float crpix = 0.;
    float crval = 0.;
    float cdelt;

    // Try to open the FITS file in read/write mode. If it doesn't exist, create a new one.
    if (fits_open_file(&fptr, filename, READWRITE, &status)) {
        if (status == FILE_NOT_OPENED) {
            status = 0;  // Reset the status
            if (fits_create_file(&fptr, filename, &status)) {
                fits_report_error(stderr, status);  // Print any error message
                return;
            }

            // Create a primary array image (needed before any extensions can be created)
            if (fits_create_img(fptr, BYTE_IMG, 0, NULL, &status)) {
                fits_report_error(stderr, status);  // Print any error message
                return;
            }

            // Construct the primary FITS HEADER

	    // Create some Primary header keyword value pairs and fill them from the current fits_header struct
	    fits_write_key(fptr, TSTRING,   "OBJECT",   fits_header->target, "Name of the target object", &status);
            fits_write_key(fptr, TSTRING,   "scantype", fits_header->type,   "Type of scan", &status);
            fits_write_key(fptr, TINT,      "scanID",  &fits_header->scanID, "ID of scan", &status);
            fits_write_key(fptr, TINT,      "CALID",   &fits_header->CALID,  "ID of correlator calibration", &status);
            fits_write_key(fptr, TINT,      "IF",      &fits_header->IF,     "Frequency (MHz) of VLSR", &status);
            fits_write_key(fptr, TFLOAT,    "LO",      &fits_header->LO,     "Synth (MHz)", &status);
            fits_write_key(fptr, TFLOAT,    "VLSR",    &fits_header->VLSR,   "VLSR (km/s)", &status);

	    // Spectral scaling
            if(fits_header->unit==6){ //ACS5 B1
	       cdelt = 5000./512.;
	    }
            if(fits_header->unit==4){ //ACS3 B2
	       cdelt = 5000./1024.;
	    }
            fits_write_key(fptr, TSTRING,   "CUNIT1",  "MHz",  "Spectral unit",    &status);
            fits_write_key(fptr, TFLOAT,    "CRPIX1",  &crpix,  "Index location", &status);
            fits_write_key(fptr, TFLOAT,    "CRVAL1",  &crval,  "Start of spectra (MHz)", &status);
            fits_write_key(fptr, TFLOAT,    "CDELT1",  &cdelt,  "Channel width (MHz)", &status);


	    // We only want to fill the primary header once, so don't bother with the fits_header struct, 
	    // which is per extension table row, just get directly from influx now
	    // Note: This is a pretty high overhead task talking to the InfluxDB, but we only need to do it once per file
            fits_write_key(fptr, TINT,    "HKscanID",    &THOTID,   "Last H/K measurement", &status);

	    // Ambient HK_TEMP           0          1          2          3          4          5          6          7          
            const char *hktemp_names[]={"CRADLE02","CRYCSEBK","CRYOPORT","CALMOTOR","CRADLE03","QAVCCTRL","COOLRTRN","FERADIAT", \
		                        "CRYCSEFT","CRADLE04","CONELOAD","OAVCCTRL","COOLSUPL","CRADLE01","EQUILREF","SECONDRY"};
	                              // 8          9          10         11         12         13         14         15
	    curl = init_influx();
            sprintf(query, "&q=SELECT * FROM /^HK_TEMP*/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
            influxReturn = influxWorker(curl, query);
	    for(int i=0; i<influxReturn->length; i++)
               fits_write_key(fptr, TFLOAT, hktemp_names[i], &influxReturn->value[i], "Ambient temps (C)", &status);
            freeinfluxStruct(influxReturn);

	    
	    // LO AD590                  0          1          10         11         2          3          
            const char *b1temp_names[]={"UNUSED  ","B1_MLSE ","B1POWER3","B1POWER4","UNUSED  ","UNUSED  ", \
		                        "B1CH5SPK","UNUSED  ","UNUSED  ","UNUSED  ","B1POWER1","B1POWER2"};
            const char *b2temp_names[]={"B2INTRN1","B2INTRN2","B2POWER3","B2POWER4","UNUNSED ","UNUSED  ", \
		                        "UNUSED  ","B2AVA183","B1CH5MLT","B2CH5SPK","B2POWER1","B2POWER2"};
                                      // 4          5          6          7          8          9 
	    curl = init_influx();
            sprintf(query, "&q=SELECT * FROM /^B1_AD590*/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
            influxReturn = influxWorker(curl, query);
	    for(int i=0; i<influxReturn->length; i++)
               fits_write_key(fptr, TFLOAT, b1temp_names[i], &influxReturn->value[i], "LO Ambient temps (C)", &status);
            freeinfluxStruct(influxReturn);

	    curl = init_influx();
            sprintf(query, "&q=SELECT * FROM /^B2_AD590*/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
            influxReturn = influxWorker(curl, query);
	    for(int i=0; i<influxReturn->length; i++)
               fits_write_key(fptr, TFLOAT, b2temp_names[i], &influxReturn->value[i], "LO Ambient temps (C)", &status);
            freeinfluxStruct(influxReturn);

	    
	    // LO Drive currents
	    curl = init_influx();
            const char *b1psat_names[]={"PSATB1M2", "PSATB1M3", "PSATB1M6"};
            const char *b2psat_names[]={"PSATB2M2", "PSATB2M5", "PSATB2M8"};
            if(fits_header->unit==6){ //ACS5 B1
               sprintf(query, "&q=SELECT * FROM /^PSatI_B1M2|PSatI_B1M3|PSatI_B1M6/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
               influxReturn = influxWorker(curl, query);
	       for(int i=0; i<influxReturn->length; i++)
                  fits_write_key(fptr, TFLOAT, b1psat_names[i], &influxReturn->value[i], "LO Drive Currents (Amps)", &status);
	    }
            if(fits_header->unit==4){ //ACS3 B2
               sprintf(query, "&q=SELECT * FROM /^PSatI_B2M2|PSatI_B2M5|PSatI_B2M8/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
               influxReturn = influxWorker(curl, query);
	       for(int i=0; i<influxReturn->length; i++)
                  fits_write_key(fptr, TFLOAT, b2psat_names[i], &influxReturn->value[i], "LO Drive Currents (Amps)", &status);
	    }
            freeinfluxStruct(influxReturn);

	    // HEB Mixer Currents
	    curl = init_influx();
            const char *b1Imon_names[]={"IMONB1M2","IMONB1M3","IMONB1M6"};
            const char *b2Imon_names[]={"IMONB2M2","IMONB2M5","IMONB2M8"};
            if(fits_header->unit==6){ //ACS5 B1
               sprintf(query, "&q=SELECT * FROM /^biasCurB1M2|biasCurB1M3|biasCurB1M6/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
               influxReturn = influxWorker(curl, query);
	       for(int i=0; i<influxReturn->length; i++)
                  fits_write_key(fptr, TFLOAT, b1Imon_names[i], &influxReturn->value[i], "Mixer Currents (mA)", &status);
	    }
            if(fits_header->unit==4){ //ACS3 B2
               sprintf(query, "&q=SELECT * FROM /^biasCurB2M2|biasCurB2M5|biasCurB2M8/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
               influxReturn = influxWorker(curl, query);
	       for(int i=0; i<influxReturn->length; i++)
                  fits_write_key(fptr, TFLOAT, b2Imon_names[i], &influxReturn->value[i], "Mixer Currents (mA)", &status);
	    }
            freeinfluxStruct(influxReturn);

	    // LO Gate Monitor
	    curl = init_influx();
            const char *gate_names[]={"GATEMON1","GATEMON2","GATEMON3","GATEMON4","GATEMON5","GATEMON6","GATEMON7","GATEMON8"};
            if(fits_header->unit==6) //ACS5 B1
               sprintf(query, "&q=SELECT * FROM /^B1_GMON_*/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
            if(fits_header->unit==4) //ACS3 B2
               sprintf(query, "&q=SELECT * FROM /^B2_GMON_*/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
            influxReturn = influxWorker(curl, query);
	    for(int i=0; i<influxReturn->length; i++)
               fits_write_key(fptr, TFLOAT, gate_names[i], &influxReturn->value[i], "LO Gate Monitor (Amps)", &status);
            freeinfluxStruct(influxReturn);

	    // Cryogenic temps
	    curl = init_influx();
            const char *cryo_names[]={"IS", "IVCS", "LNA", "MIXER","OS", "OVCS", "QCL", "TANK"};
            sprintf(query, "&q=SELECT * FROM /^DT670*/ WHERE scanID=~/%d/ LIMIT 1", THOTID);
            influxReturn = influxWorker(curl, query);
	    for(int i=0; i<influxReturn->length; i++)
               fits_write_key(fptr, TFLOAT, cryo_names[i], &influxReturn->value[i], "Cryogenic temps (K)", &status);
            freeinfluxStruct(influxReturn);

	    // Create some Primary header comments and fill them
	    get_git_commit_info("The Corrspec GUSTO pipeline is customizable combining raw spectrometer files and flight \
			         houskeeping database into minimal header level0.5 baseband spectra or level0.7 full H/K\
				 fits files. see github.com/abegyoung/gusto-corr for documentation", commit_info);
	    if (fits_write_comment(fptr, commit_info, &status)) {
	        fits_report_error(stderr, status);
		return;
	    }
	    get_git_commit_info("corrspec.c", commit_info);
	    if (fits_write_comment(fptr, commit_info, &status)) {
	        fits_report_error(stderr, status);
		return;
	    }
	    get_git_commit_info("callback.c", commit_info);
	    if (fits_write_comment(fptr, commit_info, &status)) {
	        fits_report_error(stderr, status);
		return;
	    }
	    get_git_commit_info("influx.c", commit_info);
	    if (fits_write_comment(fptr, commit_info, &status)) {
	        fits_report_error(stderr, status);
		return;
	    }

            // Define the column parameters
            char *ttype[] ={"UNIT", "DEV", "NINT", "UNIXTIME", "FRAC", "NBYTES", "CORRTIME", "Ihigh", "Qhigh", \
			    "Ilow", "Qlow", "Ierr", "Qerr", "VIhi", "VQhi", "VIlo", "VQlo", "subScan", \
		            "THOT", "RA", "DEC", "filename", "spec"};

	    // All header values are signed 32-bit except UNIXTIME which is uint64_t
            char *tform[23];
	    tform[0]  = "1J"; //int
	    tform[1]  = "1J"; //int	
	    tform[2]  = "1J"; //int
	    tform[3]  = "1J"; //int	unixtime
	    tform[4]  = "1J"; //int
	    tform[5]  = "1J"; //int
	    tform[6]  = "1E"; //float	corrtime
            tform[7]  = "1J"; //int
            tform[8]  = "1J"; //int
            tform[9]  = "1J"; //int
            tform[10] = "1J"; //int
            tform[11] = "1J"; //int
            tform[12] = "1J"; //int
            tform[13] = "1E"; //float	Vdac
            tform[14] = "1E"; //float	Vdac
            tform[15] = "1E"; //float	Vdac
            tform[16] = "1E"; //float	Vdac
            tform[17] = "1J"; //int	subScan
            tform[18] = "1E"; //float	THOT
            tform[19] = "1E"; //float	RA
            tform[20] = "1E"; //float	DEC
	    tform[21] = "48A";//char    filename
            if(fits_header->unit==6){ //ACS5 B1
	       tform[22] = "512E";
	    }
            if(fits_header->unit==4){ //ACS3 B2
	       tform[22] = "1024E";
	    }

            char *tunit[23];
	    for(int i=0; i<23; i++)
	         tunit[i] = " ";

	    int tfields = 23;

            // Create a binary table
            if (fits_create_tbl(fptr, BINARY_TBL, 0, tfields   , ttype, tform, tunit, extname, &status)) {
                fits_report_error(stderr, status);  // Print any error message
                return;
            }

        } else {
            fits_report_error(stderr, status);  // Print any error message
            return;
        }
    }
    

    // Move to the named HDU (where the table is stored)
    if (fits_movnam_hdu(fptr, BINARY_TBL, extname, 0, &status)) {
        fits_report_error(stderr, status);  // Print any error message
        return;
    }

    // Get the current number of rows in the table
    if (fits_get_num_rows(fptr, &nrows, &status)) {
        fits_report_error(stderr, status);  // Print any error message
        return;
    }

    // insert a single empty row at the end of the output table
    if (fits_insert_rows(fptr, nrows, 1, &status)) {
        fits_report_error(stderr, status);  // Print any error message
        return;
    }

    // Write the header data
    fits_write_col(fptr, TINT32BIT,  1, nrows+1 , 1, 1, &fits_header->unit,  &status);
    fits_write_col(fptr, TINT32BIT,  2, nrows+1 , 1, 1, &fits_header->dev,  &status);
    fits_write_col(fptr, TINT32BIT,  3, nrows+1 , 1, 1, &fits_header->nint,  &status);
    fits_write_col(fptr, TINT32BIT,  4, nrows+1 , 1, 1, &fits_header->unixtime, &status);
    fits_write_col(fptr, TFLOAT,     5, nrows+1 , 1, 1, &fits_header->frac,  &status);
    fits_write_col(fptr, TINT32BIT,  6, nrows+1 , 1, 1, &fits_header->nbytes,  &status);
    fits_write_col(fptr, TFLOAT,     7, nrows+1 , 1, 1, &fits_header->corrtime,  &status);

    fits_write_col(fptr, TINT32BIT,  8, nrows+1 , 1, 1, &fits_header->Ihi,  &status);
    fits_write_col(fptr, TINT32BIT,  9, nrows+1 , 1, 1, &fits_header->Qhi, &status);
    fits_write_col(fptr, TINT32BIT, 10, nrows+1 , 1, 1, &fits_header->Ilo, &status);
    fits_write_col(fptr, TINT32BIT, 11, nrows+1 , 1, 1, &fits_header->Qlo, &status);
    fits_write_col(fptr, TINT32BIT, 12, nrows+1 , 1, 1, &fits_header->Ierr, &status);
    fits_write_col(fptr, TINT32BIT, 13, nrows+1 , 1, 1, &fits_header->Qerr, &status);

    fits_write_col(fptr, TFLOAT,    14, nrows+1,  1, 1, &fits_header->VIhi, &status);
    fits_write_col(fptr, TFLOAT,    15, nrows+1,  1, 1, &fits_header->VQhi, &status);
    fits_write_col(fptr, TFLOAT,    16, nrows+1,  1, 1, &fits_header->VIlo, &status);
    fits_write_col(fptr, TFLOAT,    17, nrows+1,  1, 1, &fits_header->VQlo, &status);
									       
    fits_write_col(fptr, TINT32BIT, 18, nrows+1,  1, 1, &fits_header->subScan, &status);
    fits_write_col(fptr, TFLOAT,    19, nrows+1,  1, 1, &fits_header->THOT, &status);
    fits_write_col(fptr, TFLOAT,    20, nrows+1,  1, 1, &fits_header->RA, &status);
    fits_write_col(fptr, TFLOAT,    21, nrows+1,  1, 1, &fits_header->DEC, &status);

    fits_write_col(fptr, TSTRING,   22, nrows+1,  1, 1, &fits_header->filename, &status);

    if(fits_header->unit==6){ //ACS5 B1
        array_length=512;
    }
    if(fits_header->unit==4){ //ACS3 B2
        array_length=1024;
    }
									     
    // Write the spectra as a single 2*N column
    if (fits_write_col(fptr, TDOUBLE, 23, nrows+1 , 1, 1 * array_length, array, &status)) {
        fits_report_error(stderr, status);  // Print any error message
        return;
    }

    // Close the FITS file
    if (fits_close_file(fptr, &status)) {
        fits_report_error(stderr, status);  // Print any error message
        return;
    }

    if (DEBUG)
       printf("Array appended as a new row in the FITS table successfully.\n");
}

void printDateTimeFromEpoch(time_t ts){

        struct tm *tm = gmtime(&ts);

        char buffer[26];
        strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", tm);
        printf("UTC Date and Time: %s\n", buffer);
}


int numPlaces (int n) {
    if (n < 0) return numPlaces ((n == INT_MIN) ? INT_MAX: -n);
    if (n < 10) return 1;
    return 1 + numPlaces (n / 10);
}


char nthdigit(int x, int n)
{
    while (n--) {
        x /= 10;
    }
    return (x % 10) + '0';
}


// Callback function to process the file
// Function definition changes for FSWATCH or INOTIFY or NO_FS
#ifdef USE_FSWATCH
void const callback(const fsw_cevent *events,const unsigned int event_num, void *data){

   char *filein= events->path;
   // for fswatch, get just the filename, not path
   char *name;
   char *last = strrchr(filein, '/');
   if (last != NULL) {
      sprintf(name, "%s", last+1);
   }
#endif

#if USE_INOTIFY
void const callback(struct inotify_event *event, const char *directory){

   char filein[128];
   snprintf(filein, 128, "%s/%s", directory, event->name);
   char *name = event->name;
#endif

#ifdef NO_FS
void const callback(char *filein){
   char *name = malloc(48*sizeof(char));
   strcpy(name, filein);
#endif

   //char errfile[64] = "err.log";

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
   //FILE *fout;
   //FILE *errf;
   double P_I;
   double P_Q;
   double Ipwr;
   double Qpwr;
   struct corrType corr;

   // correlator variables from datafile
   uint64_t UNIXTIME;
   int NINT;
   int UNIT;
   int DEV;
   int NBYTES;
   float FRAC;

   float FS_FREQ; // Full scale frequency, B1==5000MHz || B2==5000MHz
   float dacV[4]; //0=VIhi, 1=VQhi, 2=VIlo, 3=VQlo
   float VIhi,  VQhi,  VIlo,  VQlo;

   // For integer correlator lags
   //int32_t *Rn;
   //int32_t *Rn2;
   
   // For normalized float correlator lags from Quant Corr
   float *Rn;
   float *Rn2;

   //telemetry objects
   float RA=0.;
   float DEC=0.;
   float THOT=0.;
   int IF=0.;
   float VLSR=0.;
   float LO=0.;
   char *TARGET = (char *)malloc(16);

   // notification
   printf("File changed: %s\n", filein);
   fp = fopen(filein, "r");

   // Find file type from filename
   int i=0;
   char *ptr = NULL;
   char *prefix=malloc(4*sizeof(char));;
   const char *prefix_names[]={"SRC", "REF", "OTF", "HOT", "COLD", "FOC", "UNK"};
   while ( ptr==NULL ){
      ptr = strstr(filein, prefix_names[i]);
      i++;
   }
   int len = strlen(prefix_names[i-1]);
   strncpy(prefix, ptr, len);
   prefix[len] = '\0';
   printf("The type is %s\n", prefix);

   // Find scanID from filename
   char *token;
   int position = 0;
   int scanID  = -1;
   int CALID   = -1;
   int THOTID  = -1;
   int TUNEID  = -1;
   int subScan = -1;
   bool error  = FALSE;

    // Use strtok to tokenize the filename using underscores as delimiters
    token = strtok(filein, "_");

   // Iterate through the tokens until reaching the 2nd position
   while (token != NULL ) {
      token = strtok(NULL, "_");

      if (position == 1 ) {      //get scanID
         if(atoi(token)>0) scanID = atoi(token);
         printf("The scanID is: %d\n", scanID);
      }

      if (position == 2 ) {      //get subscanID
         subScan = atoi(token);
         printf("The data file index # is: %05d\n", subScan);
      }

      position++;
   }


   // Build a regex with the range of the previous 16 scanID #s for Correlator DACs
   char scanIDregex[512];
   int pos = 0;
   pos += sprintf(&scanIDregex[pos], "^(");
   for (int k=0; k<15; k++){
      pos += sprintf(&scanIDregex[pos], "%d|", scanID-k);
   }
   pos += sprintf(&scanIDregex[pos], "%d)$", scanID-15);
   if (DEBUG)
      printf("%s\n", scanIDregex);


   // Build a regex with the range of the previous 12 and next 12 scanID #s for HK_TEMP11
   char HOTregex[512];
   pos = 0;
   pos += sprintf(&HOTregex[pos], "^(");
   for (int k=0; k<24; k++){
      pos += sprintf(&HOTregex[pos], "%d|", scanID-k+12);
   }
   pos += sprintf(&HOTregex[pos], "%d)$", scanID-12);
   if (DEBUG)
      printf("%s\n", HOTregex);


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
   const char *header_names[]={"UNIT", "DEV", "NINT", "UNIXTIME", "FRAC", "NBYTES", "CORRTIME", \
			       "EMPTY", "Ihigh", "Qhigh", "Ilow", "Qlow", "Ierr", "Qerr"};

//////////////////////////////  LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////


   // Start at beginning of data file
   for(int j=0; j<(int)sz/bps; j++)
   {

   // Declare all Python objects for refpower
   // pArgs 
   PyObject *pArgs;
   PyObject *pValue;

   // Python objects for quantization correction
   PyObject *pArgsII, *pArgsQI, *pArgsIQ, *pArgsQQ; 
   PyObject *pListII, *pListQI, *pListIQ, *pListQQ; 
   PyObject *pValueII, *pValueQI, *pValueIQ, *pValueQQ; 

   // Arguments to relpower(XmonL, XmonH)
   if(DOQC){
      pArgs   = PyTuple_New(2); // for relpower(XmonL, XmonH)
      pArgsII = PyTuple_New(5); // for qc(ImonL, ImonH, ImonL, ImonH, corr.II)
      pArgsIQ = PyTuple_New(5); // for qc(ImonL, ImonH, QmonL, QmonH, corr.IQ)
      pArgsQI = PyTuple_New(5); // for qc(QmonL, QmonH, ImonL, ImonH, corr.IQ)
      pArgsQQ = PyTuple_New(5); // for qc(QmonL, QmonH, QmonL, QmonH, corr.QQ)
   }


   if (DEBUG)
      printf("The type is %s\n", prefix);
      // Loop over header location
      for(int i=0; i<22; i++){
         if(i==3){
            //UNIXTIME is 64 bits
            fread(&value1, 4, 1, fp); //Least significant 32 bits
            fread(&value2, 4, 1, fp); //Most significant 32 bis
            UNIXTIME = (((uint64_t)value2 << 32) | value1 ) / 1000.; //unixtime is to msec, store as 1sec int
            FRAC     = (((uint64_t)value2 << 32) | value1 ) % 1000 ; //fractional part is 1msec
         }
         else{
            fread(&value, 4, 1, fp);
         }
         header[i] = (value);
      }
      // data file *fp is now at start of lag data

      // fill variables from header array
      UNIT          = header[0];
      DEV           = header[1];
      NINT          = header[2];
      //UNIXTIME    = header[3]; 64 bits
      //CPU         = header[4]; broken?
      NBYTES        = header[5];
      corr.corrtime = header[6];
      //EMPTY         header[7];
      corr.Ihi      = header[8];
      corr.Qhi      = header[9];
      corr.Ilo      = header[10];
      corr.Qlo      = header[11];
      corr.Ierr     = header[12];
      corr.Qerr     = header[13];

      // Since we know UNIT and NLAGS, set correlator frequency and fits spectrum for later use
      if(UNIT==6){ //ACS5 B1
         FS_FREQ = 5000.;
      }
      if(UNIT==4){ //ACS3 B2
         FS_FREQ = 5000.;
      }

      // Indication that this is a broken header file from correlator STOP signal
      if (corr.Ierr!=0 || corr.Qerr!=0 || \
           corr.Ihi==0 ||  corr.Qhi==0 || corr.Ilo==0 || corr.Qlo==0 || \
           (corr.corrtime*256.)/(FS_FREQ*1000000.)<0.1 || (corr.corrtime*256.)/(FS_FREQ*1000000.)>10.0 )
      {
         printf("######################## ERROR ###########################\n");
         printf("#                                                        #\n");
         printf("#                Error, data is no good!                 #\n");
         printf("#                        Exiting!                        #\n");
         printf("#                                                        #\n");
         printf("######################## ERROR ###########################\n");
         printf("CORRTIME was %.6f\n\n", (corr.corrtime*256.)/(FS_FREQ*1000000.));
	 error = TRUE;
         break;
      }

      // Last VLSR tuning from InfluxDB anytime before current obs time 
      curl = init_influx();
      sprintf(query, "&q=SELECT last(VLSR),* FROM \"tuning\" WHERE time<=\%" PRIu64 "000000000", UNIXTIME);
      influxReturn = influxWorker(curl, query);
      if(UNIT==6){ //ACS5 B1
         IF   = influxReturn->value[1];
         LO   = influxReturn->value[3];
      }
      if(UNIT==4){ //ACS3 B2
         IF   = influxReturn->value[2];
         LO   = influxReturn->value[4];
      }
      TARGET = influxReturn->text;
      VLSR   = influxReturn->value[0];
      TUNEID = influxReturn->scanID;


      // RA, DEC from InfluxDB 0.5s ahead or behind time
      // hesperia DB = 28800
      // sculptor DB = 25200
      curl = init_influx();
      sprintf(query, "&q=SELECT * FROM \"udpPointing\" WHERE \"scanID\"=~/%d/ AND time>\%" PRIu64 "500000000 AND time<\%" PRIu64 "500000000", scanID, UNIXTIME-1-25200, UNIXTIME+0-25200);
      influxReturn = influxWorker(curl, query);
      DEC = influxReturn->value[0];
      RA  = influxReturn->value[1];

      // Free the allocated memory from udpPointing
      freeinfluxStruct(influxReturn);

     
      // Most recent HOT temperature from current scanID or ahead/behind 2 scanIDs
      curl = init_influx();
      sprintf(query, "&q=SELECT * FROM \"HK_TEMP11\"   WHERE \"scanID\"=~/%s/ ORDER BY time DESC LIMIT 3", HOTregex);
      influxReturn = influxWorker(curl, query);
      THOT = influxReturn->value[0] + 273.13; //Kelvin -> Celsius
      THOTID = influxReturn->scanID;

      if (DEBUG)
         printf("======== RA=%.3f DEC=%.3f THOT=%.1f==========\n", RA, DEC, THOT);  //Info print

      // Free the allocated memory from HK_TEMP11
      freeinfluxStruct(influxReturn);


      // Single SELECT for CORRELATOR DACS from current or nearest previous Correlator Cal
      curl = init_influx();
      sprintf(query, "&q=SELECT * FROM /^ACS%d_DEV%d_*/ WHERE \"scanID\"=~/%s/ ORDER BY time DESC LIMIT 10", UNIT-1, DEV, scanIDregex);
      influxReturn = influxWorker(curl, query);
      dacV[0] = influxReturn->value[3]; //VIhi  Order is reverse alphabetical from InfluxDB SELECT
      dacV[1] = influxReturn->value[1]; //VQhi
      dacV[2] = influxReturn->value[2]; //VIlo
      dacV[3] = influxReturn->value[0]; //VQlo
      CALID = influxReturn->scanID;

      // Free Influx struct from ACS_DEV_VDAC
      freeinfluxStruct(influxReturn);

      // don't trust myself to rewrite the below, just copy from vector into floats
      VIhi = dacV[0];
      VQhi = dacV[1];
      VIlo = dacV[2];
      VQlo = dacV[3];

      // this section unfuck-ifys special cases when ICE was off by one
      if (VQlo==0.){
         VIhi=VIhi-(VIlo-VQhi);  //make up this lost data, it'l be close enough
         VQhi = dacV[0];
         VIlo = dacV[1];
         VQlo = dacV[2];
      }
      
      if(VIhi==0.){ //Still no values?  bail and don't make spectra
         printf("######################## ERROR ###########################\n");
         printf("#                                                        #\n");
         printf("#                  Error, no DAC values!                 #\n");
         printf("#                        Exiting!                        #\n");
         printf("#                                                        #\n");
         printf("######################## ERROR ###########################\n");
         break;
      }

      // DEBUG
      if (DEBUG)
         printf("VIhi %.3f\tVQhi %.3f\tVIlo %.3f\tVQlo %.3f\n", VIhi, VQhi, VIlo, VQlo);


      // Build the spectra filename and put it in the spectra directory
      //char fileout[512];

      //sprintf(fileout, "spectra/ACS%d_%s_%05d_DEV%d_INDX%04d_NINT%03d.txt", UNIT-1, prefix, scanID, DEV, subScan, j);
      //fout = fopen(fileout, "w");

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


      //We don't know the lag # until we open the file, so malloc now
      corr.II   = malloc(N*sizeof(int32_t));   //Uncorrected ints
      corr.QI   = malloc(N*sizeof(int32_t));
      corr.IQ   = malloc(N*sizeof(int32_t));
      corr.QQ   = malloc(N*sizeof(int32_t));
      corr.IIqc = malloc(N*sizeof(float));     //Normalized Quantization Corrected floats
      corr.QIqc = malloc(N*sizeof(float));
      corr.IQqc = malloc(N*sizeof(float));
      corr.QQqc = malloc(N*sizeof(float));
      //Rn  = malloc(2*N*sizeof(int32_t));     //Rn,Rn2 ints for unquantization corrected
      //Rn2 = malloc(4*N*sizeof(int32_t));
      Rn  = malloc(2*N*sizeof(float));         //Rn,Rn2 floats for normalizaed, quantization corrected
      Rn2 = malloc(4*N*sizeof(float));

      // Read lags in from file in order after header
      for(int i=0; i<N; i++){
         fread(&value, 4, 1, fp);
         corr.II[i] = value;
         fread(&value, 4, 1, fp);
         corr.QI[i] = value;
         fread(&value, 4, 1, fp);
         corr.IQ[i] = value;
         fread(&value, 4, 1, fp);
         corr.QQ[i] = value;
      }



      // PASS THE UNCORRECTED LAGS INTO PYTHON FOR QUANTIZATION CORRECTION HERE !!!
       

      if(DOQC){
      // create a Python list and fill it with normalized uncorrected correlation coefficients
      // Check for errors
      if (pModule != NULL) {
         // Get the function from the module

         if (pFunc2 && PyCallable_Check(pFunc2)) {
            // For first four arguments: XmonL, XmonH, YmonL, YmonH
	    // II
	    PyTuple_SetItem(pArgsII, 0, PyFloat_FromDouble((double)corr.Ilo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsII, 1, PyFloat_FromDouble((double)corr.Ihi/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsII, 2, PyFloat_FromDouble((double)corr.Ilo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsII, 3, PyFloat_FromDouble((double)corr.Ihi/(double)corr.corrtime));
            // IQ
	    PyTuple_SetItem(pArgsIQ, 0, PyFloat_FromDouble((double)corr.Ilo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsIQ, 1, PyFloat_FromDouble((double)corr.Ihi/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsIQ, 2, PyFloat_FromDouble((double)corr.Qlo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsIQ, 3, PyFloat_FromDouble((double)corr.Qhi/(double)corr.corrtime));
            // QI
	    PyTuple_SetItem(pArgsQI, 0, PyFloat_FromDouble((double)corr.Qlo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsQI, 1, PyFloat_FromDouble((double)corr.Qhi/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsQI, 2, PyFloat_FromDouble((double)corr.Ilo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsQI, 3, PyFloat_FromDouble((double)corr.Ihi/(double)corr.corrtime));
            // QQ
	    PyTuple_SetItem(pArgsQQ, 0, PyFloat_FromDouble((double)corr.Qlo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsQQ, 1, PyFloat_FromDouble((double)corr.Qhi/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsQQ, 2, PyFloat_FromDouble((double)corr.Qlo/(double)corr.corrtime));
	    PyTuple_SetItem(pArgsQQ, 3, PyFloat_FromDouble((double)corr.Qhi/(double)corr.corrtime));

            // For fifth argument: convert C array to a Python List
	    // Creates new reference here.  pList** must be DECREF to free
            pListII = PyList_New(N);
            pListQI = PyList_New(N);
            pListIQ = PyList_New(N);
            pListQQ = PyList_New(N);
	   
            for (int i=0; i<N; ++i){
               PyList_SetItem(pListII, i, PyFloat_FromDouble((double)corr.II[i]/(double)corr.corrtime));
               PyList_SetItem(pListIQ, i, PyFloat_FromDouble((double)corr.IQ[i]/(double)corr.corrtime));
               PyList_SetItem(pListQI, i, PyFloat_FromDouble((double)corr.QI[i]/(double)corr.corrtime));
               PyList_SetItem(pListQQ, i, PyFloat_FromDouble((double)corr.QQ[i]/(double)corr.corrtime));
            }
	    // pList** are stolen by SetItem here.  Do not DECREF
	    PyTuple_SetItem(pArgsII, 4, pListII);
	    PyTuple_SetItem(pArgsIQ, 4, pListIQ);
	    PyTuple_SetItem(pArgsQI, 4, pListQI);
	    PyTuple_SetItem(pArgsQQ, 4, pListQQ);


	    // DEBUG print uncorrected
	    if (DEBUG) {
	       printf("XY   ");
               for (int i=0; i<10; ++i)
                  printf("%f ", (float) corr.II[i]/corr.II[0]);
	       printf("\n");
	    }
   
            // Call the function
            pValueII = PyObject_CallObject(pFunc2, pArgsII);
            pValueIQ = PyObject_CallObject(pFunc2, pArgsIQ);
            pValueQI = PyObject_CallObject(pFunc2, pArgsQI);
            pValueQQ = PyObject_CallObject(pFunc2, pArgsQQ);
   
            // Check for errors
            if (pValueII != NULL && pValueIQ != NULL && pValueQI != NULL && pValueQQ != NULL) {
               // Extract the values from the returned list
               for (int i=0; i<N; ++i){

		  // Fill corrqc struct with normalized float32 QC values
                  corr.IIqc[i] = PyFloat_AsDouble(PyList_GetItem(pValueII, i));
                  corr.IQqc[i] = PyFloat_AsDouble(PyList_GetItem(pValueIQ, i));
                  corr.QIqc[i] = PyFloat_AsDouble(PyList_GetItem(pValueQI, i));
                  corr.QQqc[i] = PyFloat_AsDouble(PyList_GetItem(pValueQQ, i));
               }
            } else{
	       PyErr_Print();
	    }


	    // DEBUG print corrected
	    if (DEBUG) {
	       printf("XYqc ");
               for (int i=0; i<10; ++i)
                  printf("%f ", corr.IIqc[i]);
	       printf("\n");
	    }


         } else {
	    if (PyErr_Occurred()) {
	       PyErr_Print();
	       fprintf(stderr, "Cannot find function\n");
	    }
	 }
      } else {
	 PyErr_Print();
	 fprintf(stderr, "Failed to load the Python module\n");
      }
   }  // END IF DOQC
      
      // If we're not going to do the QC DLL, then just copy lags over and normlize them at least
   else
   {
      for(int i=0; i<N; i++){
         corr.IIqc[i] = corr.II[i]/corr.II[0];
         corr.IQqc[i] = corr.IQ[i]/corr.IQ[0];
         corr.QIqc[i] = corr.QI[i]/corr.QI[0];
         corr.QQqc[i] = corr.QQ[i]/corr.QQ[0];
      }
   }  // END IF ELSE


      // GET THE QUANTIZATION CORRECTED LAGS BACK AND  CONTINUE ON WITH LAGS->SPECTRA


      // Combine IQ lags into R[]
         for(int i=0; i<(2*N)-1; i++){
            if(i%2 == 0) Rn[i] = 0.5* (corr.IIqc[i/2] + corr.QQqc[i/2]);           // Even indicies
            if(i%2 == 1) Rn[i] = 0.5* (corr.IQqc[(i-1)/2] + corr.QIqc[(i-1)/2+1]); // Odd  indicies
         }
         int le = 2*N-1; //last element
         Rn[le] = 0.5* (corr.IQqc[(le-1)/2] + corr.QIqc[(le-1)/2]);         // Last element

      // Mirror R[] symmetrically
         for(int i=0; i<4*N-1; i++){
           if( i<2*N ) Rn2[2*N-1-i] = Rn[i];
           else        Rn2[i]       = Rn[i-(2*N-1)];
         }

/*
      // Try the Omnisys ICD spectrometer_api_CCv0005.docx routine
      //
      // Set QC[0] = 0
      corr.IQqc[0] = 0.;
      // circular shift minus one step
       circularShiftLeft(corr.IQqc, sizeof(corr.IQqc) / sizeof(corr.IQqc[0]));

        for(int i=0; i<2*N; i+=2){
           Rn[i]   = 0.5 * (corr.IIqc[i/2] + corr.QQqc[i/2]);
           Rn[i+1] = 0.5 * (corr.IQqc[i/2] + corr.QIqc[i/2]);
        }
      // For whatever reason, this doesn't work straight outta the box
*/

      // Apply Hann window
         for(int i=0; i<4*N; i++){
           Rn2[i] = Rn2[i]*0.5*(1-cos(2*PI*i/(4*N)));     //real with Hann window
         }

      // Fill fft struct
         for(int i=0; i<4*N; i++){
           spec[specA].in[i][0] = Rn2[i];  //real
           spec[specA].in[i][1] = 0.;      //imag
         }

      // Do FFT and print
         fftw_execute(spec[specA].p);

      // Compute Power Coefficients
         P_I = pow((VIhi-VIlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Ihi/(double)corr.corrtime)) + \
                                                 (erfinv(1-2*(double)corr.Ilo/(double)corr.corrtime)),2);
         P_Q = pow((VQhi-VQlo),2) * 1.8197 / pow((erfinv(1-2*(double)corr.Qhi/(double)corr.corrtime)) + \
                                                 (erfinv(1-2*(double)corr.Qlo/(double)corr.corrtime)),2);

      // GET ALTERNATIVE POWER CALIBRATION FROM OMNISYS DLL
      // P_I,  P_Q calculated from the inverse error function using (Ihi, Ilow) is equal
      // to the relpower function from the Omnisys DLL to high precision. When  validated
      // over a range of power levels (HOT, OTF, REF) the two give equal results
      // (The factor 1.8197 likely comes from the erfinv for a 3-level ACS)
      
      if(DOQC){ // Only do this if Python Objects are declared
         PyTuple_SetItem(pArgs, 0, PyFloat_FromDouble((double)corr.Ilo/corr.corrtime));
         PyTuple_SetItem(pArgs, 1, PyFloat_FromDouble((double)corr.Ihi/corr.corrtime));
         pValue = PyObject_CallObject(pFunc1, pArgs);
         Ipwr = 2. * pow((VIhi-VIlo),2) * PyFloat_AsDouble(pValue);

         PyTuple_SetItem(pArgs, 0, PyFloat_FromDouble((double)corr.Qlo/corr.corrtime));
         PyTuple_SetItem(pArgs, 1, PyFloat_FromDouble((double)corr.Qhi/corr.corrtime));
         pValue = PyObject_CallObject(pFunc1, pArgs);
         Qpwr = 2. * pow((VQhi-VQlo),2) * PyFloat_AsDouble(pValue);


         // Output the relative power comparison
         if (DEBUG)
            printf("Ipwr is %f\tQpwr is %f\tP_I is %f\tP_Q is %f\n", Ipwr, Qpwr, P_I, P_Q);
      }

      // Comment out all text spectral file outputs.  FITS done below
      // Will be deprecated soon.
      // Header information in spectra file
/*
      fprintf(fout, "UNIXTIME\t%" PRIu64 "\n", UNIXTIME);
      fprintf(fout, "CORRTIME\t%.6f\n", (corr.corrtime*256.)/(FS_FREQ*1000000.));
      fprintf(fout, "UNIT\t%d\n", UNIT);
      fprintf(fout, "DEV\t%d\n",   DEV); 
      fprintf(fout, "NLAGS\t%d\n", N);
      fprintf(fout, "NINT\t%d\n", NINT);
      fprintf(fout, "LEVEL_Ihi\t%.2f\n",  (double)corr.Ihi/(double)corr.corrtime);
      fprintf(fout, "LEVEL_Qhi\t%.2f\n",  (double)corr.Qhi/(double)corr.corrtime);
      fprintf(fout, "LEVEL_Ilo\t%.2f\n",  (double)corr.Ilo/(double)corr.corrtime);
      fprintf(fout, "LEVEL_Qlo\t%.2f\n",  (double)corr.Qlo/(double)corr.corrtime);
      fprintf(fout, "IHI\t%u\n",  corr.Ihi);
      fprintf(fout, "QHI\t%u\n",  corr.Qhi);
      fprintf(fout, "ILO\t%u\n",  corr.Ilo);
      fprintf(fout, "QLO\t%u\n",  corr.Qlo);

    // Used calibration DAC voltages
      fprintf(fout, "VIHI\t%.3f\nVQHI\t%.3f\nVILO\t%.3f\nVQLO\t%.3f\n", VIhi, VQhi, VIlo, VQlo);
      fprintf(fout, "CAL\t%d\n", CALID);
      fprintf(fout, "DATA\t%d\n", scanID);

    // Data consistency checks and error flaging
      fprintf(fout, "IERR\t%u\n", corr.Ierr);
      fprintf(fout, "QERR\t%u\n", corr.Qerr);
      fprintf(fout, "ZEROLAGSUM_I\t%u\t%u\n", corr.Ihi+corr.Ilo, corr.II[0]);
      fprintf(fout, "ZEROLAGSUM_Q\t%u\t%u\n", corr.Qhi+corr.Qlo, corr.QQ[0]);
*/

      // Write to error log.
      // Was for flight ops.  Probably will deprecate soon.
      /*
      if(1)
      {
         errf = fopen(errfile, "a");
         fprintf(errf, "%s\t", name);
         fflush(errf);
         fprintf(errf, "%" PRIu64 "\t", UNIXTIME);
         fprintf(errf, "%u\t", CPU); //CPU => FRAC
         fprintf(errf, "%s\t", prefix);
         fprintf(errf, "%d\t%d\t", UNIT, DEV);
         fprintf(errf, "%.6f\t", (corr.corrtime*256.)/(FS_FREQ*1000000.));
         fprintf(errf, "%u\t", corr.Ierr);
         fprintf(errf, "%u\t", corr.Qerr);
         fprintf(errf, "%u\t", abs((corr.Ihi+corr.Ilo)-corr.II[0]));
         fprintf(errf, "%u\n", abs((corr.Qhi+corr.Qlo)-corr.QQ[0]));
         fclose(errf);
      }
      */

      //fprintf(fout, "ETAQ\t%.3f\n", 1/sqrt(P_I*P_Q));
   
      //Print in counts per second (assuming FS_FREQ sampling freq)
      /*
      for(int i=0; i<2*N; i++){
         fprintf(fout, "%d\t%lf\n", (FS_FREQ*i)/(2*N), sqrt(P_I*P_Q) * \
                                    sqrt(pow(spec[specA].out[i][0],2)+pow(spec[specA].out[i][1],2)));
      }
      fclose(fout); //close single spectra file
      */
		    

/*
 * Don't use this stuff, it was for V&V with the lags and spectra from LabView.
 * Never gets utilized now, will be deprecated in the future
      if (DEBUG>1){
         fout = fopen("lags.txt", "w");
         //Save QC lags
         for(int i=0; i<N; i++){
            fprintf(fout, "%d\t%f\t%f\t%f\t%f\n", i, corr.IIqc[i], corr.QQqc[i], corr.IQqc[i], corr.QIqc[i]);
         }
         fclose(fout);


         fout = fopen("lagsRn.txt", "w");
         //Save combined lags
         for(int i=0; i<2*N; i++){
            fprintf(fout, "%d\t%f\n", i,Rn[i]);
         }
         fclose(fout);


         fout = fopen("lagsRn2.txt", "w");
         //Save combined mirrored lags
         for(int i=0; i<4*N; i++){
            fprintf(fout, "%d\t%f\n", i,Rn2[i]);
         }
         fclose(fout);
      }
 */


      // Construct the per row FITS HEADER

      s_header *fits_header = (s_header *)malloc(sizeof(s_header));
      fits_header->type     = (char *)malloc(6);
      fits_header->filename = (char *)malloc(48);
      fits_header->target   = (char *)malloc(16);

      fits_header->unit     = UNIT;
      fits_header->dev      = DEV;
      fits_header->nint     = NINT;
      fits_header->unixtime = (int) UNIXTIME;
      fits_header->frac     = FRAC;
      fits_header->nbytes   = NBYTES;
      fits_header->corrtime = (corr.corrtime*256.)/(FS_FREQ*1000000.);

      fits_header->Ihi      = corr.Ihi;
      fits_header->Qhi      = corr.Qhi;
      fits_header->Ilo      = corr.Ilo;
      fits_header->Qlo      = corr.Qlo;
      fits_header->Ierr     = corr.Ierr;
      fits_header->Qerr     = corr.Qerr;

      fits_header->VIhi     = VIhi;
      fits_header->VQhi     = VQhi;
      fits_header->VIlo     = VIlo;
      fits_header->VQlo     = VQlo;

      fits_header->scanID   = scanID;
      fits_header->subScan  = subScan;
      fits_header->CALID    = CALID;
      fits_header->THOT     = THOT;
      fits_header->RA       = RA;
      fits_header->DEC      = DEC;
      fits_header->IF       = IF;
      fits_header->LO       = LO;  
      fits_header->VLSR     = VLSR;

      strcpy(fits_header->type, prefix);
      strcpy(fits_header->filename, name);
      strcpy(fits_header->target, TARGET);
      
      // Construct the FITS DATA
      double *array = malloc(2*N*sizeof(double));
      for(int i=0; i<2*N; i++){
         array[i] = (FS_FREQ*1e6)/(corr.corrtime*256.) * sqrt(P_I*P_Q) * sqrt(pow(spec[specA].out[i][0],2)+pow(spec[specA].out[i][1],2));
      }

      // Let's try out CFITSIO!
      char fitsfile[20];
      sprintf(fitsfile, "ACS%d_%s_%05d.fits", UNIT-1, prefix, scanID);
      if (DEBUG)
         printf("%s\n", fitsfile);
      append_to_fits_table(fitsfile, fits_header, array, THOTID);


      // Free items before next spectra within this file
      // All of these objects are malloced at the start of every spectra
      free(corr.II);      //free all mallocs
      free(corr.QI);
      free(corr.IQ);
      free(corr.QQ);
      free(corr.IIqc);    //free all mallocs
      free(corr.QIqc);
      free(corr.IQqc);
      free(corr.QQqc);
      free(Rn);
      free(Rn2);
      free(array);

      free(fits_header->type);
      free(fits_header->filename);
      free(fits_header->target);
      free(fits_header);

//
// move to within 100 spectra loop
//

   // Clean Up memory before leaving callback()
   // All of these objects are malloced at the start of callback but re-used every spectra
   // 4 X pArgs 
   //printf("free pArgsII\t from refcount\t %ld\n", pArgsII->ob_refcnt);
   Py_DECREF(pArgsII);
   //printf("free pArgsIQ\t from refcount\t %ld\n", pArgsIQ->ob_refcnt);
   Py_DECREF(pArgsIQ);
   //printf("free pArgsQI\t from refcount\t %ld\n", pArgsQI->ob_refcnt);
   Py_DECREF(pArgsQI);
   //printf("free pArgsQQ\t from refcount\t %ld\n", pArgsQQ->ob_refcnt);
   Py_DECREF(pArgsQQ);
    
   // and the refpower
   //printf("free pArgs\t from refcount\t %ld\n", pArgs->ob_refcnt);
   Py_DECREF(pArgs);

   // 4 X pValue
   //printf("free pValueII\t from refcount\t %ld\n", pValueII->ob_refcnt);
   Py_DECREF(pValueII);
   //printf("free pValueIQ\t from refcount\t %ld\n", pValueIQ->ob_refcnt);
   Py_DECREF(pValueIQ);
   //printf("free pValueQI\t from refcount\t %ld\n", pValueQI->ob_refcnt);
   Py_DECREF(pValueQI);
   //printf("free pValueQQ\t from refcount\t %ld\n", pValueQQ->ob_refcnt);
   Py_DECREF(pValueQQ);
	       
   // and the refpower
   //printf("free pValue\t from refcount\t %ld\n", pValue->ob_refcnt);
   Py_DECREF(pValue);
   

   // 4 X pList
   // These don't need to be freed since PyList_SetItem() steals the reference
   /*
   printf("free pListII\t from refcount\t %ld\n", pListII->ob_refcnt);
   Py_DECREF(pListII);
   printf("free pListIQ\t from refcount\t %ld\n", pListIQ->ob_refcnt);
   Py_DECREF(pListIQ);
   printf("free pListQI\t from refcount\t %ld\n", pListQI->ob_refcnt);
   Py_DECREF(pListQI);
   printf("free pListQQ\t from refcount\t %ld\n", pListQQ->ob_refcnt);
   Py_DECREF(pListQQ);
   */
     
   if (DEBUG)
      printf("all Python Objects from callback() freed\n\n");
 
 //
 // end test free in loop
 //

   }

/////////////////////////////  END LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////
   
   fclose(fp);   //close input data file
		    
   if (!error){
      //ouput stats for last spectra in file
      printf("UNIXTIME is %" PRIu64 "\n", UNIXTIME);
      printf("CORRTIME is %.6f\n", (corr.corrtime*256.)/(FS_FREQ*1000000.));
      printDateTimeFromEpoch((long long) UNIXTIME);
      printf("UNIT is %d\n", UNIT);
      printf("DEV  is %d\n",  DEV); 
      printf("NINT is %d\n", NINT);
      printf("%.2f %.2f %.2f %.2f\n",  (double)corr.Ihi/(double)corr.corrtime, \
                                       (double)corr.Qhi/(double)corr.corrtime, \
                                       (double)corr.Ilo/(double)corr.corrtime, \
                                       (double)corr.Qlo/(double)corr.corrtime);
      printf("nlags=%d\n", N);
      printf("etaQ\t%.3f\n", 1/sqrt(P_I*P_Q));
      printf("ETAQ\t%.3f\n\n", 1/sqrt(Ipwr*Qpwr));

      // current scanID, and scanID used for cal
      printf("The cal    is from scanID: %d\n", CALID);
      printf("The THOT   is from scanID: %d\n", THOTID);
      printf("The data   is from scanID: %d\n", scanID);
      printf("The tuning is from scanID: %d\n", TUNEID);
      printf("\tIF   = %d MHz\n", IF);
      printf("\tVLSR = %.0f km/s\n", VLSR);
      printf("\tTRGET= %s\n", TARGET);
   }

   //timing
   gettimeofday(&end, 0);
   int seconds = end.tv_sec - begin.tv_sec;
   int microseconds = end.tv_usec - begin.tv_usec;
   double elapsed = seconds + microseconds*1e-6;
   if (!error)
      printf("AVG FFTW %.1f ms in %d spectra\n\n", 1000.*elapsed/(sz/bps), sz/bps);
   fflush(stdout);

   
//
// move to within 100 spectra loop
//
/*
   // Clean Up memory before leaving callback()
   // All of these objects are malloced at the start of callback but re-used every spectra
   // 4 X pArgs 
   printf("free pArgsII\t from refcount\t %ld\n", pArgsII->ob_refcnt);
   Py_DECREF(pArgsII);
   printf("free pArgsIQ\t from refcount\t %ld\n", pArgsIQ->ob_refcnt);
   Py_DECREF(pArgsIQ);
   printf("free pArgsQI\t from refcount\t %ld\n", pArgsQI->ob_refcnt);
   Py_DECREF(pArgsQI);
   printf("free pArgsQQ\t from refcount\t %ld\n", pArgsQQ->ob_refcnt);
   Py_DECREF(pArgsQQ);
    
   // and the refpower
   printf("free pArgs\t from refcount\t %ld\n", pArgs->ob_refcnt);
   Py_DECREF(pArgs);

   // 4 X pValue
   printf("free pValueII\t from refcount\t %ld\n", pValueII->ob_refcnt);
   Py_DECREF(pValueII);
   printf("free pValueIQ\t from refcount\t %ld\n", pValueIQ->ob_refcnt);
   Py_DECREF(pValueIQ);
   printf("free pValueQI\t from refcount\t %ld\n", pValueQI->ob_refcnt);
   Py_DECREF(pValueQI);
   printf("free pValueQQ\t from refcount\t %ld\n", pValueQQ->ob_refcnt);
   Py_DECREF(pValueQQ);
	       
   // and the refpower
   printf("free pValue\t from refcount\t %ld\n", pValue->ob_refcnt);
   Py_DECREF(pValue);
   

   // 4 X pList
   // These don't need to be freed since PyList_SetItem() steals the reference
   
   printf("free pListII\t from refcount\t %ld\n", pListII->ob_refcnt);
   Py_DECREF(pListII);
   printf("free pListIQ\t from refcount\t %ld\n", pListIQ->ob_refcnt);
   Py_DECREF(pListIQ);
   printf("free pListQI\t from refcount\t %ld\n", pListQI->ob_refcnt);
   Py_DECREF(pListQI);
   printf("free pListQQ\t from refcount\t %ld\n", pListQQ->ob_refcnt);
   Py_DECREF(pListQQ);
   
     
   printf("all Python Objects from callback() freed\n");
 */
 //
 // end test free in loop
 //
     
   // Free filename type char
   free(prefix);

   // Free Influx query string
   free(query);

   // Free Influx query string
   free(name);
   
}






