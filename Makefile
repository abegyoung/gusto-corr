CXX := gcc
CXXFLAGS :=
INCLUDES := -I/opt/local/include -I/opt/local/include -I./
LIBS := -Wl,-rpath,/opt/local/lib -lit -L/opt/local/lib -lm -lfftw3 -lfswatch -DUSE_FSWATCH

corrspec: corrspec.c
	$(CXX) -o corrspec corrspec.c $(INCLUDES) $(CXXFLAGS) $(LIBS)

all: corrspec

clean:
	rm corrspec
