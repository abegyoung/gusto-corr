corrspec: corrspec.c
	gcc -o corrspec corrspec.c -L./ -I./ -L/opt/local/lib -I/opt/local/include -ldict -lm -l fftw3 -lm -lit -ldict -lc -lfswatch

dict: dict.c
	gcc -c dict.c -I./
	ar r libdict.a dict.o
	ranlib libdict.a
 
all: corrspec dict

clean:
	rm corrspec
	rm dict.o
	rm libdict.a
