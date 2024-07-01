import glob
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits

# Function to extract column data from the binary table extension
def get_column_data(fits_file, column_names):
    try:
        with fits.open(fits_file) as hdul:
            # Assuming the binary table extension is named 'DATA_TABLE'
            data = hdul['DATA_TABLE'].data
            column_data = [data[column_name] for column_name in column_names]
            return column_data
    except Exception as e:
        print(f"Error reading {fits_file}: {e}")
        return [None, None]

# Directory containing the FITS files
directory = "./"
# Glob pattern to find all FITS files
fits_files = glob.glob(f"{directory}/*.fits")

# The column names you want to plot (X and Y axes)
x_column_name = 'UNIXTIME'
y_column_name = 'THOT'

# Extract column data from all FITS files
all_x_data = []
all_y_data = []
for fits_file in fits_files:
    x_data, y_data = get_column_data(fits_file, [x_column_name, y_column_name])
    if x_data is not None and y_data is not None:
        all_x_data.append(x_data)
        all_y_data.append(y_data)

# Concatenate all column data
all_x_data = np.concatenate(all_x_data)
all_y_data = np.concatenate(all_y_data)

# Plot the column data
plt.figure(figsize=(10, 6))
plt.plot(all_x_data, all_y_data, 'b.', label=f'{y_column_name} vs {x_column_name}')
plt.xlabel(x_column_name)
plt.ylabel(y_column_name)
plt.ylim((270, 300))
plt.title(f'{y_column_name} vs {x_column_name} from DATA_TABLE of FITS Files')
plt.legend()
plt.grid()
plt.show()

