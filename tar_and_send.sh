#!/bin/bash

# Define variables
LOCAL_DIR="./"
REMOTE_USER="obs"
REMOTE_HOST="soral.as.arizona.edu"
REMOTE_DIR="/storage/archive/GUSTO/level0.7/Oct16_B1"
START_NUM=$1 # Replace with M (e.g., 00001)
END_NUM=$2 # Replace with N (e.g., 99999)
ARCHIVE_NAME="ACS5_$START_NUM-$END_NUM.tar.gz"

# Use tar to create an archive and send it via ssh to the remote machine
tar -czf - -C "$LOCAL_DIR" $(ls "$LOCAL_DIR" | grep -E '.*[0-9]{5}.*' | awk -v start="$START_NUM" -v end="$END_NUM" '
{
  # Extract the 5-digit number from the filename
  match($0, /[0-9]{5}/, arr);
  num = arr[0];
  # Check if the number is within the range
  if (num >= start && num <= end) print $0;
}') | ssh "$REMOTE_USER@$REMOTE_HOST" "cat > '$REMOTE_DIR/$ARCHIVE_NAME'"

echo "Archive created and stored on remote machine: $REMOTE_HOST:$REMOTE_DIR/$ARCHIVE_NAME"

