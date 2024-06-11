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
#include <fitsio.h>

#define PI 3.14159
#define BUFSIZE 128
#define DEBUG 1


void append_to_fits_table(const char *filename, double *array, long n_elements) {
    fitsfile *fptr;  // FITS file pointer
    int status = 0;  // CFITSIO status value MUST be initialized to zero!
    int hdutype;
    long nrows;
    char extname[] = "DATA_TABLE";

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

            // Define the column parameters
            char **ttype = malloc(n_elements * sizeof(char*));
            char **tform = malloc(n_elements * sizeof(char*));
            char **tunit = malloc(n_elements * sizeof(char*));
            for (long i = 0; i < n_elements; i++) {
                ttype[i] = malloc(10 * sizeof(char));
                snprintf(ttype[i], 10, "Data%ld", i+1);
                tform[i] = "D";
                tunit[i] = "";
            }

            // Create a binary table
	    //  fits_create_tbl(
            if (fits_create_tbl(fptr, BINARY_TBL, 0, n_elements, ttype, tform, tunit, extname, &status)) {
                fits_report_error(stderr, status);  // Print any error message
                return;
            }

            for (long i = 0; i < n_elements; i++) {
                free(ttype[i]);
            }
            free(ttype);
            free(tform);
            free(tunit);
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

    // Write the array as a new row in the binary table
    for (long i = 0; i < n_elements; i++) {
        if (fits_write_col(fptr, TDOUBLE, i + 1, nrows+1 , 1, 1, &array[i], &status)) {
            fits_report_error(stderr, status);  // Print any error message
            return;
        }
    }

    // Close the FITS file
    if (fits_close_file(fptr, &status)) {
        fits_report_error(stderr, status);  // Print any error message
        return;
    }

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

   char *name = filein;

#endif

   char errfile[64] = "err.log";

   // moved to main()
   // Initialize the Python interpreter
   //Py_Initialize();

   // moved to main()
   // common to both functions
   //PyObject *pName, *pModule;
   
   // for relpower
   //PyObject *pFunc1;
   PyObject *pArgs1, *pValue;

   // for qc
   //PyObject *pFunc2;
   PyObject *pArgsII, *pArgsQI, *pArgsIQ, *pArgsQQ; 
   PyObject *pListII, *pListQI, *pListIQ, *pListQQ; 
   PyObject *pValueII, *pValueQI, *pValueIQ, *pValueQQ; 

   // moved to main()
   // Build the name object for both functions from callQC.py file
   //pName = PyUnicode_FromString("callQC");

   // moved to main()
   // Load the module object
   //pModule = PyImport_Import(pName);

   // moved to main()
   // Get the two functions from the module
   //if (pModule != NULL){
   //   pFunc1 = PyObject_GetAttrString(pModule, "relpower");
   //   pFunc2 = PyObject_GetAttrString(pModule, "qc");
   //}


   // Arguments to relpower(XmonL, XmonH)
   pArgs1 = PyTuple_New(2); // for relpower(XmonL, XmonH)
   pArgsII = PyTuple_New(5); // for       qc(ImonL, ImonH, ImonL, ImonH, corr.II)
   pArgsIQ = PyTuple_New(5); // for       qc(ImonL, ImonH, QmonL, QmonH, corr.IQ)
   pArgsQI = PyTuple_New(5); // for       qc(QmonL, QmonH, ImonL, ImonH, corr.IQ)
   pArgsQQ = PyTuple_New(5); // for       qc(QmonL, QmonH, QmonL, QmonH, corr.QQ)

   // End Python initilization


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
   FILE *errf;
   double P_I;
   double P_Q;
   double Ipwr;
   double Qpwr;
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
   printf("File changed: %s\n", filein);
   fp = fopen(filein, "r");

   // Find file type from filename
   // TODO: implement the UNKNOWN filetype and use tokens
   int i=0;
   char *ptr = NULL;
   char *prefix=malloc(6*sizeof(char));;
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
   // TODO: combine the file type and scanID from filename 
   int scanID = -1;
   int dataN;
   char *token;
   int position = 0;

    // Use strtok to tokenize the filename using underscores as delimiters
    token = strtok(filein, "_");

    // Iterate through the tokens until reaching the 2nd position
    while (token != NULL ) {
        token = strtok(NULL, "_");

        if (position == 1 ) {      //get scanID
            if(atoi(token)>0) scanID = atoi(token);
            printf("The scanID is: %d\n", scanID);
        }

        if (position == 2 ) {      //get scanID
            dataN = atoi(token);
            printf("The data file index # is: %05d\n", dataN);
        }

        position++;
    }


   // Build a regex with the range of the previous 8 scanID #s
   char scanIDregex[512];
   int pos = 0;
   pos += sprintf(&scanIDregex[pos], "(");
   for (int k=0; k<30; k++){
      pos += sprintf(&scanIDregex[pos], "%d|", scanID-k);
   }
   pos += sprintf(&scanIDregex[pos], "%d)", scanID-30);
   printf("%s\n", scanIDregex);



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
      corr.Ierr     = header[12];
      corr.Qerr     = header[13];

      if (corr.Ierr!=0 || corr.Qerr!=0 || \
           corr.Ihi==0 ||  corr.Qhi==0 || corr.Ilo==0 || corr.Qlo==0 || \
           (corr.corrtime*256.)/(5000.*1000000.)<0.1 )
      {
         printf("######################## ERROR ###########################\n");
         printf("#                                                        #\n");
         printf("#                Error, data is no good!                 #\n");
         printf("#                        Exiting!                        #\n");
         printf("#                                                        #\n");
         printf("######################## ERROR ###########################\n");
         //break;
      }

      // Initialize the Influx DB
      // read 4 correlator DAC voltages
      for (int k=0; k<4; k++){
         curl = init_influx();
         sprintf(query, "&q=SELECT * FROM \"ACS%d_DEV%d%s\" WHERE \"scanID\"=~/%s/  \
                                                             ORDER BY time DESC LIMIT 10", \
                                          UNIT-1, DEV, query_list[k], scanIDregex);

         //dacV[k] = influxWorker(curl, query);
         influxReturn = influxWorker(curl, query);
         //influxReturn.scanID integer
         //influxReturn.value  float
         dacV[k] = influxReturn.value;
      }
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
      
      // DEBUG
      if (DEBUG)
         printf("VIhi %.3f\tVQhi %.3f\tVIlo %.3f\tVQlo %.3f\n", VIhi, VQhi, VIlo, VQlo);

      if(VIhi==0.){ //Still no values?  bail and don't make spectra
        printf("no DAC values, bailing.\n");
        //break;
      }


      // Build the spectra filename and put it in the spectra directory
      char fileout[512] = "";

      sprintf(fileout, "spectra/ACS%d_%s_%05d_DEV%d_INDX%04d_NINT%03d.txt", \
                                               UNIT-1, prefix, scanID, DEV, dataN, j);
      fout = fopen(fileout, "w");

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
      corr.II   = malloc(N*sizeof(int32_t));
      corr.QI   = malloc(N*sizeof(int32_t));
      corr.IQ   = malloc(N*sizeof(int32_t));
      corr.QQ   = malloc(N*sizeof(int32_t));
      Rn  = malloc(2*N*sizeof(int32_t));
      Rn2 = malloc(4*N*sizeof(int32_t));

      // Read lags
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
       



      // create a Python list and fill it with normalized uncorrected correlation coefficients
      // Check for errors
      if (pModule != NULL) {
         // Get the function from the module
         //pFunc2 = PyObject_GetAttrString(pModule, "qc");

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
	    PyTuple_SetItem(pArgsII, 4, pListII);
	    PyTuple_SetItem(pArgsIQ, 4, pListIQ);
	    PyTuple_SetItem(pArgsQI, 4, pListQI);
	    PyTuple_SetItem(pArgsQQ, 4, pListQQ);


	    // DEBUG print uncorrected
	    if (DEBUG) {
	       printf("XY   ");
               for (int i=0; i<10; ++i)
                  printf("%d ", corr.II[i]);
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
                  corr.II[i] = (int32_t) (0.5 * corr.corrtime * PyFloat_AsDouble(PyList_GetItem(pValueII, i)));
                  corr.IQ[i] = (int32_t) (0.5 * corr.corrtime * PyFloat_AsDouble(PyList_GetItem(pValueIQ, i)));
                  corr.QI[i] = (int32_t) (0.5 * corr.corrtime * PyFloat_AsDouble(PyList_GetItem(pValueQI, i)));
                  corr.QQ[i] = (int32_t) (0.5 * corr.corrtime * PyFloat_AsDouble(PyList_GetItem(pValueQQ, i)));
               }
	       //Py_DECREF(pValueII);
            } else{
	       PyErr_Print();
	    }


	    // DEBUG print corrected
	    if (DEBUG) {
	       printf("XYqc ");
               for (int i=0; i<10; ++i)
                  printf("%d ", corr.II[i]);
	       printf("\n");
	       printf("\n");
	    }


	    // Clean Up
	    // Py_DECREF(pListII);
         } else {
	    if (PyErr_Occurred()) {
	       PyErr_Print();
	       fprintf(stderr, "Cannot find function\n");
	    }
	 }
	 //Py_XDECREF(pFunc2);
	 //Py_DECREF(pModule);
      } else {
	 PyErr_Print();
	 fprintf(stderr, "Failed to load the Python module\n");
      }





      // GET THE QUANTIZATION CORRECTED LAGS BACK AND USE BELOW !!!
   




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

      // GET ALTERNATIVE POWER CALIBRATION FROM OMNISYS DLL
      // P_I,  P_Q calculated from the inverse error function using (Ihi, Ilow) is equal
      // to the relpower function from the Omnisys DLL to high precision. When  validated
      // over a range of power levels (HOT, OTF, REF) the two give equal results up to a
      // factor of 2.   (The factor 1.8197 likely comes from the erfinv for a 3-level ACS
      PyTuple_SetItem(pArgs1, 0, PyFloat_FromDouble((double)corr.Ilo/corr.corrtime));
      PyTuple_SetItem(pArgs1, 1, PyFloat_FromDouble((double)corr.Ihi/corr.corrtime));
      pValue = PyObject_CallObject(pFunc1, pArgs1);
      Ipwr = 2. * pow((VIhi-VIlo),2) * PyFloat_AsDouble(pValue);

      PyTuple_SetItem(pArgs1, 0, PyFloat_FromDouble((double)corr.Qlo/corr.corrtime));
      PyTuple_SetItem(pArgs1, 1, PyFloat_FromDouble((double)corr.Qhi/corr.corrtime));
      pValue = PyObject_CallObject(pFunc1, pArgs1);
      Qpwr = 2. * pow((VQhi-VQlo),2) * PyFloat_AsDouble(pValue);

      // Output the relative power comparison
      if (DEBUG)
         printf("Ipwr is %f\tQpwr is %f\tP_I is %f\tP_Q is %f\n", Ipwr, Qpwr, P_I, P_Q);

      // Header information in spectra file
      fprintf(fout, "UNIXTIME\t%" PRIu64 "\n", UNIXTIME);
      fprintf(fout, "CORRTIME\t%.6f\n", (corr.corrtime*256.)/(5000.*1000000.));
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
      fprintf(fout, "CAL\t%d\n", influxReturn.scanID);
      fprintf(fout, "DATA\t%d\n", scanID);

    // Data consistency checks and error flaging
      fprintf(fout, "IERR\t%u\n", corr.Ierr);
      fprintf(fout, "QERR\t%u\n", corr.Qerr);
      fprintf(fout, "ZEROLAGSUM_I\t%u\t%u\n", corr.Ihi+corr.Ilo, corr.II[0]);
      fprintf(fout, "ZEROLAGSUM_Q\t%u\t%u\n", corr.Qhi+corr.Qlo, corr.QQ[0]);

      if(1)
      {
         errf = fopen(errfile, "a");
         fprintf(errf, "%s\t", name);
         fflush(errf);
         fprintf(errf, "%" PRIu64 "\t", UNIXTIME);
         fprintf(errf, "%u\t", CPU);
         fprintf(errf, "%s\t", prefix);
         fprintf(errf, "%d\t%d\t", UNIT, DEV);
         fprintf(errf, "%.6f\t", (corr.corrtime*256.)/(5000.*1000000.));
         fprintf(errf, "%u\t", corr.Ierr);
         fprintf(errf, "%u\t", corr.Qerr);
         fprintf(errf, "%u\t", abs((corr.Ihi+corr.Ilo)-corr.II[0]));
         fprintf(errf, "%u\n", abs((corr.Qhi+corr.Qlo)-corr.QQ[0]));
         fclose(errf);
      }

      fprintf(fout, "ETAQ\t%.3f\n", 1/sqrt(P_I*P_Q));
   
      //Print in counts per second (assuming 5000 MHz sampling freq)
      for(int i=0; i<2*N; i++){
         fprintf(fout, "%d\t%lf\n", (5000*i)/(2*N), (5000.*1e6)/(corr.corrtime*256.) * sqrt(P_I*P_Q) * sqrt(fabs(spec[specA].out[i][0]*(-1*spec[specA].out[i][1]))));
      }
      fclose(fout); //close single spectra file
		    
		  
      double array[512];
      for(int i=0; i<512; i++){
         array[i] = (5000.*1e6)/(corr.corrtime*256.) * sqrt(P_I*P_Q) * sqrt(fabs(spec[specA].out[i][0]*(-1*spec[specA].out[i][1])));
      }


      // Let's try out CFITSIO!
      append_to_fits_table("tablefile.fits", array, sizeof(array) / sizeof(array[0]));


      free(corr.II);    //free all mallocs
      free(corr.QI);
      free(corr.IQ);
      free(corr.QQ);
      free(Rn);
      free(Rn2);
   }


//Py_INCREF(pArgs1);
//Py_INCREF(pValue);

//Py_INCREF(pListII);
//Py_INCREF(pListIQ);
//Py_INCREF(pListQI);
//Py_INCREF(pListQQ);

//Py_INCREF(pValueII);
//Py_INCREF(pValueQI);
//Py_INCREF(pValueIQ);
//Py_INCREF(pValueQQ);

/////////////////////////////  LOOP OVER ALL SPECTRA IN FILE  ///////////////////////////////////
   
      fclose(fp);   //close input file
		    
      //ouput stats for last spectra in file
      printf("\nUNIXTIME is %" PRIu64 "\n", UNIXTIME);
      printf("CORRTIME is %.6f\n", (corr.corrtime*256.)/(5000.*1000000.));
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
      printf("The cal  is from scanID: %d\n", influxReturn.scanID);
      printf("The data is from scanID: %d\n", scanID);
      if( influxReturn.scanID==0 ){
        printf("######################## ERROR ###########################\n");
        printf("#                                                        #\n");
        printf("#           Error, calibration was no good!              #\n");
        printf("#                                                        #\n");
        printf("######################## ERROR ###########################\n");
      }

      //timing
      gettimeofday(&end, 0);
      int seconds = end.tv_sec - begin.tv_sec;
      int microseconds = end.tv_usec - begin.tv_usec;
      double elapsed = seconds + microseconds*1e-6;
      printf("AVG FFTW %.1f ms in %d spectra\n\n", 1000.*elapsed/(sz/bps), sz/bps);
      fflush(stdout);
   
}







