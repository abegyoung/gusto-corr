KERNEL := $(shell uname -s)

CXX := gcc
CXXFLAGS :=


ifeq ($(KERNEL), Linux)
      INCLUDES := -I/usr/local/include -I/usr/pkg/include -I./
      LIBS := -Wl,-rpath,/usr/local/lib -lit -L/usr/pkg/lib -L/usr/local/lib -lm -lfftw3 -DUSE_INOTIFY

else ifeq ($(KERNEL), Darwin)
      INCLUDES := -I/opt/local/include -I/opt/local/include -I./
      LIBS := -Wl,-rpath,/opt/local/lib -lit -L/opt/local/lib -lm -lfftw3 -lfswatch -DUSE_FSWATCH

else
      $(error unknown kernel)

endif

corrspec: corrspec.c corrspec.h callback.c callback.h
	$(CXX) -c callback.c $(INCLUDES) $(CXXFLAGS) $(LIBS)
	$(CXX) -c corrspec.c $(INCLUDES) $(CXXFLAGS) $(LIBS)
	$(CXX) -o corrspec corrspec.o callback.o $(INCLUDES) $(CXXFLAGS) $(LIBS)

all: corrspec

clean:
	rm corrspec *.o

