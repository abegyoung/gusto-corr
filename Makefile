KERNEL := $(shell uname -s)

CXX := gcc
CFLAGS := -g

ifeq ($(KERNEL), Linux)
      INCLUDES := -I/usr/include -I/usr/local/include -I/usr/pkg/include -I./ -I/usr/include/python3.10
      LIBS := -Wl,-rpath,/usr/local/lib -lit -L/usr/pkg/lib -L/usr/local/lib -lm -lfftw3 -lcurl -lpython3.10 -lcfitsio -lc -lrt

else ifeq ($(KERNEL), Darwin)
      INCLUDES := -I/opt/local/include -I/opt/local/include -I./ -I/usr/include/python3.10
      LIBS := -Wl,-rpath,/opt/local/lib -lit -L/opt/local/lib -lm -lfftw3 -lfswatch -lcurl -lpython3.10 -lc

else
      $(error unknown kernel)

endif

corrspec: corrspec.c corrspec.h callback.c callback.h influx.c influx.h search_glob.c
	$(CXX) -c callback.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -c corrspec.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -c influx.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -c search_glob.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -o corrspec corrspec.o callback.o influx.o search_glob.o $(INCLUDES) $(CFLAGS) $(LIBS)

influx_reader: influx_reader.c influx.c influx.h
	$(CXX) -c influx_reader.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -c influx.c $(INCLUDES) $(CFLAGS) $(LIBS)
	$(CXX) -o influx_reader influx_reader.o influx.o $(INCLUDES) $(CFLAGS) $(LIBS)

all: corrspec influx_reader

clean:
	rm corrspec influx_reader *.o

