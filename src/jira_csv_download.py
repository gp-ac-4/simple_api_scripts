import argparse
import os
import pandas
import warnings
import JIRA
# jira = JIRA(jira_url, basic_auth=(username, password)
def download_ticket_data(jql, fields=["key", "summary","assignee","created","resolutiondate"], file_name="jira_output.csv", page_size=100, status_callback=None, jira_connection=None, jira_srver=None, pat=None, localserver=False):
    if localserver:
        options['verify'] = False
        restore_warning = warnings.showwarning
        warnings.showwarning = lambda *args, **kwargs: None

    if jira_connection is None:
        options = {
            'server': jira_srver,
            'headers': {
                'Authorization': 'Bearer {}'.format(pat),
                'Accept': 'application/json'
            },
        }

        if status_callback:
            status_callback("Connecting to Jira server {}".format(jira_srver))

        jira_connection = JIRA(options, max_retries=0)

    if status_callback:
        status_callback("Searching Jira Issues...")

    issues = jira_connection.search_issues(jql, fields=fields, maxResults=page_size)
    total_issues = issues.total
    if total_issues >0:
        # Calculate the number of pages based on the page size
        num_pages = (total_issues // page_size) + 1
    else:
        if status_callback:
            status_callback("No issues found")
        return
    
    if status_callback:
        status_callback("Found {} issues".format(total_issues))
        status_callback("Saving page {} of {}".format(1, num_pages))

    # Extract data and convert to DataFrame
    write_issues_to_csv(issues, fields, file_name, False)
        
    # Loop over each page and save it as a chunk in the CSV
    for page in range(1, num_pages):
        # Execute JQL query with pagination
        start_at = page * page_size
        issues = jira_connection.search_issues(jql, fields=fields, startAt=start_at, maxResults=page_size)

        if status_callback:
            status_callback("Saving page {} of {}".format(page + 1, num_pages))

        write_issues_to_csv(issues, fields, file_name, False)

    if localserver:
        warnings.showwarning = restore_warning

def write_issues_to_csv(issues, fields, file_name, csv_header):
    data = []
    for issue in issues:
        row = {field: issue.fields.__dict__.get(field) for field in fields}
        row['Issue key'] = issue.key
        row['Issue id'] = issue.id
        data.append(row)
    df = pandas.DataFrame(data)
    
    # Save each page in a CSV chunk using pandas
    df.to_csv(file_name, mode='a', index=False, header=csv_header)

def jira_csv_status_callback(message):
    print(" -- " + message)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', "--jira_server", help="Jira server URL")
    parser.add_argument('-t', "--jira_token", help="Jira personal access token")
    parser.add_argument('-q', "--jql", help="Jira Query Language (JQL)")
    
    parser.add_argument("--file_name", help="Name of the CSV", default="jira_output.csv")
    parser.add_argument("--page_size", help="Page size for pagination", default=100)
    parser.add_argument("--fields", help="Fields to include in the CSV", default=["key", "summary","assignee","created","description","resolutiondate","status"])
    args = parser.parse_args()

    # Get the parameters from the command line using argparse
    jira_server = args.jira_server or os.environ.get("JIRA_SERVER")
    jira_token = args.jira_token or os.environ.get("JIRA_TOKEN")


    if not jira_server:
        print("Jira server must be specified via parameter or JIRA_SERVER environment variable")
        parser.print_help()
        return
    
    if not jira_token:
        print("Jira token must be specified via parameter or JIRA_TOKEN environment variable")
        parser.print_help()
        return
    
    if os.path.isfile(args.file_name):
        os.remove(args.file_name)

    # Call the method to download ticket data from Jira and save it in a CSV
    download_ticket_data(
        args.jql,
        args.fields,
        args.file_name,
        args.page_size,
        jira_srver=jira_server,
        jira_token=jira_token,
        status_callback=jira_csv_status_callback
    )

if __name__ == "__main__":
    main()



