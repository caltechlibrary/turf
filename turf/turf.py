#!/usr/bin/env python3

# ipdb> x = tree.getroot().findall('{http://www.loc.gov/MARC21/slim}record')
# ipdb> x
# [<Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876278>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x1088764f8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876598>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876638>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x1088766d8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876778>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876818>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x1088768b8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876958>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x1088769f8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876a98>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876b38>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876bd8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876c78>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876d18>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876db8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876e58>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876ef8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876f98>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108879098>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108879138>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x1088791d8>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108879278>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108879318>, <Element '{http://www.loc.gov/MARC21/slim}record' at 0x1088793b8>]
# ipdb> x[0]
# <Element '{http://www.loc.gov/MARC21/slim}record' at 0x108876278>
# ipdb> x.findall('{http://www.loc.gov/MARC21/slim}datafield')
# *** AttributeError: 'list' object has no attribute 'findall'
# ipdb> x[0].findall('{http://www.loc.gov/MARC21/slim}datafield')
# [<Element '{http://www.loc.gov/MARC21/slim}datafield' at 0x1088763b8>]
# ipdb>
# [<Element '{http://www.loc.gov/MARC21/slim}datafield' at 0x1088763b8>]
# ipdb> y = x[0].findall('{http://www.loc.gov/MARC21/slim}datafield')
# ipdb> y
# [<Element '{http://www.loc.gov/MARC21/slim}datafield' at 0x1088763b8>]
# ipdb> y[0]
# <Element '{http://www.loc.gov/MARC21/slim}datafield' at 0x1088763b8>
# ipdb> y[0].tag
# '{http://www.loc.gov/MARC21/slim}datafield'
# ipdb> y[0].findall('{http://www.loc.gov/MARC21/slim}subfield')
# [<Element '{http://www.loc.gov/MARC21/slim}subfield' at 0x108876408>, <Element '{http://www.loc.gov/MARC21/slim}subfield' at 0x108876458>]
# ipdb> f = y[0].findall('{http://www.loc.gov/MARC21/slim}subfield')
# ipdb> f
# [<Element '{http://www.loc.gov/MARC21/slim}subfield' at 0x108876408>, <Element '{http://www.loc.gov/MARC21/slim}subfield' at 0x108876458>]
# ipdb> f[0]
# <Element '{http://www.loc.gov/MARC21/slim}subfield' at 0x108876408>
# ipdb> f[0].tag
# '{http://www.loc.gov/MARC21/slim}subfield'
# ipdb> f[0].text
# 'https://clsproxy.library.caltech.edu/login?url=http://search.ebscohost.com/login.aspx?CustID=s8984125&db=edspub&type=44&bQuery=AN%2065536&direct=true&site=pfi-live'

import http.client
from   http.client import responses as http_responses
import os
import plac
import sys
from   time import time, sleep
from   urllib.parse import urlsplit
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
    logger = logging.getLogger('urlup')
    def log(s, *other_args): logger.debug('urlup: ' + s.format(*other_args))


# Global constants.
# .............................................................................

_DEFAULT_FETCH_COUNT = 1000
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

def entries_from_search(search, count, colorize, quiet):
    # Substitute the output format to be MARCXML.
    search = substituted(search, '&of=', '&of=xm')
    # Get results in batches of a certain number of records.
    search = substituted(search, '&rg=', '&rg=' + str(count))
    # Do a search & iterate over the results until we can't anymore.
    start = 1
    results = []
    while start > 0:
        records = tind_records(search, start)
        if records:
            url_data = _entries_with_urls(records, colorize, quiet)
            results.append(url_data)
            start += len(url_data)
            sleep(1)                    # Be nice to the server.
        else:
            start = -1
    return results


def entries_from_file(file, count, colorize, quiet):
    xmlcontent = None
    results = []
    with open(file) as f:
        xmlcontent = ElementTree.parse(f)
        results = _entries_with_urls(xmlcontent, colorize, quiet)
    return results


def _entries_with_urls(marcxml, colorize, quiet):
    results = []
    for e in marcxml.findall('{http://www.loc.gov/MARC21/slim}record'):
        tind_id = ''
        url = ''
        results_tuple = None
        original_url = None
        for child in e:
            if child.tag == '{http://www.loc.gov/MARC21/slim}controlfield':
                if 'tag' in child.attrib and child.attrib['tag'] == '001':
                    tind_id = child.text.strip()
                    continue
            if child.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                if 'tag' in child.attrib and child.attrib['tag'] == '856':
                    for elem in child:
                        if 'code' in elem.attrib and elem.attrib['code'] == 'u':
                            original_url = elem.text.strip()
                            headers = { 'Cookie': _SESSION_COOKIE }
                            results_tuple = updated_urls(eds_url(original_url), headers)
                            break
        if tind_id:
            destination_url = results_tuple[1] if results_tuple else None
            if not quiet:
                if results_tuple:
                    msg('{}: {} => {}'.format(tind_id, original_url, destination_url))
                else:
                    msg('{}'.format(tind_id))
            results.append([tind_id, original_url, destination_url])
    return results


def tind_records(query, start):
    query = substituted(query, '&jrec=', '&jrec=' + str(start))
    parts = urlsplit(query)
    if parts.scheme == 'https':
        conn = http.client.HTTPSConnection(parts.netloc, timeout=_NETWORK_TIMEOUT)
    else:
        conn = http.client.HTTPConnection(parts.netloc, timeout=_NETWORK_TIMEOUT)
    conn.request("GET", query, {})
    response = conn.getresponse()
    if response.status in [200, 202]:
        body = response.read().decode("utf-8")
        return ElementTree.fromstring(body)
    elif response.status in [301, 302, 303, 308]:
        # Redirection.  Start from the top with new URL.
        new_url = response.getheader('Location')
        return tind_records(new_url)
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
