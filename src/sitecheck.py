import requests
import ssl
import socket
import argparse
import sys
import threading

from requests.packages.urllib3.exceptions import InsecureRequestWarning # type: ignore
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def get_certificate(host, port=443):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
    conn.settimeout(3.0)
    try:
        conn.connect((host, port))
        return conn.getpeercert()
    except Exception as e:
        raise Exception(f"Unable to retrieve certificate from {host}:{port}. Error {e}") from e

def check_webserver(fqdn, httpTimeout=2):
    output = []
    output.append("\n")
    repeatchar = len(fqdn) + 17
    divider = "-" * repeatchar
    output.append(divider)
    output.append(f"--- Checking {fqdn} ---")
    output.append(divider)
    try:
        response = requests.get(f"https://{fqdn}", timeout=httpTimeout, verify=False)
        output.append(f"Webserver found on {fqdn}.")
        format_header_output(output, response, divider)
        check_certificate(fqdn, output, divider)
    except requests.exceptions.Timeout:
        output.append(f"No webserver found on {fqdn}.")

    print('\n'.join(output))

def format_header_output(output, response, divider):
    output.append("\n")
    output.append("  HTTP HEADER INFORMATION")
    output.append(divider)
    for key, value in response.headers.items():
        output.append(f"{key}: {value}")

def check_certificate(fqdn, output, divider):
    output.append("\n")
    output.append("  CERTIFICATE INFORMATION")
    output.append(divider)
    try:
        cert = get_certificate(fqdn)
        if cert is not None:
            subject = dict(x[0] for x in cert['subject'])
            issued_to = subject['commonName']
            output.append(f"Certificate for {fqdn} issued to {issued_to}:")
            for key, value in cert.items():
                output.append(f"{key}: {value}")
        else:
            output.append(f"Certificate information for {fqdn} not found.")

    except Exception as e:
        output.append(divider)
        output.append(f"Error retrieving certificate for {fqdn}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Check a list of FQDNs for webservers.')
    parser.add_argument('-file', help='The file containing the list of FQDNs.')
    parser.add_argument('-threads', help='Maximum concurrent threads.', type=int, default=5)
    parser.add_argument('-timeout', help='Maximum http timeout.', type=int, default=5)
    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            fqdns = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File {args.file} not found.")
        sys.exit(1)
        
 
    threads = []
    for fqdn in fqdns:
        t = threading.Thread(target=check_webserver, args=(fqdn,))
        threads.append(t)
        t.start()
        # Limit the number of concurrent threads
        if len(threads) >= args.threads:
            for t in threads:
                t.join()
            threads = []

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()