
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


struct Spectrum spec[4];

int main(int argc, char **argv) {

   
   void *data;

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

   /* Initialize either fswatch or inotify */

#ifdef USE_FSWATCH
   int flag = 1<<6;
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



#ifdef USE_INOTIFY

   char buffer[EVENT_BUF_LEN];
   int fd = inotify_init();
   int wd = inotify_add_watch(fd, directory, IN_MOVED_TO|IN_CLOSE_WRITE);

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

