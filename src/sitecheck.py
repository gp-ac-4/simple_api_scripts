import json
import requests
import socket
import argparse
import sys
import pandas
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


def check_web_request(host, httpTimeout=2): 
    try:
        response = requests.get(f"https://{host}", timeout=httpTimeout, verify=False)
        # convert the headers to a dictionary
        return {'host':host,'http_connect':'true','http_status':response.status_code,'http_headers':json.dumps(dict(response.headers))}
    except Exception as e:
        return {'host':host,'http_connect':'false'}

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
    return {"commonName" : get_common_name(cert),
     "SAN" : get_alt_names(cert),
     "issuer" : get_issuer(cert),
     "expires" : str(cert.not_valid_after_utc)}
    

def check_socket_connect(hostname, port):
    try:
        sock = connect_socket(hostname, port)
        peername = sock.getpeername()

        cert = get_cert(sock, idna.encode(hostname))
        basicinfo = format_basic_info(cert)
        return {**{'host':hostname,'port':port,'peername':peername}, **basicinfo}

    except Exception as e:
            print(f"Failed to connect to {hostname}. {e}")



def check_web_server(hostname, port, data={}, mergedata=False):

    connectresult = check_web_request(hostname)
    if mergedata: connectresult = {**connectresult, **data}

    certresult = {} 
    if (connectresult['http_connect'] == 'true'): certresult = check_socket_connect(hostname, port)

    return {**connectresult, **certresult}

def chunk_hosts(hostRowCollection, mergedata=False):
    for index, row in hostRowCollection.iterrows():
        if row.get('port') == None: row['port'] = 443
        yield check_web_server(row['host'], row['port'], row, mergedata)

def main():
    parser = argparse.ArgumentParser(description='Check a list of hosts for webservers.')
    parser.add_argument('-file', help='The file containing the list of host.')
    parser.add_argument('-threads', help='Maximum concurrent threads.', type=int, default=5, choices=range(1, 11))
    parser.add_argument('-timeout', help='Maximum http timeout.', type=int, default=5)
    parser.add_argument('-output', help='Output file.', default='PRINT')
    parser.add_argument('-update', help='Update the input file.', action='store_true')
    parser.add_argument('-overwrite', help='Overwrite the output file if it already exists.', action='store_true')
    parser.add_argument('-append', help='Append to the output file if it already exists.', action='store_true')
    parser.add_argument('-chunksize', help='Chunk size for reading the input file.', type=int, default=1000)
    args = parser.parse_args()

    # check to make sure the file exists
    try:
        with open(args.file) as reader:
            pass
    except FileNotFoundError:
        print(f"Input file {args.file} not found.")
        sys.exit(1)

    addHeaders = True
    if (args.overwrite):  
        writeMode = 'w'
    else:
        writeMode = 'a'
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        for hostresult in executor.map(lambda x: chunk_hosts(x, args.update), pandas.read_csv(args.file, chunksize=args.chunksize)):
            if args.output == 'PRINT':
                print(hostresult)
            else:
                pandas.DataFrame(hostresult).to_csv(args.output, mode=writeMode, header=addHeaders)
                addHeaders = False
                writeMode = 'a'
                    
if __name__ == "__main__":
    main()