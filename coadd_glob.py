import sys
import numpy as np
import glob
import matplotlib.pyplot as plt
from PyAstronomy import pyasl

doDespike = False

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
        if not (np.std(second_column[42:62])>50000 or np.all(second_column == 0) or np.any(np.isnan(second_column))):
            all_first_columns.append(first_column)
            valid_second_columns.append(second_column)
        else:
          print("Throwing out ", file, "with stddev ", np.std(second_column[42:62]))

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


def plot_subtraction_ratio(x_values, subtraction_ratio, x_limit, y_limit):
    global num
    #my_dpi=96
    #plt.figure(figsize=(120/my_dpi, 120/my_dpi), dpi=my_dpi)

    plt.figure()

    # Plot the subtraction ratio with the first column on the x-axis
    plt.step(x_values, subtraction_ratio)
    plt.xlabel('MHz')
    plt.ylabel('(S-R) / R (+ DC offset)')
    a = plt.gca()
 
    # set visibility of x-axis as False
    xax = a.axes.get_xaxis()
 
    # set visibility of y-axis as False
    yax = a.axes.get_yaxis()

    # Set limits on the x and y axes
    plt.xlim(x_limit)
    plt.ylim(y_limit)

    plt.tight_layout()
    plt.text(0.8, 0.9, "{:02d}".format(num), transform=a.transAxes)
    plt.savefig('NGC6334-{:05}.png'.format(num))

    plt.show()



if __name__ == "__main__":
    # Check if the correct number of command-line arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python script_name.py file_pattern1 file_pattern2")
        sys.exit(1)

    # Get file patterns from command-line arguments
    file_pattern1 = sys.argv[1]
    file_pattern2 = sys.argv[2]
    global num
    num=int(file_pattern1[9:14])
    

    average_first_column1, average_second_column1 = read_and_average_files(file_pattern1, n_lines_header=25)
    average_first_column2, average_second_column2 = read_and_average_files(file_pattern2, n_lines_header=25)

    if average_second_column1 is not None and average_second_column2 is not None:
        # Use the first column as x-values
        x_values = average_first_column1

        # Calculate the subtraction ratio
        subtraction_ratio = (average_second_column1 - average_second_column2) / average_second_column2

        # Set limits on the x and y axes
        #subtraction_ratio[201:204] = subtraction_ratio[200]
        #subtraction_ratio[131:137] = subtraction_ratio[130]
        x_limit = (800, 1400)  # Replace xmin and xmax with your desired values
        y_limit = (-0.005, 0.005)
        spec = subtraction_ratio-subtraction_ratio[250]

        # despike
        newspec = []
        if doDespike == True:
          mask = np.zeros(len(spec), dtype=bool)
          r = pyasl.pointDistGESD(spec, maxOLs=20, alpha=5)
          
          mask[r[1]] = 1
          newspec = np.ma.masked_array(spec, mask)

        else:
          newspec = spec

        # Plot the result with customized axis labels and limits
        plot_subtraction_ratio(x_values, newspec, x_limit, y_limit)

