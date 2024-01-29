import sys
import numpy as np
import glob
import matplotlib.pyplot as plt
from PyAstronomy import pyasl
import math as m

doDespike = True

def create_spiral_index(size):
    # Initialize variables for the center and current index
    center = size // 2
    current_index = 0

    # Initialize a list to store the (i, j) position indices
    spiral_index = []

    # Nested for loop to traverse the map in a spiral pattern
    for i in range(size // 2 + 1):
        for j in range(center - i, center + i + 1):
            spiral_index.append((i, j))
            current_index += 1

        for j in range(center - i + 1, center + i + 1):
            spiral_index.append((j, size - 1 - i))
            current_index += 1

        for j in range(center + i - 1, center - i - 1, -1):
            spiral_index.append((size - 1 - i, j))
            current_index += 1

        for j in range(center + i - 1, center - i, -1):
            spiral_index.append((j, i))
            current_index += 1

    return spiral_index

# Display the 1D index containing tuples with (i, j) position indices
spiral_index = create_spiral_index(5)

def read_and_average_files(file_pattern, n_lines_header=0):
    # Get a list of files that match the specified pattern
    files = glob.glob(file_pattern)

    if not files:
        print(f"No files found matching the pattern: {file_pattern}")
        return None

    # Initialize lists to store first and second columns
    all_first_columns = []
    valid_second_columns = []

    i=0
    for file in files:
        # Read the data from the text file, skipping the specified number of header lines
        data = np.loadtxt(file, skiprows=n_lines_header)

        # Extract the first and second columns
        first_column = data[:, 0]
        second_column = data[:, 1]

        # Check if all values in the second column are zero or NaN
        if not (np.all(second_column == 0) or np.any(np.isnan(second_column))):
            all_first_columns.append(first_column)
            valid_second_columns.append(second_column)

    if not valid_second_columns:
        print("All second columns are zero or contain NaN values. No valid data for averaging.")
        return None

    # Convert the lists of arrays to NumPy arrays
    all_first_columns = np.array(all_first_columns)
    valid_second_columns = np.array(valid_second_columns)

    # Calculate the average along the rows (axis=0)
    average_first_column = np.mean(all_first_columns, axis=0)
    average_second_column = np.nanmean(valid_second_columns, axis=0)

    return average_first_column, average_second_column



def plot_subtraction_ratio(x_values, y_values, xpoint, ypoint, indx):
    global axes

    # Plot the subtraction ratio with the first column on the x-axis
    axes[xpoint, ypoint].step(x_values, y_values)
    a = plt.gca()

    axes[xpoint, ypoint].set_xlim(600, 1500)
    axes[xpoint, ypoint].set_ylim(-.005, .005)

    # set visibility of x-axis as False
    xax = axes[xpoint, ypoint].axes.get_xaxis()
    xax = xax.set_visible(False)

    # set visibility of y-axis as False
    yax = axes[xpoint, ypoint].get_yaxis()
    yax = yax.set_visible(False)

#    plt.text(0,6, 0.8, "{:02d}".format(int(indx)))


 

if __name__ == "__main__":
    # Check if the correct number of command-line arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python script_name.py file_pattern1 file_pattern2")
        sys.exit(1)

    global fig
    global axes

    # Get file patterns from command-line arguments
    start = int(sys.argv[1])
    stop  = int(sys.argv[2])
    N = stop - start + 1
    SRC    = np.zeros((N,1024))
    SRCcal = np.zeros((N,1024))

    x_values = np.zeros(1024)

    if N==25:
        # 5x5
        spiral_index = [[2,2],  [2,3],  [1,3],  [1,2],  [1,1],  [2,1],  [3,1],  [3,2],  [3,3],  [3,4],  [2,4],  [1,4],  [0,4],  [0,3],  [0,2],  [0,1],  [0,0],  [1,0],  [2,0],  [3,0],  [4,0],  [4,1],  [4,2],  [4,3],  [4,4]]
    elif N==9:
        # 3x3
        spiral_index = [[1,1],  [1,2],  [0,2],  [0,1],  [0,0],  [1,0],  [2,0],  [2,1],  [2,2],]



    i=0
    for scanID in range(start, stop+1):
        # make a glob
        srcs = "ACS3_SRC_"+str(scanID)+"_DEV4_INDX*_NINT*.txt"

        # x, y[i] spectra for [i]th spiral map pointing
        x_values, SRC[i] = read_and_average_files(srcs, n_lines_header=25)
        i+=1

    # Calculate the subtraction ratio
    for i in range(0,N):
        SRCcal[i] = (SRC[i] - SRC[3]) / SRC[3]
    
        # despike
        newspec = []
        if doDespike == True:
            mask = np.zeros(len(SRCcal[i]), dtype=bool)
            r = pyasl.pointDistGESD(SRCcal[i], maxOLs=20, alpha=5)

            mask[r[1]] = 1
            newspec = np.ma.masked_array(SRCcal[i], mask)

        else:
            newspec = SRCcal[i] 
        SRCcal[i] = newspec

        # DC offset
        SRCcal[i] = SRCcal[i] - np.mean(SRCcal[i])

    i=0
    fig, axes = plt.subplots(int(m.sqrt(N)), int(m.sqrt(N)))
    # Plot the result with customized axis labels and limits
    for indx in range(0, N):
      xpoint = spiral_index[indx][0]
      ypoint = spiral_index[indx][1]
      plot_subtraction_ratio(x_values, SRCcal[indx], xpoint, ypoint, int(indx))
    plt.show()

