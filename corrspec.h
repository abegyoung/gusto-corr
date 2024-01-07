#ifdef USE_FSWATCH

   #include <libfswatch/c/libfswatch.h>

   void const callback(const fsw_cevent *events, const unsigned int event_num, void * data);

#endif

#ifdef USE_INOTIFY

   #define EVENT_SIZE (sizeof (struct inotify_event))
   #define EVENT_BUF_LEN (1024*(EVENT_SIZE+16))

   #include <sys/inotify.h>
   void const callback(struct inotify_event *event, const char *directory);

#endif
      


