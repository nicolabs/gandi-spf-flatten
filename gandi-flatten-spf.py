#!/usr/bin/env python3
import argparse
import logging
import os
import requests
import json
import re
from dns import resolver
from dns import name
from sender_policy_flattener.crawler import crawl
from sender_policy_flattener.formatting import ips_to_spf_strings
import numpy


DEFAULT_LOGLEVEL = logging.getLevelName(logging.INFO)

# Template URLs to get / put the TXT records of {domain}
URL_TEMPLATE = "https://api.gandi.net/v5/livedns/domains/{domain}/records/@/TXT"

# HTTP headers with {apikey}
AUTHZ_TEMPLATE = 'Apikey {apikey}'

# Regular expression to detect SPF records between other records
# Note that a SPF string may not exceed 255 characters,
# however it is allowed so split the record's content into several quote-enclosed strings to bypass this limit
# (very useful when flattening DNS into many IPs)
RE_SPF = re.compile(r'v=spf1')

RE_MERGE_SUBSTRINGS = re.compile(r'"\s+"')

# Template string to build TXT record for SPF
SPF_TEMPLATE = "\"v=spf1 {includes} ~all\""

# Default name servers to use to resolve domain addresses
DEFAULT_DNS = ['8.8.8.8','4.4.4.4']



def spf2ips(records, domain, resolvers):
    ips = set()
    for rrecord, rdtype in records.items():
        for ip in crawl(rrecord, rdtype, domain, resolvers):
            ips.add(ip)
    ips = ips_to_spf_strings(ips)
    return ips



"""
    Builds a valid TXT record for SPF by resolving DNS into IP addresses

    _emailProviders: list of SPF domains of the email providers you want to add to SPF
    _nameServers: list of DNS you want to use to resolve domains into IP addresses

    Returns the TXT record as a string
"""
def createFlatSpfRecord( _emailProviders, _nameServers ):

    dnsResolver = resolver.Resolver()
    dnsResolver.nameservers = _nameServers

    ips = []
    for emailProvider in _emailProviders:

        ips = ips + spf2ips({emailProvider: 'txt'}, emailProvider, dnsResolver)

    logging.debug("Flattened IPs : %s",ips)
    return SPF_TEMPLATE.format( includes=" ".join(ips) )



"""
    Reads JSON TXT record using Gandi's API

    Returns the list of TXT records as an array of strings
"""
def gandi_getTxtRecords( _domain, _apikey ):

    url = URL_TEMPLATE.format(domain=_domain)
    headers = {'authorization': AUTHZ_TEMPLATE.format(apikey=_apikey)}
    logging.debug("Calling : %s",url)
    logging.debug("Headers : %s",headers)
    response = requests.get(url, headers=headers)
    logging.debug("Response & .text : %s %s",response,response.text)
    txtRecords = json.loads(response.text)
    return txtRecords['rrset_values']



"""
    Reads JSON TXT records from a JSON file

    Returns the list of TXT records as an array of strings
"""
def file_getTxtRecords( _filename ):

    with open(_filename) as f:
        response = json.dumps(json.load(f))
        txtRecords = json.loads(response)
        return txtRecords['rrset_values']



"""
    Takes existing TXT SPF records and returns a flattened version.
    This function only does formatting (no online call).
"""
def flattenSpfRecords( _txtRecords, _flatSpfRecord ):

    oldRecords = []
    newRecords = []

    done = None
    for record in _txtRecords:
        # If this record is a SPF one (starts with 'v=spf1')
        # Replace it with the flatten record

        # Note : using search instead of match because the record might start with quotes (or not ?)
        if RE_SPF.search(record):
            logging.debug("Flattening record : %s",record)
            # There must be only one such record
            if not done:
                newRecords = newRecords + [_flatSpfRecord]
                # Normalize the old record so that it can be compared later
                # => The old record may contain split strings,
                # but we don't do it in the new record (it's handled by the API)
                oldRecords = oldRecords + [ RE_MERGE_SUBSTRINGS.sub('',record) ]
                done = record
            else:
                logging.warning("Multiple SPF records detected !\n1. %s\n2. %s",done,record)
        # Else, simply put it back in the list (unchanged)
        else:
            logging.debug("Keeping record untouched : %s",record)
            newRecords = newRecords + [record]
            oldRecords = oldRecords + [record]

    return oldRecords, newRecords



"""
    Custom comparison function.

    Compares one by one the records before and after,
    and especially dive into the SPF records to make sure that equality is not
    dependent on the order of entries within the record.

    Returns True if the records have changed
"""
def isRecordsChanged( _recordsBefore, _recordsAfter ):

    if len(_recordsBefore) != len(_recordsAfter):
        return True

    sortedBefore = sorted(_recordsBefore)
    sortedAfter = sorted(_recordsAfter)
    for r in range(len(_recordsBefore)):
        if RE_SPF.search(sortedBefore[r]) and RE_SPF.search(sortedAfter[r]):
            listBefore = re.split( r'\s+', sortedBefore[r] )
            listAfter = re.split( r'\s+', sortedAfter[r] )
            if not numpy.array_equal( sorted(listBefore), sorted(listAfter) ):
                return True
        else:
            if sortedAfter[r] != sortedBefore[r]:
                return True

    return False



"""
    Updates the TXT records with the flattened SPF ones, using Gandi's Live DNS API
"""
def updateDns( _domain, _apikey, _txtRecords, _dryRun=False ):

    url = URL_TEMPLATE.format(domain=_domain)
    headers = {'authorization': AUTHZ_TEMPLATE.format(apikey=_apikey)}
    body = json.dumps( {"rrset_values":_txtRecords} )
    if not _dryRun:
        response = requests.put(url, headers=headers, data=body)
    else:
        logging.info("Calling : %s",url)
        logging.info("With headers : %s",headers)
        logging.info("And body : %s",body)



parser = argparse.ArgumentParser(description="Flatten SPF records using Gandi's Live DNS API")
parser.add_argument('-d', '--domain', nargs='+', required=True, help="Domains you own from which to update the TXT record for SPF")
parser.add_argument('-e', '--email-providers', nargs='+', required=True, help="E-mail providers' SPF domains to add to the TXT record")
parser.add_argument('-k', '--apikey', help="Your Gandi API key (otherwise looks for the 'GANDI-APIKEY' environment variable)")
parser.add_argument('-r', '--dns', default=DEFAULT_DNS, nargs='+', help="DNS servers to use to resolve into IP addresses")
parser.add_argument('-l', '--log-level', default=DEFAULT_LOGLEVEL, help="Log level")
parser.add_argument('-L', '--load', help="A JSON file to load the result from Gandi's API instead of calling the API")
parser.add_argument('-K', '--dry-run', action='store_true', help="Dry-run mode (will not change the records, only print)")
args = parser.parse_args()

logging.basicConfig(level=logging.getLevelName(args.log_level))

logging.debug(repr(args))

if args.apikey:
    apikey = args.apikey
else :
    apikey = os.environ['GANDI_APIKEY']



flatSpf = createFlatSpfRecord(args.email_providers,args.dns)
for domain in args.domain:
    if args.load:
        txts = file_getTxtRecords(args.load)
    else:
        txts = gandi_getTxtRecords(domain,apikey)
    oldTxts, newTxts = flattenSpfRecords(txts,flatSpf)
    logging.debug("Old records : %s",oldTxts)
    logging.debug("New records : %s",newTxts)
    # Only proceed if records have changed
    if isRecordsChanged(newTxts,oldTxts):
        updateDns(domain,apikey,newTxts,args.dry_run)
    else:
        logging.info("No change - quitting")
