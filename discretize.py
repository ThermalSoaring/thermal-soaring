#
# Usage:
#
# $ python3
# >>> from discretize import discretize
# >>> discretize('path/to/file.csv', 'path/to/output.csv', 50)
#
import csv
import numpy as np

def discretize(infile, outfile, numbins=50):
    # Read
    with open(infile, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        rows = []

        # Read all the data
        for row in reader:
            rows.append(row)

        # Delete first and last rows, the first is the header
        # and the last likely is missing some data
        header = rows[0]
        del rows[0]
        del rows[-1]

        # Discretize each column
        if len(rows) > 0:
            #assert len(rows[0]) == 25, \
            #        "Not valid data, wrong number of columns"

            np_rows = np.array(rows, dtype=np.float)
            output_rows = np.zeros(np_rows.shape, dtype=np.int)

            for i in range(0, len(rows[0])):
                #output_rows[:, i] = np.digitize(np_rows[:, i], bins)
                col = np_rows[:, i]
                minval = np.min(col)
                maxval = np.max(col)
                bins = np.linspace(minval, maxval, num=numbins, endpoint=True)

                output_rows[:, i] = np.digitize(np_rows[:, i], bins)

            # Write
            with open(outfile, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=',',
                    quotechar='"', quoting=csv.QUOTE_MINIMAL)

                writer.writerow(header)

                for row in output_rows:
                    writer.writerow(row)

if __name__ == "__main__":
    numbins = 50
    input_filename = "simulation.csv"
    output_filename = "simulation_discretized.csv"

    discretize(input_filename, output_filename, numbins)
