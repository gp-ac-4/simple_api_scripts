import requests
import socket
import argparse
import sys
from OpenSSL import SSL
from cryptography import x509
from cryptography.x509.oid import NameOID
import concurrent.futures
from collections import namedtuple
import idna
from socket import socket

from requests.packages.urllib3.exceptions import InsecureRequestWarning # type: ignore
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

HostInfo = namedtuple(field_names='cert hostname peername', typename='HostInfo')

def connect_socket(hostname, port):
    sock = socket()
    sock.connect((hostname, port))
    return sock


def get_cert(sock, hostname_idna):
    ctx = SSL.Context(SSL.SSLv23_METHOD) # most compatible
    ctx.check_hostname = False
    ctx.verify_mode = SSL.VERIFY_NONE

    sock_ssl = SSL.Connection(ctx, sock)
    sock_ssl.set_connect_state()
    sock_ssl.set_tlsext_host_name(hostname_idna)
    sock_ssl.do_handshake()
    cert = sock_ssl.get_peer_certificate()
    crypto_cert = cert.to_cryptography()
    sock_ssl.close()
    sock.close()

    return crypto_cert # HostInfo(cert=crypto_cert, peername=peername, hostname=hostname)


def check_web_request(fqdn, output, httpTimeout=2):
    try:
        response = requests.get(f"https://{fqdn}", timeout=httpTimeout, verify=False)
        output.append(f"Webserver FOUND on {fqdn}.")
        output.append("\t --HTTP header info--")
        for key, value in response.headers.items():
            output.append(f"{key}: {value}")
    except requests.exceptions.Timeout:
        output.append(f"NO WEBSERVER found on {fqdn}.")
        return False
    except Exception as e:
        output.append(f"Failed to check {fqdn}. {e}")
        return False
    return True

def get_issuer(cert):
    try:
        names = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        return names[0].value
    except x509.ExtensionNotFound:
        return ""
    
def get_alt_names(cert):
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return ",".join(ext.value.get_values_for_type(x509.DNSName))
    except x509.ExtensionNotFound:
        return ""
    
def get_common_name(cert):
    try:
        names = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return names[0].value
    except x509.ExtensionNotFound:
        return ""
    
def format_basic_info(cert):
    output = []
    output.append("Certificate:")
    output.append("commonName: " + get_common_name(cert))
    output.append("SAN: " + get_alt_names(cert))
    output.append("issuer: " + get_issuer(cert))
    output.append(f"expires: {str(cert.not_valid_after_utc)}")
    return "\n".join(output)

def check_socket_connect(hostname, port):
    output = []
    try:
        sock = connect_socket(hostname, port)
        peername = sock.getpeername()
        output.append(f"Connected to {hostname} on {peername}.")

        cert = get_cert(sock, idna.encode(hostname))
        basicinfo = format_basic_info(cert)
        output.append(basicinfo)

    except Exception as e:
            output.append(f"Failed to connect to {hostname}. {e}")

    return "\n".join(output)

def check_web_server(hostname, port):
    output = []
    output.append("\n")
    repeatchar = len(hostname) + 21
    divider = "-" * repeatchar
    output.append(divider)
    output.append(f"--- Checking {hostname}:{port} ---")
    output.append(divider)
    # web request
    if check_web_request(hostname, output):
        output.append(divider)
        # socket connect
        output.append(check_socket_connect(hostname, port))

    output.append(divider)
    output.append(divider)
    output.append(divider)
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description='Check a list of FQDNs for webservers.')
    parser.add_argument('-file', help='The file containing the list of FQDNs.')
    parser.add_argument('-threads', help='Maximum concurrent threads.', type=int, default=5, choices=range(1, 11))
    parser.add_argument('-timeout', help='Maximum http timeout.', type=int, default=5)
    parser.add_argument('-output', help='Output file.', default='PRINT')
    parser.add_argument('-overwrite', help='Overwrite the output file if it already exists.', action='store_true')
    parser.add_argument('-append', help='Append to the output file if it already exists.', action='store_true')
    args = parser.parse_args()

    try:
        with open(args.file, 'r') as f:
            hosts = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File {args.file} not found.")
        sys.exit(1)

    if args.output != 'PRINT':
        if args.overwrite:
            with open(args.output, 'w') as f:
                f.write('')
        elif not args.append:
            try:
                with open(args.output, 'x') as f:
                    f.write('')
            except FileExistsError:
                print(f"File {args.output} already exists. You can use -overwrite or -append to this same name.")
                sys.exit(1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        for certinfo in executor.map(lambda x: check_web_server(x, 443), hosts):
            if args.output == 'PRINT':
                print(certinfo)
            else:
                with open(args.output, 'a') as f:
                    f.write(certinfo)
                    
# TODO: add support for CSV input and output
if __name__ == "__main__":
    main()