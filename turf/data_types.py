'''
data_types: data types used in Turf

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2018 by the California Institute of Technology.  This code is
open-source software released under a 3-clause BSD license.  Please see the
file "LICENSE" for more information.
'''

from   collections import namedtuple

TindData = namedtuple('TindData', 'id url_data')
TindData.__doc__ = '''Named tuple storing the id and UrlData for an entry.
'''

ProxyInfo = namedtuple('ProxyInfo', 'user password use_keyring')
ProxyInfo.__doc__ = '''Named tuple storing data for proxy logins'
'''

UIsettings = namedtuple('UIsettings', 'colorize quiet')
UIsettings.__doc__ = '''Named tuple storing run-time display settings'''
