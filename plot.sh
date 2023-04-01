#!/bin/bash
date=`grep UNIXTIME out.lags|cut -d " " -f 2`
nint=`grep NINT out.lags|cut -d " " -f 2`
fifo=`grep FIFO out.lags|cut -d " " -f 2`
unit=`grep UNIT out.lags|cut -d " " -f 2`
dev=`grep DEV  out.lags|cut -d " " -f 2`
cat out.spec|plt 0 1 -t $date -L"(Ft-b-i-P20,Cmaroon)" .85 .9 CC "NINT = $nint" -L"(Ft-b-i-P20,Cmaroon)" .85 .8 CC "FIFO = $fifo" -B 0 0 1 1 -xa 0 4500 -x MHz -y "counts/sec" -L"(Ft-b-i-P20,Cmaroon)" .85 .7 CC "UNIT= $unit" -L"(Ft-b-i-P20,Cmaroon)" .85 .6 CC "DEV= $dev"

