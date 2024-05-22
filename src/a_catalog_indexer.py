import base64
import os
import sys
import argparse
import yaml
import pandas as pd
from github import Github

def create_csv_index(access_token, file_name, repo_name, yaml_value, output_file, chunk_size=1000):
    # Initialize a Github instance with your access token
    g = Github(access_token)

    # Get the repository
    repo = g.get_repo(repo_name)

    # Initialize a list to store the results
    results = []

    # Search for the file in the repository
    for i, file in repo.get_contents(""):
        if file.name == file_name:
            # Get the content of the file
            content = base64.b64decode(file.content)

            # Parse the content as YAML
            data = yaml.safe_load(content)

            # Extract the 'team' value
            team = data.get(yaml_value)

            # Get the name of the folder that contains the file
            folder_name = file.path.rsplit('/', 1)[0]

            # Add the 'team' value and the folder name to the results
            results.append({yaml_value: team, 'folder_name': folder_name})
            
            # Write the results to a file every N rows
            if (i + 1) % chunk_size == 0:
                df = pd.DataFrame(results)
                df.to_csv(output_file, index=False, mode='a', header=not os.path.exists(output_file))
                results = []

    # Write any remaining results to the file
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, mode='a', header=not os.path.exists(output_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--access_token', type=str, default=os.getenv('GITHUB_ACCESS_TOKEN'),
                        help='Github access token')
    parser.add_argument('--file_name', type=str, required=True,
                        help='Name of the file to search for')
    parser.add_argument('--repo_name', type=str, required=True,
                        help='Name of the repository to search in')
    parser.add_argument('--yaml_value', type=str, required=True,
                        help='YAML value to extract')
    parser.add_argument('--output_file', type=str, required=True,
                        help='Output CSV file name', default='output.csv')

    args = parser.parse_args()

    if args.repo_name is None or args.accesstoken is None:
        parser.print_help()
        sys.exit(1) 

    create_csv_index(args.access_token, args.file_name, args.repo_name, args.yaml_value, args.output_file)