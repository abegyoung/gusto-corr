corrspec: corrspec.c
	gcc -o corrspec corrspec.c -I./ -I/usr/include -I/opt/local/include -I/usr/include/arm-linux-gnueabihf -L./ -L/opt/local/lib -lm -lc -lfftw3 -lit -ldict -lfswatch

dict: dict.c
	gcc -c dict.c -I./
	ar r libdict.a dict.o
	ranlib libdict.a
 
all: corrspec dict

clean:
	rm corrspec
	rm dict.o
	rm libdict.a
