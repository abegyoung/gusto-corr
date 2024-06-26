#!/bin/bash
start=$1
end=$2

echo $1
echo $2

for file in series_[0-9][0-9][0-9][0-9][0-9]_*;
do [[ "$file" =~ series_([0-9]{5})_.* && $((10#${BASH_REMATCH[1]})) \
	-ge $((10#$start)) && $((10#${BASH_REMATCH[1]})) -le $((10#$end)) && -e "$file" ]] && \
		   tar xf  "$file" --wildcards --no-anchored 'ACS3*' ;done


