
// main.c
#include <unistd.h>
#include <sys/time.h>
#include <time.h>
#include <stdio.h>
#include <inttypes.h>
#include <stdlib.h>
#include <inttypes.h>
#include <string.h>
#include <arpa/inet.h>
#include "corrspec.h"
#include "callback.h"
#include "search_glob.h"
#include <glob.h>
#include <Python.h>
#include <stdbool.h>

#include <signal.h>
#include <errno.h>
#include <sys/mman.h>

#define handle_error(msg) \
	do { perror(msg); exit(EXIT_FAILURE); } while (0)

struct Spectrum spec[4];
PyObject *pName, *pModule;
PyObject *pFunc1, *pFunc2;

struct RefDestination
{
   int scanID1;
   int scanID2;
   int scanID3;
   int scanID4;
};

struct RefDestination find_REF_destination(glob_t glob_result, int)
{
	struct RefDestination destination;

	destination.scanID1 = 1;
	destination.scanID2 = 2;
	destination.scanID3 = 3;
	destination.scanID4 = 4;

	return destination;
}


static void handler(int sig, siginfo_t *si, void *unused)
{
   printf("Got SIGSEGV at address: 0x%lx\n", (long) si->si_addr);
   printf("Gracefully exiting\n");
   sleep(3);

   // close wenv connection to avoid many spawned Python.exe processes
   Py_DECREF(pFunc1);
   Py_DECREF(pFunc2);
   Py_DECREF(pModule);
   Py_DECREF(pName);
   Py_Finalize();

   // Send email notification via perl script if run > 1hr AND completed succesfully
   // 
}

int main(int argc, char **argv) {

   int isREFHOT = 0;
   struct RefDestination destination;
   glob_t glob_result;

   // Set up SIGSEGV handler
   struct sigaction sa;
   sa.sa_flags = SA_SIGINFO;
   sigemptyset(&sa.sa_mask);
   sa.sa_sigaction = handler;
   if (sigaction(SIGSEGV, &sa, NULL) == -1)
	   handle_error("sigaction");


   // Set up the Python C Extensions here (Used in callback() function in callback.c
   putenv("PYTHONPATH=./");

   // Initialize the Python interpreter
   Py_Initialize();

   // Build the name object for both functions from callQC.py file
   pName = PyUnicode_FromString("callQC");

   // Load the module object
   pModule = PyImport_Import(pName);

   // Get the two functions from the module
   if (pModule != NULL){
      pFunc1 = PyObject_GetAttrString(pModule, "relpower");
      pFunc2 = PyObject_GetAttrString(pModule, "qc");
   } else {
	   PyErr_Print();
	   fprintf(stderr, "Failed to load the Python module in main()\n");
   }


   // Setup all possible FFTW array lengths
   printf("readying fft\n");
   for(int i=0; i<4; i++){
     int N=(i+1)*128;
     spec[i].in  = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].out = (fftw_complex *) fftw_malloc((4*N-1) *  sizeof(fftw_complex));
     spec[i].p = fftw_plan_dft_1d((4*N-1), spec[i].in, spec[i].out, FFTW_FORWARD, FFTW_PATIENT|FFTW_PRESERVE_INPUT);
   }
   fftw_import_system_wisdom();
   printf("ready to start\n");


   // Get a list of ALL data files in a directory.  Only use for yes/no process and isREFHOT?
   if(glob("ACS*_*_*_*.dat", GLOB_ERR, NULL, &glob_result) != 0){
      perror("Error in glob\n");
      return 1;
   }


   char *filename = malloc(23*sizeof(char));
   const char *prefix_names[]={"HOT", "OTF", "REF"};

   int unit = atoi(argv[1]);
   int start_scanID = atoi(argv[2]);
   int stop_scanID = atoi(argv[3]);
   // Make a list of files to process
   for (int scanid=start_scanID; scanid<=stop_scanID; scanid++){
      for(int subscan=0; subscan<100; subscan++){
         for(int type=0; type<3; type++){
            sprintf(filename, "ACS%d_%s_%05d_%04d.dat", unit, prefix_names[type], scanid, subscan);
	    filename[23] = '\0';

            if (file_exists(filename)) {
               // Process each file
               printf("processing file: %s\n", filename);

               // Is the file a REF HOT?
               if ( search_glob_results(glob_result, scanid) && (type==0) )	// check scanID for "REF"
                  isREFHOT = 1;
               printf("isREFHOT? %d\n", isREFHOT);

	       destination = find_REF_destination(glob_result, scanid);
	       printf("Ref destination 1 = %d\n", destination.scanID1);
	       printf("Ref destination 2 = %d\n", destination.scanID2);
	       printf("Ref destination 3 = %d\n", destination.scanID3);
	       printf("Ref destination 4 = %d\n", destination.scanID4);

               // Send file to be processed
               //callback(filename, isREFHOT, destination);  // for REF and REFHOT, suggest fitsfile scanID
               callback(filename, isREFHOT);

               // reset vars
               isREFHOT = 0;
            }
         }
      }
   }

   // Clean up Python calls
   Py_DECREF(pFunc1);
   Py_DECREF(pFunc2);

   Py_DECREF(pModule);
   Py_DECREF(pName);
   Py_Finalize();

   // Send email notification via perl script if run > 1hr AND completed succesfully


   return 0;
}

