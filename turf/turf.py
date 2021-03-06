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

from   collections import namedtuple
import http.client
from   http.client import responses as http_responses
from   itertools import zip_longest
import os
import plac
import re
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

from urlup import updated_urls, UrlData

import turf
from turf.messages import color, msg
from turf.data_types import TindData, ProxyInfo, UIsettings

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
'''How many entries to get at one time from caltech.tind.io.  Smaller batches
make it possible to write out results more reliably as we run, at the cost of
some speed.'''

_NETWORK_TIMEOUT = 15
'''How long to wait on a network connection attempt.'''

_MAX_NULLS = 10
'''How many consecutive empty results we accept before we assume that
something is going wrong.'''

# This is a cookie I extracted from a past session, and it seems to work to
# keep reusing it, which makes me think their service only checks for the
# valid form of a cookie value and not anything about the actual value used.
# However, this may break at some point.  FIXME.
_SESSION_COOKIE = 'EBSESSIONID=92991f926e3b4796a115da4505a01cfc'
'''Session cookie needed by EDS online API.'''

#_EDS_ROOT_URL = 'http://web.b.ebscohost.com/pfi/detail/detail?vid=4&bdata=JnNjb3BlPXNpdGU%3d#'
_EDS_ROOT_URL = 'http://eds.a.ebscohost.com/eds/detail/detail?vid=0&bdata=JnNpdGU9ZWRzLWxpdmUmc2NvcGU9c2l0ZQ%3d%3d#'


# Main functions.
# .............................................................................

# field 001 is the tind record number
# field 856 is a URL, if there is one

def entries_from_search(search, max_records, start_index, proxyinfo, uisettings):
    # Get results in batches of a certain number of records.
    if max_records and max_records < _FETCH_COUNT:
        search = substituted(search, '&rg=', '&rg=' + str(max_records))
    else:
        search = substituted(search, '&rg=', '&rg=' + str(_FETCH_COUNT))
    # Substitute the output format to be MARCXML.
    search = substituted(search, '&of=', '&of=xm')
    # Remove any 'ot' field because it screws up results.
    search = substituted(search, '&ot=', '')
    # Set starting and stopping points.
    current = start_index
    stop = (start_index + max_records) if max_records else sys.maxsize
    if __debug__: log('query string: {}', search)
    if __debug__: log('getting records starting at {}', start_index)
    if __debug__: log('will stop at {} records', stop)
    # The tind.io output doesn't include the number of records available.  So,
    # when iterating over all results, we must do something ourselves to avoid
    # fetching the last page over and over.  We watch for entries we've seen.
    seen = set()
    # Sometimes the server stops returning values.  Unclear why, but when it
    # happens we may as well stop.  We track it using this variable:
    consecutive_nulls = 0
    while 0 < current < stop and consecutive_nulls < _MAX_NULLS:
        try:
            marcxml = tind_records(search, current, proxyinfo)
            if not marcxml:
                if __debug__: log('no records received')
                current = -1
                consecutive_nulls += 1
                break
            if __debug__: log('looping over {} TIND records', len(marcxml))
            for data in _extracted_data(marcxml, proxyinfo):
                if data.id in seen:
                    stop = 0
                else:
                    seen.add(data.id)
                if not data.url_data:
                    consecutive_nulls += 1
                else:
                    consecutive_nulls = 0
                if not uisettings.quiet:
                    print_record(current, data, uisettings.colorize)
                yield data
                if current >= stop:
                    break
                current += 1
                if proxyinfo.reset:
                    # Don't keep resetting the credentials.
                    proxyinfo.reset = False
        except KeyboardInterrupt:
            msg('Stopped', 'warn', uisettings.colorize)
            current = -1
        except Exception as err:
            msg('Error: {}'.format(err), 'error', uisettings.colorize)
            current = -1
        sleep(0.5)                      # Be nice to the server.
    if current >= stop and consecutive_nulls < _MAX_NULLS:
        if __debug__: log('stopping point reached')
        if not uisettings.quiet:
            msg('Processed {} entries'.format(len(seen)), 'info', uisettings.colorize)
    elif consecutive_nulls >= _MAX_NULLS:
        if not uisettings.quiet:
            msg('Too many consecutive null responses -- something is wrong',
                'error', uisettings.colorize)
    yield None


def entries_from_file(file, max_records, start_index, proxyinfo, uisettings):
    xmlfile = open(file, 'r')
    if __debug__: log('parsing XML file {}', file)
    try:
        xmlcontent = ElementTree.parse(xmlfile)
        for data in _extracted_data(xmlcontent):
            yield data
    except KeyboardInterrupt:
        msg('Stopped', 'warn', uisettings.colorize)
        yield None
    except Exception as err:
        msg('Error: {}'.format(err), 'error', uisettings.colorize)
        yield None
    finally:
        xmlfile.close()


def _extracted_data(marcxml, proxyinfo):
    # Generator producing a list of TindData named tuples. The url_data field
    # is a list of UrlData structures retured by Urlup for each URL found in
    # field 856 (if any are found) for the MARC XML record.

    for e in marcxml.findall('{http://www.loc.gov/MARC21/slim}record'):
        id = ''
        final_urls = []
        original_urls = []
        # Look through this record, searching for field 856.
        # If found, gather up all URLs (datafield code 'u') into original_urls
        # (massaging them using function eds_url() while we're at it).
        for child in e:
            if child.tag == '{http://www.loc.gov/MARC21/slim}controlfield':
                if 'tag' in child.attrib and child.attrib['tag'] == '001':
                    id = child.text.strip()
                    continue
            if child.tag == '{http://www.loc.gov/MARC21/slim}datafield':
                if 'tag' in child.attrib and child.attrib['tag'] == '856':
                    for elem in child:
                        if 'code' in elem.attrib and elem.attrib['code'] == 'u':
                            extracted_url = eds_url(elem.text.strip())
                            original_urls.append(extracted_url)
        if not id:
            if __debug__: log('skipping entry without id')
            continue
        if len(original_urls) == 0:
            if __debug__: log('no URLs in record for {}', id)
            yield TindData(id, [])
            continue

        # Setting the user agent is because Proquest.com returns a 403
        # otherwise, possibly as an attempt to block automated scraping.
        # Changing the user agent to a browser name seems to solve it.
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:42.0)'}
        # This next thing is a hack that makes ebscohost think we're logged in.
        # It's the only way I found so far to avoid the occasional "upcoming
        # maintenance" announcement click-through pages.
        cookies = {'EBSESSIONID': '79e365c204f844af99f26dd45fedf6e1',
                   'EBUQUSER': '79e365c204f844af99f26dd45fedf6e1'}
        if __debug__: log('calling urlup on record ' + id)
        url_data_list = updated_urls(original_urls, cookies, headers,
                                     proxyinfo.user, proxyinfo.password,
                                     proxyinfo.use_keyring, proxyinfo.reset)
        if __debug__: log('got {} URLs for {}', len(url_data_list), id)
        url_data_list = list(map(rewrite_url, url_data_list))
        yield TindData(id, url_data_list)


def tind_records(query, start, proxyinfo):
    query = substituted(query, '&jrec=', '&jrec=' + str(start))
    parts = urlsplit(query)
    if parts.scheme == 'https':
        conn = http.client.HTTPSConnection(parts.netloc, timeout=_NETWORK_TIMEOUT)
    else:
        conn = http.client.HTTPConnection(parts.netloc, timeout=_NETWORK_TIMEOUT)
    if __debug__: log('connecting to {} using url {}', parts.netloc, query)
    headers = { 'Cookie': _SESSION_COOKIE }
    conn.request("GET", query, headers = headers)
    response = conn.getresponse()
    if __debug__: log('got response code {}', response.status)
    if response.status in [200, 202]:
        body = response.read().decode("utf-8")
        return ElementTree.fromstring(body)
    elif response.status in [301, 302, 303, 308]:
        raise Exception('Server returned code {} -- unable to continue'.format(response.status))
    return None


def num_records(marcxml):
    return len(marcxml.findall('{http://www.loc.gov/MARC21/slim}record'))


# This is a start.  Probabaly will have to create an objection and better
# organization if more URLs are needed in the future.

_recognized_patterns = [
    r'https://ebookcentral.proquest.com/auth/lib/caltech-ebooks/maintenance.action\?returnURL=(http.*)$',
]

def rewrite_url(url_data):
    for pat in _recognized_patterns:
        if not url_data.final:
            continue
        content_match = re.match(pat, url_data.final)
        if content_match:
            real_destination = decoded_html(content_match.group(1))
            return UrlData(url_data.original, real_destination,
                           url_data.status, url_data.error)
    return url_data


def recognized_url(url):
    return any(re.match(case[0], url) for case in _rewritable_urls)



# Miscellaneous utilities.
# .............................................................................

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
    (r'&amp;', '&'),
    (r'&#39;', "'"),
    (r'&quot;', '"'),
    (r'&gt;', '>'),
    (r'&lt;', '<'),
    (r'%2B', '+'),
    (r'%2C', ','),
    (r'%2F', '/'),
    (r'%20', ' '),
    (r'%3A', ':'),
    (r'%3D', '='),
    (r'%3F', '?'),
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


def print_record(current_index, record, colorize):
    if len(record.url_data) == 0:
        msg('No URLs for {}'.format(record.id), 'warn', colorize)
        return
    for item in record.url_data:
        text = []
        if item.error:
            if colorize:
                text += ['{} error: {}'.format(color(item.original, 'error', colorize),
                                               color(item.error, 'error', colorize))]
            else:
                # If not using colorization, go easy on the use of the
                # 'error' code because the plain-text equivalent is loud.
                text += ['{}: {}'.format(color(item.original, 'error', colorize),
                                         color(item.error, 'info', colorize))]
        elif item.original != item.final:
            text += ['{} => {}'.format(color(item.original, 'info', colorize),
                                       color(item.final, 'cyan', colorize))]
        else:
            text += ['{} {}'.format(color(item.original, 'info', colorize),
                                    color('[unchanged]', 'dark', colorize))]
        msg('({:6}) {}: {}'.format(current_index, record.id,
                                   ('\n          ' + ' '*len(record.id)).join(text)))


# Please leave the following for Emacs users.
# ......................................................................
# Local Variables:
# mode: python
# python-indent-offset: 4
# End:
