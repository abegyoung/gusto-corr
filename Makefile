KERNEL := $(shell uname -s)

CXX := gcc
CFLAGS := -g -pg

FSFLAG=0

ifeq ($(FSFLAG), 0)
  CFLAGS += -DNO_FS
endif
ifeq ($(FSFLAG), 1)
  CFLAGS += -DUSE_INOTIFY
endif
ifeq ($(FSFLAG), 2)
  CFLAGS += -DUSE_FSWATCH
endif

ifeq ($(KERNEL), Linux)
      INCLUDES := -I/usr/local/include -I/usr/pkg/include -I./ -I/usr/include/python3.10
      LIBS := -Wl,-rpath,/usr/local/lib -lit -L/usr/pkg/lib -L/usr/local/lib -lm -lfftw3 -lcurl -lpython3.10 -lcfitsio

else ifeq ($(KERNEL), Darwin)
      INCLUDES := -I/opt/local/include -I/opt/local/include -I./ -I/usr/include/python3.10
      LIBS := -Wl,-rpath,/opt/local/lib -lit -L/opt/local/lib -lm -lfftw3 -lfswatch -lcurl -lpython3.10

else
      $(error unknown kernel)

endif

corrspec: corrspec.c corrspec.h callback.c callback.h influx.c influx.h
	$(CXX) -c callback.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -c corrspec.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -c influx.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -o corrspec corrspec.o callback.o influx.o $(INCLUDES) $(CFLAGS) $(LIBS)

all: corrspec

clean:
	rm corrspec *.o

