CXX := gcc
CXXFLAGS :=
INCLUDES := -I/usr/local/include -I/usr/pkg/include
LIBS := -L/usr/pkg/lib -L/usr/local/lib -lm -lc -lfftw3 -lit -lfswatch -DUSE_FSWATCH

corrspec: corrspec.c
	$(CXX) -o corrspec corrspec.c $(INCLUDES) $(CXXFLAGS) $(LIBS)

all: corrspec
