#!/bin/bash

# Set the directory path
directory_path="/home/young/Desktop/GUSTO-DATA"

# Check if the directory exists
if [ ! -d "$directory_path" ]; then
    echo "Error: Directory not found."
    exit 1
fi

# Change to the specified directory
cd "$directory_path" || exit 1

# Iterate over files in the directory
for file in series_????_????-2.*; do
    # Check if the item is a file
    if [ -f "$file" ]; then
        # Extract the file extension
        basename=$file;
        extension=
        while [[ $basename = ?*.* ]]
        do
          extension=${basename##*.}.$extension
          basename=${basename%.*}
        done
        extension=${extension%.}

        # Extract the existing numbers from the filename
        existing_numbers="${basename#series_}"
        number1="${existing_numbers%%_*}"
        number2="${existing_numbers#*_}"

        # Zero pad the existing numbers
        number1_padded=$(printf "%05d" "$number1")
        number2_padded=$(printf "%05d" "$number2")

        # Create the new filename with zero-padded numbers
        new_filename="series_${number1_padded}_${number2_padded}.${extension}"

        # Rename the file
        mv "$file" "$new_filename"

        echo "Renamed: $file to $new_filename"
    fi
done

echo "Script executed successfully."

