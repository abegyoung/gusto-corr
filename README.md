# README for the gusto-corr repository

Omnisys correlator prototype software

A series of Python 3 scripts is included to initialize, calibrate, and read data from a correlator.

Optionally C code for `corrspec` to watch for lag files delivered by NFS or TFTP and FFT's of the lags done for spectra output.  This relies on either inotify or fswatch.

## Prerequisites:
### libiT Information Theory C library
Provides a C library for access to the inverse error function erfinv( ) which takes the Hi and Lo count values as inputs to the P_I and P_Q power scaling factors along with the DAC Voltage settings.

libit.sourceforge.net/index.html

Installation of the library  is to download libit-0.2.3 from sourceforge and install where the FFT of the lags will be done.

Fix some things

1) in src/convcode.c:53, fls=>fls2, as well as name changed through.  Todo: make a patch for this, or even better fix it and use the one in strings.h if possible.

To install on OS X:
```
./configure --target=x86_64 --prefix=/opt/local
make
make install
```
Assuming you've installed libit in a local library directory, add that to the corrspec Makefile.

### fftw-3
FFTW is used to perform the FFT of lags to spectra.  Installation from either a debian or Macports repository is adequate.
Mac:
```
sudo port install fftw-3
```

### Optional: inotify is not available in OS X, so fswatch is complied as an option to corrspec

Getting fswatch
---------------

A regular user may be able to fetch `fswatch` from the package manager of your
OS or a third-party one.  If you are looking for `fswatch` for macOS, you can
install it using either [MacPorts] or [Homebrew]:

```
# MacPorts
$ port install fswatch

# Homebrew
$ brew install fswatch
```

On FreeBSD, `fswatch` can be installed using [pkg]:

```console
# pkg install fswatch-mon
```


### InfluxDB
InfluxDB is a time series database which handles precisely timed writes with high loads, perfect for an observatory continually writing time-stamped observations at a high rate.  InfluxDB OSS is a free Open Source version of the product.

There are a few choices for the Influx Database install.  Mostly old style V1.8 which we run on the GUSTO instrument because its the last version which is 32-bit compatible, or V2.0 and above which are incompatible but produce nice web interface graphs.  You may recreate on the ground the flight database in either version, however the corrspec code uses the V1.8 query interface.

You may find the Influx DB install at: https://docs.influxdata.com/influxdb/v1/introduction/download/

Click the link and follow the instructions to download Influx V1.8 for Mac, Linux, or *shudder* Windows PowerShell.

Once installed, edit the config file to allow an infinite number of series instead of the default one million by setting:

```
[data]
  max-series-per-database = 0
```

Starting with a blank canvas, import the first 28 days of GUSTO with the portable format from soral: `influx_gustoDBlp_backup.tar.gz`.  Untarred, this will create a directory `backup`.  Also get the compressed binary format export from Jan28 - Feb 26: `export_v18_18-01-2024.dat`

Start influxd from the command line using ``sudo influxd``, then issue:
```
young@Abrams-MBP ~ % sudo influxd restore -portable ./backup
young@Abrams-MBP ~ % influx -database 'gustoDBlp' -host 'localhost' -port '8086' -compressed -import -path Desktop/export_v18_02_26_2024.dat
```

This should have created a new database, and imported the compressed binary exports from the gondola.  You should now have a gustoDBlp and a gustoDBlp2.  Merging these two databases is trivial with a SELECT INTO.

From the influx command line
```
SELECT * INTO "gustoDBlp"."autogen".:MEASUREMENT FROM "gustoDBlp2"."autogen"./.*/ WHERE time > now() - 2w AND time < now() - 1w GROUP BY *
```

You'll need to process about a week at a time using ``WHERE time > now()`` blocks so as not to run out of memory.


###
findIF.sh

An ICE config variable called ``firstIF`` was set by the observer whenever GUSTO tracked a new region of the Sky.  For example G333 which was done very early on used 900 MHz as the zero velocity based on the regions VLSR and our own velocity.

A somewhat edited ICEobs.log is fed to ``findIF.sh`` and the target names compared to GUSTO.cat which has the VLSR for each target.

A file is produced with B1 and B2 frequency in MHz which corresponds to zero doppler shift velocity releative to VLSR, the first scanID which uses the new synthesizer tuning, and the target name.

IF and scanID may then be read into InfluxDB for automated emission line intensities.

example:
```
1900    1900    27704   RCW120
1900    1900    27718   G002
1100    1100    27883   RCW120
1100    1100    27897   G334
1100    1100    27969   G334
1300    1300    28060   LMC
1900    1900    28169   RCW120
1900    1900    28183   G002
1100    1100    28233   G334
```


### corrspec
To compile `corrspec`

```
make dict
make corrspec
```

## Using corrspec
To test FFT functionality, build with either fswatch or inotify.

Run in the current directory and update the watched file out.lags by copying from the data directory into the currently watched directory.

```
./corrspec
```
In another window:
```
cp data/out.lags .
```
or use a ``touch file`` to modify the file Attributes triggering the file system watcher to begin processing the file.

Output:
```
young@Abrams-MacBook-Pro gusto-corr % ./corrspec 
UNIXTIME is 2023-04-03_21:38:32.108
0.00 0.00 0.00 0.00
nlags=128
etaQ 423.554
Hash table 1.6 ms
FFTW 1.3 ms

UNIXTIME is 2023-04-03_21:38:32.108
0.00 0.00 0.00 0.00
nlags=128
etaQ 423.554
Hash table 1.4 ms
FFTW 1.5 ms
```
The `corrspec` binary notices the file has changed, reads it, automatically determines the length of the lags, and runs the corresponding FFTW (128, 256, 384, or 512) and outputs the spectra to `out.spec`.  Performance data is printed to the terminal where the program is run from.

Tests on gusto-data compiled with inotify result in slightly longer FFT times:

```
young@gusto-data:~/gusto-corr$ ./corrspec 
UNIXTIME is 2023-04-03_21:38:32.108
intTime is 250.0 msec
0.00 0.00 0.00 0.00
nlags=128
etaQ 423.554
Hash table 5.9 ms
FFTW 14.9 ms

UNIXTIME is 2023-04-03_21:38:32.108
intTime is 250.0 msec
0.00 0.00 0.00 0.00
nlags=128
etaQ 423.554
Hash table 5.7 ms
FFTW 13.5 ms
```
YMMV
