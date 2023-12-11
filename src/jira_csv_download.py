import argparse
import os
import pandas
import JIRA

def download_ticket_data(username, password, jql, fields=["key", "summary","assignee","created","resolutiondate"], file_name="jira_output.csv", page_size=100):
    # Connect to Jira
    jira = JIRA(basic_auth=(username, password), server='https://your-jira-instance.atlassian.net')

    # Get the total number of issues
    total_issues = jira.search_issues(jql, maxResults=0).total

    # Calculate the number of pages based on the page size
    num_pages = (total_issues // page_size) + 1

    # Loop over each page and save it as a chunk in the CSV
    for page in range(num_pages):
        # Execute JQL query with pagination
        start_at = page * page_size
        issues = jira.search_issues(jql, fields=fields, startAt=start_at, maxResults=page_size)

        # Extract data and convert to pandas DataFrame
        data = []
        for issue in issues:
            row = {field: issue.fields.__dict__.get(field) for field in fields}
            data.append(row)
        df = pandas.DataFrame(data)

        # Save each page in a CSV chunk using pandas
        save_csv_chunk(df, file_name)

def save_csv_chunk(data, filename):
    data.to_csv(filename, mode='a', index=False, header=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", help="Jira username")
    parser.add_argument("--password", help="Jira password")
    parser.add_argument("--jql", help="Jira Query Language (JQL)")
    parser.add_argument("--fields", help="Fields to include in the CSV")
    parser.add_argument("--file_name",default="jira_output.csv", help="Name of the CSV")
    parser.add_argument("--page_size",default=500, help="Page size for pagination")
    args = parser.parse_args()

    # Get the parameters from the command line using argparse
    username = args.username or os.environ.get("JIRA_USERNAME")
    password = args.password or os.environ.get("JIRA_PASSWORD")

    # If Jira username and password are not passed at the command line, attempt to get them from the environment
    if not username or not password:
        raise ValueError("Jira username and password are required")

    # Call the method to download ticket data from Jira and save it in a CSV
    download_ticket_data(username, password, args.jql, args.fields, args.file_name, args.page_size)

if __name__ == "__main__":
    main()



