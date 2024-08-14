import pandas as pd
import re
import argparse

def process_csv(input_file_name, output_file_name, field_name, pattern, output_field_name):
    # Define the regular expression pattern
    pattern = re.compile(pattern)

    # Define a function to apply the regex pattern and return matches
    def find_matches(field):
        return pattern.findall(str(field))

    # Define the chunk size
    chunksize = 10 ** 3

    csv_header = True
    # Read the input CSV file in chunks
    for chunk in pd.read_csv(input_file_name, chunksize=chunksize):
        # Apply the function to the specified field
        chunk[output_field_name] = chunk[field_name].apply(find_matches)
        # extract all values from the chunk except the field_name
        chunk = chunk.drop(field_name, axis=1)
        chunk = chunk.explode(output_field_name)
        # Write the output DataFrame to the output CSV file
        chunk.to_csv(output_file_name, mode='a', index=False, header=csv_header)
        csv_header = False

if __name__ == "__main__":
    # Define the command-line arguments
    parser = argparse.ArgumentParser(description='Process a CSV file.')
    parser.add_argument('-i', '--input_file', help='The name of the input file.', default='input.csv')
    parser.add_argument('-o', '--output_file', help='The name of the output file.', default='output.csv')
    parser.add_argument('-n', '--output_field_name', help='The name of the new field.', default='matches')
    parser.add_argument('-f', '--field_name', help='The name of the field to be searched.', default='description')
    parser.add_argument('-p', '--pattern', help='The regular expression pattern.', default='ec2-[\w\-\.]*?\.amazonaws\.com')
    args = parser.parse_args()

    process_csv(args.input_file, args.output_file, args.field_name, args.pattern, args.output_field_name)