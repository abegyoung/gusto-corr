#ifdef USE_FSWATCH

   #include <libfswatch/c/libfswatch.h>

   void const callback(const fsw_cevent *events, const unsigned int event_num, void * data);

   int flag = 0;//1<<2;

   struct fsw_event_type_filter cevent_filter;

#endif

#ifdef USE_INOTIFY

   #define EVENT_SIZE (sizeof (struct inotify_event))
   #define EVENT_BUF_LEN (1024*(EVENT_SIZE+16))

   #include <sys/inotify.h>
   void const callback(struct inotify_event *event, const char *directory);

#endif
      


