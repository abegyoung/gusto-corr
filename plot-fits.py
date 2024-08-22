import glob
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
import gc

# Function to extract column data from the binary table extension
def get_column_data(fits_file, column_names, mixer):
    x_column_name, y_column_name = column_names
    try:
        with fits.open(fits_file, memmap=True) as hdul:
            # Assuming the binary table extension is named 'DATA_TABLE'
            data = hdul['DATA_TABLE'].data
            # Applf filter condition for dev
            mask = data['MIXER'] == mixer
            #column_data = [data[column_name] for column_name in column_names]
            x_data = data[x_column_name][mask]
            y_data = data[y_column_name][mask]
            #return column_data
            return x_data, y_data
    except Exception as e:
        print(f"Error reading {fits_file}: {e}")
        return [None, None]

# Directory containing the FITS files
directory = "./"
# Glob pattern to find all FITS files
fits_files = glob.glob(f"{directory}/*.fits")

# The column names and mixer you want to plot (X and Y axes)
x_column_name = 'UNIXTIME'
y_column_name = 'PSat'
mixer=8

# Extract column data from all FITS files
all_x_data = []
all_y_data = []
for fits_file in fits_files:
    x_data, y_data = get_column_data(fits_file, [x_column_name, y_column_name], mixer)
    if x_data is not None and y_data is not None:
        all_x_data.extend(x_data)
        all_y_data.extend(y_data)
    gc.collect()  # Force garbage collection after each file

# Convert to numpy arrays
all_x_data = np.array(all_x_data)
all_y_data = np.array(all_y_data)

# Plot the column data
plt.figure(figsize=(10, 6))
plt.plot(all_x_data, all_y_data, 'b.', label=f'{y_column_name} vs {x_column_name}')
plt.xlabel(x_column_name)
plt.ylabel(y_column_name)
#plt.xlim((1706143800, 1706623600))
#plt.ylim((270, 300))
plt.title(f'{y_column_name} vs {x_column_name} from DATA_TABLE of FITS Files')
plt.legend()
plt.grid()
plt.show()

