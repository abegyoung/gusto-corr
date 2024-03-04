KERNEL := $(shell uname -s)

CXX := gcc
CXXFLAGS :=


ifeq ($(KERNEL), Linux)
      INCLUDES := -I/usr/local/include -I/usr/pkg/include -I./
      LIBS := -Wl,-rpath,/usr/local/lib -lit -L/usr/pkg/lib -L/usr/local/lib -lm -lfftw3 -DUSE_INOTIFY -lcurl

else ifeq ($(KERNEL), Darwin)
      INCLUDES := -I/opt/local/include -I/opt/local/include -I./
      LIBS := -Wl,-rpath,/opt/local/lib -lit -L/opt/local/lib -lm -lfftw3 -lfswatch -DUSE_FSWATCH -lcurl

else
      $(error unknown kernel)

endif

corrspec: corrspec.c corrspec.h callback.c callback.h
	$(CXX) -c callback.c $(INCLUDES) $(CXXFLAGS) $(LIBS)
	$(CXX) -c corrspec.c $(INCLUDES) $(CXXFLAGS) $(LIBS)
	$(CXX) -c influx.c $(INCLUDES) $(CXXFLAGS) $(LIBS)
	$(CXX) -o corrspec corrspec.o callback.o influx.o $(INCLUDES) $(CXXFLAGS) $(LIBS)

corrspec-nofs: corrspec-nofs.c corrspec-nofs.h callback.c callback.h
	$(CXX) -c callback.c $(INCLUDES) $(CXXFLAGS) $(LIBS) -DNO_FS
	$(CXX) -c corrspec-nofs.c $(INCLUDES) $(CXXFLAGS) $(LIBS) -DNO_FS
	$(CXX) -c influx.c $(INCLUDES) $(CXXFLAGS) $(LIBS)
	$(CXX) -o corrspec-nofs corrspec-nofs.o callback.o influx.o $(INCLUDES) $(CXXFLAGS) $(LIBS) -DNO_FS

all: corrspec corrspec-nofs

clean:
	rm corrspec corrspec-nofs *.o

