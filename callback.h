#include <math.h>
#include <it/math.h>
#include <fftw3.h>
#include <sys/time.h>



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



#ifdef USE_FSWATCH

   #include <libfswatch/c/libfswatch.h>

   void const callback(const fsw_cevent *events, const unsigned int event_num, void * data);
/*
0       NoOp
1<<0    PlatformSpecific
1<<1    Created
1<<2    Updated
1<<6    AttributeModified
1<<8    MovedTo
1<<9    IsFile
*/
#endif

#ifdef USE_INOTIFY

   #define EVENT_SIZE (sizeof (struct inotify_event))
   #define EVENT_BUF_LEN (1024*(EVENT_SIZE+16))

   #include <sys/inotify.h>
   void const callback(struct inotify_event *event, const char *directory);

#endif

