#!/bin/bash

# Define variables
LOCAL_DIR="/Users/young/Projects/GUSTO/Data/level0.95"
REMOTE_USER="obs"
REMOTE_HOST="soral.as.arizona.edu"
REMOTE_DIR="/storage/archive/GUSTO/level0.95"
START_NUM=$1 # Replace with M (e.g., 00001)
END_NUM=$2 # Replace with N (e.g., 99999)
ARCHIVE_NAME="ACS5_$START_NUM-$END_NUM.tar.gz"

START_TIME=`date +%s`

# Use tar to create an archive and send it via ssh to the remote machine
tar -czf - -C "$LOCAL_DIR" $(ls "$LOCAL_DIR" | grep -E '^ACS5_' | grep -E '.*[0-9]{5}.*' | gawk -v start="$START_NUM" -v end="$END_NUM" '
{
  # Extract the 5-digit number from the filename
  match($0, /[0-9]{5}/, arr);
  num = arr[0];
  # Check if the number is within the range
  if (num >= start && num <= end) print $0;
}') | ssh "$REMOTE_USER@$REMOTE_HOST" "cat > '$REMOTE_DIR/$ARCHIVE_NAME'"

END_TIME=`date +%s`

SIZE=`ssh "$REMOTE_USER@$REMOTE_HOST" "ls -l $REMOTE_DIR/$ARCHIVE_NAME" | cut -d " " -f 6`

RATE=`echo "scale=2;$SIZE/($END_TIME-$START_TIME)/1000000" | bc -l`

echo "Archive created and stored on remote machine: $REMOTE_HOST:$REMOTE_DIR/$ARCHIVE_NAME at $RATE MB/s"
