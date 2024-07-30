#!/bin/bash

f1=1461132000000  #rest freq in 1/s
f2=1900536900000  #rest freq in 1/s
c=299792458 #speed of light in m/s

CAT="GUSTO.cat"

while read -r line; do
    # Get line with target name
    if [[ $line != *VLSR* ]]; then
      prev2="${prev1}"
      prev1="${line}"
    fi

    if [[ $line == *VLSR* ]]; then
        ## Find the TARGET name
        TARGET=$(echo "$prev2" | awk '{print $10}')              # Target name
        VLSR=$(grep "$TARGET" GUSTO.cat | awk '{print $5*1000}') # VLSR in m/s
        VLSRkm=$(grep "$TARGET" GUSTO.cat | awk '{print $5}')    # VLSR in km/s
	date_str=$(echo "$prev2" | cut -c 1-20)                  # timedate
	epoch_sec=$(date -d "$date_str" +%s)
        gonVel=$(echo "$line" | awk '{print $8*1000}')           # gonVel in m/s
        read -r next_line

        LO1=$(echo "$next_line" | awk '{print $6}' | cut -c 2- ) #LO in MHz
        LO1=$(echo "$LO1 * 1000000" | bc)  #LO in 1/s
        read -r next_line

        LO2=$(echo "$next_line" | awk '{print $6}' | cut -c 2- ) #LO in MHz
        LO2=$(echo "$LO2 * 1000000" | bc)  #LO in 1/s
        read -r next_line
        read -r next_line
        read -r next_line

        scanID=$(echo "$next_line" | awk '{print $10}' ) #scanID

        IF1=$(echo "$f1 * (1 - 1*($VLSR+$gonVel)/$c) - $LO1*108" | bc -l) #IF in 1/s
        IF1=$(echo "$IF1 / 1000000" | bc )  #IF in MHz
        IF1=$(echo "$IF1" | awk '{print int(($1+5)/10)*10}')
        IF2=$(echo "$f2 * (1 - 1*($VLSR+$gonVel)/$c) - $LO2*144" | bc -l) #IF in 1/s
        IF2=$(echo "$IF2 / 1000000" | bc )  #IF in MHz
        IF2=$(echo "$IF1" | awk '{print int(($1+5)/10)*10}')

        #if [ bc <<< "$IF1 < 1000" ] ; then
        #    IF1=$(echo "scale=2; $IF1 * 2" | bc)
        #elif [ bc <<< "$IF1 > 3000" ] ; then
        #    IF1=$(echo "scale=2; $IF1 / 2" | bc)
        #fi
        #if [ bc <<< "$IF2 < 1000" ] ; then
        #    IF2=$(echo "scale=2; $IF2 * 2" | bc)
        #elif [ bc <<< "$IF2 > 3000" ] ; then
        #    IF2=$(echo "scale=2; $IF2 / 2" | bc)
        #fi

        if [[ $scanID != 0 && $scanID != 1 ]] ; then
          printf '%d\t%d\t%d\t%.1f\t%d\t%s\n' $epoch_sec $IF1 $IF2 $VLSRkm $scanID $TARGET
        fi
    fi
done < ICEobs.log
