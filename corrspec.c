
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
#include <glob.h>
#include <Python.h>

#include <signal.h>
#include <errno.h>
#include <sys/mman.h>

#define handle_error(msg) \
	do { perror(msg); exit(EXIT_FAILURE); } while (0)

struct Spectrum spec[4];
PyObject *pName, *pModule;
PyObject *pFunc1, *pFunc2;

static void handler(int sig, siginfo_t *si, void *unused)
{
   printf("Got SIGSEGV at address: 0x%lx\n", (long) si->si_addr);
   printf("Gracefully exiting\n");

   // close wenv connection
   Py_DECREF(pFunc1);
   Py_DECREF(pFunc2);
   Py_DECREF(pModule);
   Py_DECREF(pName);
   Py_Finalize();

}

int main(int argc, char **argv) {

/*
   // Set up SIGSEGV handler
   struct sigaction sa;
   sa.sa_flags = SA_SIGINFO;
   sigemptyset(&sa.sa_mask);
   sa.sa_sigaction = handler;
   if (sigaction(SIGSEGV, &sa, NULL) == -1)
	   handle_error("sigaction");
*/

   // Set up the Python C Extensions here (Used in callback() function in callback.c
   putenv("PYTHONPATH=./");

   // Initialize the Python interpreter
   Py_Initialize();

   // common to both functions

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


   void *data;

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

   /* Initialize either fswatch or inotify */

#ifdef USE_FSWATCH
   // Set the directory to monitor
   const char *directory = argv[1];

   int flag = 1<<9;
   struct fsw_event_type_filter cevent_filter;

   // Initialize the session
   fsw_init_library();

   FSW_HANDLE fsw_handle = fsw_init_session(fsevents_monitor_type);      //MacOSX
   //FSW_HANDLE fsw_handle = fsw_init_session(inotify_monitor_type);     //Linux
   //FSW_HANDLE fsw_handle = fsw_init_session(kqueue_monitor_type);      //BSD

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



#if USE_INOTIFY
   // Set the directory to monitor
   const char *directory = argv[1];


   char buffer[EVENT_BUF_LEN];
   int fd = inotify_init();
   int wd = inotify_add_watch(fd, directory, IN_MOVED_TO|IN_CLOSE_WRITE);

   while(1){
      int length = read(fd, buffer, EVENT_BUF_LEN);
      struct inotify_event *event = (struct inotify_event *) &buffer;
      callback(event, directory);
   }

#endif

#ifdef NO_FS

   glob_t glob_result;

   if(glob(argv[1], GLOB_NOSORT, NULL, &glob_result) != 0){
      perror("Error in glob\n");
      return 1;
   }

   for (size_t i=0; i < glob_result.gl_pathc; ++i){
      // Process each file
      printf("processing file: %s\n", glob_result.gl_pathv[i]);
      callback( glob_result.gl_pathv[i]);

   }

#endif

   // Clean up Python calls
Py_DECREF(pFunc1);
Py_DECREF(pFunc2);

Py_DECREF(pModule);
Py_DECREF(pName);
Py_Finalize();

   return 0;
}

