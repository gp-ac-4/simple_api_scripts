import argparse
import os
import pandas
import warnings
import JIRA


def download_ticket_data(jql, fields=["key", "summary","assignee","created","resolutiondate"], file_name="jira_output.csv", page_size=100, status_callback=None, jira_connection=None, jira_srver=None, pat=None, localserver=False):
    """
    Downloads ticket data from Jira based on the provided JQL query and saves it in a CSV file.

    Args:
        jql (str): Jira Query Language (JQL) to search for issues.
        fields (list, optional): List of fields to include in the CSV. Defaults to ["key", "summary","assignee","created","resolutiondate"].
        file_name (str, optional): Name of the CSV file to save the data. Defaults to "jira_output.csv".
        page_size (int, optional): Page size for pagination. Defaults to 100.
        status_callback (function, optional): Callback function to display status messages. Defaults to None.
        jira_connection (JIRA, optional): Existing JIRA connection object. Defaults to None.
        jira_srver (str, optional): Jira server URL. Defaults to None.
        pat (str, optional): Jira personal access token. Defaults to None.
        localserver (bool, optional): Flag to indicate if running on a local server. Defaults to False.
    """
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
    """
    Writes the Jira issues data to a CSV file.

    Args:
        issues (list): List of Jira issues.
        fields (list): List of fields to include in the CSV.
        file_name (str): Name of the CSV file.
        csv_header (bool): Flag to indicate if the CSV file should include a header row.
    """
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
    """
    Callback function to print status messages.

    Args:
        message (str): Status message to print.
    """
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



