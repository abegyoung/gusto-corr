corrspec: corrspec.c
	gcc -o corrspec corrspec.c -g -I./ -I/usr/include -I/opt/local/include -I/usr/include/arm-linux-gnueabihf -L./ -L/opt/local/lib -lm -lc -lfftw3 -lit -lfswatch -DUSE_FSWATCH

all: corrspec
