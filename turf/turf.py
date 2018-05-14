'''
turf.py: main code for Turf, the Caltech library TIND.io URL Fixer

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2018 by the California Institute of Technology.  This code is
open-source software.  Please see the file "LICENSE" for more information.
'''


import http.client
from   http.client import responses as http_responses
import os
import plac
import sys
from   time import time, sleep
from   urllib.parse import urlsplit
import urllib.request
from   xml.etree import ElementTree

try:
    thisdir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisdir, '../..'))
except:
    sys.path.append('../..')

from urlup import updated_urls

import turf
from turf.messages import color, msg

# NOTE: to turn on debugging, make sure python -O was *not* used to start
# python, then set the logging level to DEBUG *before* loading this module.
# Conversely, to optimize out all the debugging code, use python -O or -OO
# and everything inside "if __debug__" blocks will be entirely compiled out.
if __debug__:
    import logging
    logging.basicConfig(level = logging.INFO)
    logger = logging.getLogger('turf')
    def log(s, *other_args): logger.debug('turf: ' + s.format(*other_args))


# Global constants.
# .............................................................................

_FETCH_COUNT = 100
'''How many entries to get at one time from caltech.tind.io.'''

_NETWORK_TIMEOUT = 15
'''
How long to wait on a network connection attempt.
'''

# This is a cookie I extracted from a past session, and it seems to work to
# keep reusing it, which makes me think their service only checks for the
# valid form of a cookie value and not anything about the actual value used.
# However, this may break at some point.  FIXME.
_SESSION_COOKIE = 'EBSESSIONID=92991f926e3b4796a115da4505a01cfc'
'''Session cookie needed by EDS online API.'''

_EDS_ROOT_URL = 'http://web.b.ebscohost.com/pfi/detail/detail?vid=4&bdata=JnNjb3BlPXNpdGU%3d#'


# Main functions.
# .............................................................................

# field 001 is the tind record number
# field 856 is a URL, if there is one

def entries_from_search(search, max_records, write_unchanged, colorize, quiet):
    # Get results in batches of a certain number of records.
    if max_records and max_records < _FETCH_COUNT:
        search = substituted(search, '&rg=', '&rg=' + str(max_records))
    else:
        search = substituted(search, '&rg=', '&rg=' + str(_FETCH_COUNT))
    # Substitute the output format to be MARCXML.
    search = substituted(search, '&of=', '&of=xm')
    # Remove any 'ot' field because it screws up results.
    search = substituted(search, '&ot=', '')
    if __debug__: log('query string: {}', search)
    # Do a search & iterate over the results until we can't anymore.
    start = 1
    results = []
    if not max_records:
        max_records = 1000000           # FIXME
    while start > 0 and start < max_records:
        if __debug__: log('getting records starting at {}', start)
        records = tind_records(search, start)
        if records:
            if __debug__: log('processing next {} records', len(records))
            url_data = _entries_with_urls(records, write_unchanged, colorize, quiet)
            results += url_data
            start += len(url_data)
            sleep(1)                    # Be nice to the server.
        else:
            start = -1
    if start > max_records:
        msg('Stopped after {} records processed'.format(len(results)), 'warn', colorize)
    return results


def entries_from_file(file, max_records, write_unchanged, colorize, quiet):
    xmlcontent = None
    results = []
    with open(file) as f:
        if __debug__: log('parsing XML file {}', file)
        xmlcontent = ElementTree.parse(f)
        results = _entries_with_urls(xmlcontent, write_unchanged, colorize, quiet)
    return results


def _entries_with_urls(marcxml, write_unchanged, colorize, quiet):
    results = []
    for e in marcxml.findall('{http://www.loc.gov/MARC21/slim}record'):
        id = ''
        url_data = None
        original_url = ''
        for child in e:
            if child.tag == '{http://www.loc.gov/MARC21/slim}controlfield':
                if 'tag' in child.attrib and child.attrib['tag'] == '001':
                    id = child.text.strip()
                    continue
            if child.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                if 'tag' in child.attrib and child.attrib['tag'] == '856':
                    for elem in child:
                        if 'code' in elem.attrib and elem.attrib['code'] == 'u':
                            original_url = elem.text.strip()
                            headers = { 'Cookie': _SESSION_COOKIE }
                            url_data = updated_urls(eds_url(original_url), headers)
                            break
        if id:
            if len(e) <= 1:
                msg('Empty result for {}'.format(id), 'warn', colorize)
            if not quiet:
                if url_data and url_data.error:
                    msg('{}: {} produced error: {}'.format(color(id, 'error', colorize),
                                                           color(original_url, 'error', colorize),
                                                           color(url_data.error, 'error', colorize)))
                elif url_data:
                    if url_data.final != original_url or write_unchanged:
                        msg('{}: {} => {}'.format(color(id, 'info', colorize),
                                                  color(original_url, 'info', colorize),
                                                  color(url_data.final, 'blue', colorize)))
                else:
                    msg('{}'.format(id), 'info', colorize)
            if url_data:
                if url_data.error:
                    results.append([id, original_url, 'Error: ' + str(url_data.error)])
                elif url_data.final != original_url or write_unchanged:
                    results.append([id, original_url, url_data.final])
            else:
                results.append([id, original_url, ''])
    return results


def tind_records(query, start):
    query = substituted(query, '&jrec=', '&jrec=' + str(start))
    parts = urlsplit(query)
    if parts.scheme == 'https':
        conn = http.client.HTTPSConnection(parts.netloc, timeout=_NETWORK_TIMEOUT)
    else:
        conn = http.client.HTTPConnection(parts.netloc, timeout=_NETWORK_TIMEOUT)
    if __debug__: log('connecting to {}', parts.netloc)
    conn.request("GET", query, {})
    response = conn.getresponse()
    if __debug__: log('got response code {}', response.status)
    if response.status in [200, 202]:
        body = response.read().decode("utf-8")
        return ElementTree.fromstring(body)
    elif response.status in [301, 302, 303, 308]:
        import pdb; pdb.set_trace()
    else:
        return None


# Miscellaneous utilities.
# .............................................................................

_proxy_prefix = 'https://clsproxy.library.caltech.edu/login?url='
_proxy_prefix_len = len(_proxy_prefix)

# Example of a URL we start from:
# 'http://search.ebscohost.com/login.aspx?
# CustID=s8984125&db=edspub&type=44&bQuery=AN%2065536&direct=true&site=pfi-live'
#
# What we want to grab out of it:
# - db
# - bQuery

def eds_url(url):
    try:
        db = None
        item = None
        if url.startswith(_proxy_prefix):
            url = url[_proxy_prefix_len:]
        start = url.find('db=')
        if start > 0:
            end = url.find('&', start + 1)
            db = url[start + 3 : end]
        start = url.find('bQuery=')
        if start > 0:
            end = url.find('&', start + 1)
            item = url[start + 7 : end]
            item = decoded_html(item)
            # convert "AN ZZZZZ" to "AN=ZZZZZ"
            item = item.replace(' ', '=')
            return _EDS_ROOT_URL + item + '&db=' + db
        else:
            # This was not in the form we expected.  Return it as-is.
            return url
    except:
        import pdb; pdb.set_trace()


htmlCodes = (
    ('&amp;', '&'),
    ('&#39;', "'"),
    ('&quot;', '"'),
    ('&gt;', '>'),
    ('&lt;', '<'),
    ('%2B', '+'),
    ('%2C', ','),
    ('%20', ' '),
)


def decoded_html(s):
    for code in htmlCodes:
        s = s.replace(code[0], code[1])
    return s


def substituted(query, cmd, replacement):
    start = query.find(cmd)
    if start > 0:
        end = query.find('&', start + 1)
        new_query = query[: start] + replacement
        if end > 0:
            # Append back the rest if the cmd was not the last thing.
             new_query += query[end:]
        return new_query
    else:
        # What we searched for wasn't in the query string.  Append it.
        return query + replacement





# Please leave the following for Emacs users.
# ......................................................................
# Local Variables:
# mode: python
# python-indent-offset: 4
# End:
