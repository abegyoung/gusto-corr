TARGET_CPU := $(shell uname -m)

CXX := gcc
CXXFLAGS :=


ifeq ($(TARGET_CPU), armv7l)
      INCLUDES := -I/usr/local/include -I/usr/pkg/include -I./
      LIBS := -Wl,-rpath,/usr/local/lib -lit -L/usr/pkg/lib -L/usr/local/lib -lm -lfftw3 -DUSE_INOTIFY

else ifeq ($(TARGET_CPU), x86_64)
      INCLUDES := -I/opt/local/include -I/opt/local/include -I./
      LIBS := -Wl,-rpath,/opt/local/lib -lit -L/opt/local/lib -lm -lfftw3 -lfswatch -DUSE_FSWATCH

else
      $(error unknown target_cpu)

endif

corrspec: corrspec.c
	$(CXX) -o corrspec corrspec.c $(INCLUDES) $(CXXFLAGS) $(LIBS)

all: corrspec

clean:
	rm corrspec

