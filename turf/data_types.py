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

class TindData():
    '''Class object to store the id and UrlData for an entry.'''

    id = None
    url_data = None

    def __init__(self, id = None, url_data = None):
        self.id = id
        self.url_data = url_data


class ProxyInfo():
    '''Class object to store data for proxy logins.'''

    user = None
    password = None
    use_keyring = True
    reset = False

    def __init__(self, user = None, pswd = None, use_keyring = True, reset = False):
        self.user = user
        self.password = pswd
        self.use_keyring = use_keyring
        self.reset = reset


class UIsettings():
    '''Class object to store run-time display settings.'''

    colorize = False
    quiet = True

    def __init__(self, colorize = False, quiet = True):
        self.colorize = colorize
        self.quiet = quiet
