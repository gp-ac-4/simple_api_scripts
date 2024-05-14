import pandas as pd
import re
import argparse

def process_csv(input_file_name, output_file_name, field_name, pattern):
    # Define the regular expression pattern
    pattern = re.compile(pattern)

    # Define a function to apply the regex pattern and return matches
    def find_matches(field):
        return pattern.findall(str(field))

    # Define the chunk size
    chunksize = 10 ** 6

    # Initialize an empty DataFrame for the output
    df_output = pd.DataFrame()

    # Read the input CSV file in chunks
    for chunk in pd.read_csv(input_file_name, chunksize=chunksize):
        # Apply the function to the specified field
        chunk['matches'] = chunk[field_name].apply(find_matches)
        # Append the processed chunk to the output DataFrame
        df_output = pd.concat([df_output, chunk])

    # Write the output DataFrame to the output CSV file
    df_output.to_csv(output_file_name, index=False)

if __name__ == "__main__":
    # Define the command-line arguments
    parser = argparse.ArgumentParser(description='Process a CSV file.')
    parser.add_argument('-i', '--input_file', help='The name of the input file.')
    parser.add_argument('-o', '--output_file', help='The name of the output file.')
    parser.add_argument('-f', '--field_name', help='The name of the field to be searched.')
    parser.add_argument('-p', '--pattern', help='The regular expression pattern.')
    args = parser.parse_args()

    process_csv(args.input_file, args.output_file, args.field_name, args.pattern)