import sys
import numpy as np
import glob
import matplotlib.pyplot as plt
from PyAstronomy import pyasl
import math as m

doDespike = True

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

    return average_second_column



def plot_subtraction_ratio(x_values, y_values, xpoint, ypoint):
    global axes

    # Plot the subtraction ratio with the first column on the x-axis
    axes[xpoint, ypoint].step(x_values, y_values)

    axes[xpoint, ypoint].set_xlim(150, 350)
    axes[xpoint, ypoint].set_ylim(-.01, .01)

    # set visibility of x-axis as False
    xax = axes[xpoint, ypoint].axes.get_xaxis()
    xax = xax.set_visible(False)

    # set visibility of y-axis as False
    yax = axes[xpoint, ypoint].get_yaxis()
    yax = yax.set_visible(False)


 

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

    x_values = np.arange(0, 1024)

    i=0
    for scanID in range(start, stop+1):
        # make a glob
        srcs = "ACS3_SRC_"+str(scanID)+"_DEV4_INDX*_NINT*.txt"

        # x, y[i] spectra for [i]th spiral map pointing
        SRC[i] = read_and_average_files(srcs, n_lines_header=25)
        i+=1

    # Calculate the subtraction ratio
    for i in range(0,N):
        SRCcal[i] = (SRC[i] - SRC[24]) / SRC[24]
    
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

    i=0
    fig, axes = plt.subplots(int(m.sqrt(N)), int(m.sqrt(N)))
    # Plot the result with customized axis labels and limits
    for xpoint in range(0,int(m.sqrt(N))):
        for ypoint in range(0,int(m.sqrt(N))):
            plot_subtraction_ratio(x_values, SRCcal[i], xpoint, ypoint)
            i+=1
    plt.show()

