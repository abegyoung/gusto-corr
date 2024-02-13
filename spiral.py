import sys
import glob
#import scipy
import argparse
import math as m
import numpy as np
import matplotlib.pyplot as plt

from photutils.centroids import centroid_2dg
from scipy.interpolate import interp2d
from PyAstronomy import pyasl

import warnings
warnings.simplefilter("ignore")


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


def calculate_centroid(x, y, z):
    # Calculate centroid using photutils.centroids.centroid_2dg
    centroid_x, centroid_y = centroid_2dg(z)

    # Print the centroid coordinates
    print(f"Centroid X: {centroid_x}")
    print(f"Centroid Y: {centroid_y}")



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
        if not (np.std(second_column[42:62])>20000 or np.all(second_column == 0) or np.any(np.isnan(second_column))):
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




def plot_subtraction_ratio(x_values, y_values, xpoint, ypoint, indx):
    global axes
    global centerIF

    # Plot the subtraction ratio with the first column on the x-axis
    axes[xpoint, ypoint].step(x_values, y_values)
    a = plt.gca()

    # set plot range
    axes[xpoint, ypoint].set_xlim(centerIF-350, centerIF+350)
    axes[xpoint, ypoint].set_ylim(-.005, .005)

    # set visibility of x-axis as False
    if(indx<6):
       xax = axes[xpoint, ypoint].axes.get_xaxis()
       xax = xax.set_visible(False)

    # set visibility of y-axis as False
    if(indx<4 or indx>6):
        yax = axes[xpoint, ypoint].get_yaxis()
        yax = yax.set_visible(False)

    # Integrate over 100 MHz
    difference_array = np.absolute(x_values-1040)
    start = difference_array.argmin()
    difference_array = np.absolute(x_values-1140)
    end= difference_array.argmin()
    
    indices = np.arange(start,end)
    integrated_flux = y_values[indices].sum()

    integrated_fluxes[xpoint][ypoint] = integrated_flux
    ''' 
    if(xpoint==1 and ypoint==1):
      integrated_flux = 0
    elif( xpoint==1 and ypoint==2):
      integrated_flux = 0
    elif( xpoint==0 and ypoint==2):
      integrated_flux = 0
    elif( xpoint==0 and ypoint==1):
      integrated_flux = 0
    elif( xpoint==0 and ypoint==0):
      integrated_flux = 9
    elif( xpoint==1 and ypoint==0):
      integrated_flux = 0
    elif( xpoint==2 and ypoint==0):
      integrated_flux = 0
    elif( xpoint==2 and ypoint==1):
      integrated_flux = 0
    elif( xpoint==2 and ypoint==2):
      integrated_flux = 0
    '''

    # set legend
    axes[xpoint][ypoint].text(0.6, 0.8, "{:.4f}".format(integrated_flux), transform=axes[xpoint][ypoint].transAxes)

    # find and plot peaks
    #peaks, _ = scipy.signal.find_peaks(y_values[123:307], height=.001, width=3)
    #try:
    #    axes[xpoint][ypoint].vlines(x_values[peaks[0]], -.002, .002)
    #except:
    #    pass


    return integrated_flux


 

if __name__ == "__main__":
    # Check if the correct number of command-line arguments is provided
    #if len(sys.argv) != 3:
    #    print("Usage: python script_name.py file_pattern1 file_pattern2")
    #    sys.exit(1)

    global fig
    global axes
    global centerIF

    centerIF=1300

    # Get file patterns from command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--despike", help="\tDespike ratioed ROI", default=True)
    parser.add_argument("-r", "--refs", help="\tSpiral was taken with REFs On", default=False)
    parser.add_argument("-S", "--start", help="\tSpiral start scanID", default=0)
    parser.add_argument("-E", "--end",   help="\tSpiral stop scanID", default=8)
    parser.add_argument("-R", "--REF",   help="\tSpiral reference scanID", default=4)

    args = parser.parse_args()

    doDespike = args.despike
    refs = args.refs

    start = int(args.start)
    stop  = int(args.end)
    ref   = int(args.REF)

    N = stop - start + 1
    SRC    = np.zeros((N,1024))
    SRCcal = np.zeros((N,1024))

    x_values = np.zeros(1024)

    if N==49:
        # 7x7
        spiral_index = [[3,3], 
                       [3,4], [2,4], [2,3], [2,2], [3,2], [4,2], [4,3], [4,4], 
                       [4,5], [3,5], [2,5], [1,5], [1,4], [1,3], [1,2], [1,1], [2,1], [3,1], [4,1], [5,1], [5,2], [5,3], [5,4], [5,5],
                       [5,6], [4,6], [3,6], [2,6], [1,6], [0,6], [0,5], [0,3], [0,2], [0,1], [0,0], [1,0], [2,0], [3,0], [4,0], [5,0], [6,0], [6,1], [6,2], [6,3], [6,4], [6,5], [6,6]]
    elif N==25:
        # 5x5
        spiral_index = [[2,2],  [2,3],  [1,3],  [1,2],  [1,1],  
                        [2,1],  [3,1],  [3,2],  [3,3],  [3,4],  
                        [2,4],  [1,4],  [0,4],  [0,3],  [0,2],  
                        [0,1],  [0,0],  [1,0],  [2,0],  [3,0],  
                        [4,0],  [4,1],  [4,2],  [4,3],  [4,4]]

    elif N==9:
        # 3x3
        spiral_index = [[1,1],  [1,2],  [0,2],  
                        [0,1],  [0,0],  [1,0],  
                        [2,0],  [2,1],  [2,2],]



    i=0
    for scanID in range(start, stop+1):
        # make a glob
        srcs = "ACS3_SRC_"+str(scanID)+"_DEV4_INDX*_NINT*.txt"

        # x, y[i] spectra for [i]th spiral map pointing
        x_values, SRC[i] = read_and_average_files(srcs, n_lines_header=25)
        i+=1


    # Should we use a recent REF?
    if ref>N:
        # make a glob
        refs = "ACS3_REF_"+str(ref)+"_DEV4_INDX*_NINT*.txt"

        x_values, REF = read_and_average_files(refs, n_lines_header=25)
    else:
        REF=[]

    # region of interest for DC offset
    difference_array = np.absolute(x_values-(centerIF+200))
    start = difference_array.argmin()
    difference_array = np.absolute(x_values-(centerIF+300))
    end= difference_array.argmin()

    # Calculate the subtraction ratio
    for i in range(0,N):
        if ref>N:
            SRCcal[i] = (SRC[i] - REF) / REF
        else:
            SRCcal[i] = (SRC[i] - SRC[ref]) / SRC[ref]

        # despike
        newspec = []
        newref  = []
        if doDespike == True:
            # despike SRC
            mask = np.zeros(len(SRCcal[i]), dtype=bool)
            r = pyasl.pointDistGESD(SRCcal[i], maxOLs=40, alpha=.5)
            mask[r[1]] = 1
            newspec = np.ma.masked_array(SRCcal[i], mask)
            # count spikes
            n=0
            for j in range(0, r[0]-1):
              if np.any(SRCcal[start:end] == r[1][j]):
                n+=1
            print(n)

            if ref>N:
                # despike REF
                refmask = np.zeros(len(REF), dtype=bool)
                refr = pyasl.pointDistGESD(REF, maxOLs=20, alpha=.5)
                refmask[refr[1]] = 1
                newref = np.ma.masked_array(REF, refmask)
        else:
            newspec = SRCcal[i] 
            newref  = REF

        SRCcal[i] = newspec
        REF = newref

        # Slope correction
        # region of interest for DC offset
        difference_array = np.absolute(x_values-(centerIF-350))
        lowerExt = difference_array.argmin()
        difference_array = np.absolute(x_values-(centerIF+350))
        upperExt = difference_array.argmin()
        slope = (SRCcal[i][upperExt] - SRCcal[i][lowerExt]) / (upperExt-lowerExt)
        for j in range(lowerExt,upperExt):
            SRCcal[i][j] = SRCcal[i][j] - slope*j

        # DC offset
        SRCcal[i] = SRCcal[i] - np.mean(SRCcal[i][start:end])


    # set up for centroid
    AZ = np.arange( 270, 391,  60)
    EL = np.arange(-650 -771, -60)
    AZ_data, EL_data = np.meshgrid(AZ, EL)
    integrated_fluxes = np.zeros((int(m.sqrt(N)), int(m.sqrt(N))))
        
              

    i=0
    fig, axes = plt.subplots(int(m.sqrt(N)), int(m.sqrt(N)))
    # Plot the result with customized axis labels and limits
    for indx in range(0, N):
      xpoint = spiral_index[indx][0]
      ypoint = spiral_index[indx][1]
      integrated_fluxes[xpoint][ypoint] = plot_subtraction_ratio(x_values, SRCcal[indx], xpoint, ypoint, int(indx))

    print(integrated_fluxes)
    cx, cy = centroid_2dg(integrated_fluxes)
    print("tAzD = {:d}".format(int(310+(cx-1)*60)))
    print("tElD = {:d}".format(int(-730-(cy-1)*60)))
    print(cx)
    print(cy)
       
    plt.setp(axes, xticks=[centerIF-350, centerIF, centerIF+350])
    plt.show()

   
