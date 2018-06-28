'''__main__: main command-line interface to turf

There are several hundred thousand entries in https://caltech.tind.io.  Some
of the entries contain links to other web resources.  As a matter of regular
maintenance, the links need to be checked periodically for validity, and
preferrably also updated to point to new destinations if the referenced
resources have been relocated.

Turf is a small program that downloads records from https://caltech.tind.io,
examines each one looking for URLs, deferences any found, and then finally
prints a list of record entries together with old and new URLs.  By default,
if not given an explicit search string, Turf will do a search for all entries
that have one or more URLs in MARC field 856.  Alternatively, it can be given
a search query on the command line; in that case, the string should be a
complete search URL as would be typed into a web browser address bar (or more
practically, copied from the browser address bar after performing some
exploratory searches in https://caltech.tind.io.  Finally, as another
alternative, it can read MARC XML input from a file when given the -f option
(/f on Windows).

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2018 by the California Institute of Technology.  This code is
open-source software released under a 3-clause BSD license.  Please see the
file "LICENSE" for more information.
'''

import os
from   os import path
import plac
import requests
import sys
try:
    from termcolor import colored
except:
    pass

import turf
from turf import entries_from_file, entries_from_search
from turf.messages import msg, color
from turf.writers import write_results
from turf.data_types import ProxyInfo, UIsettings


# Global constants.
# .............................................................................

_DEFAULT_SEARCH = 'https://caltech.tind.io/search?ln=en&p=856%3A%25&f=&sf=&so=d'
'''Default search performed if no explicit search string is given.'''


# Main program.
# ......................................................................

@plac.annotations(
    all        = ('write all entries, not only those with URLs',        'flag',   'a'),
    unchanged  = ("write entries with URLs even if they're unchanged",  'flag',   'n'),
    file       = ('read MARC from file F instead of searching tind.io', 'option', 'f'),
    output     = ('write results to the file R',                        'option', 'o'),
    pswd       = ('proxy user password',                                'option', 'p'),
    quiet      = ('do not print messages while working',                'flag',   'q'),
    start_at   = ("start with Nth record (default: start at 1)",        'option', 's'),
    total      = ('stop after processing M records (default: all)',     'option', 't'),
    user       = ('proxy user name',                                    'option', 'u'),
    no_color   = ('do not color-code terminal output',                  'flag',   'C'),
    reset      = ('reset proxy user name and password'   ,              'flag',   'R'),
    version    = ('print version info and exit',                        'flag',   'V'),
    no_keyring = ('do not use a keyring',                               'flag',   'X'),
    search     = 'complete search URL (default: none)',
)

def main(file = 'F', output = 'R', all = False, unchanged = False,
         start_at = 'N', total = 'M', user  =  'U', pswd  =  'P',
         quiet = False, no_color = False, no_keyring = False, reset = False,
         version = False, *search):
    '''Look for caltech.tind.io records containing URLs and return updated URLs.

If not given an explicit search query, it will perform a default search that
looks for records containing URLs in MARC field 856.  If given a search query
on the command line, the string should be a complete search URL as would be
typed into a web browser address bar (or more practically, copied from the
browser address bar after performing some exploratory searches in
caltech.tind.io).  If given a file using the -f option (/f on Windows), the
file should contain MARC XML content.

It is best to quote the search string, using double quotes on Windows and
single quotes on Linux/Unix, to avoid terminal shells interpreting special
characters such as question marks in the search string.  Example (for Windows):

   turf "https://caltech.tind.io/search?ln=en&p=856%3A%27ebrary%27"

By default, this program only writes out entries that have URLs in MARC field
856, and then only those whose URLs are found to dereference to a different
URL after following it.  (That is, by default, it skips writing entries whose
URLs do not change after dereferencing.)  If given the -u flag (/u on
Windows), it will write out entries with URLs even if the URLs are unchanged
after dereferencing.  If given the -a flag (/a on Windows), it will write out
all TIND entries retrieved, even those that have no URLs.

If given the -t option (/t on Windows), it will only fetch and process a
total of that many results instead of all results.  If given the -s (/s on
Windows) option, it will start at that entry instead of starting at number 1;
this is useful if searches are being done in batches or a previous search is
interrupted and you don't want to restart from 1.

If given an output file using the -o option (/o on Windows), the results will
be written to that file.  The format of the file will be deduced from the file
name extension (.csv or .xlsx).  In the absence of a file name extension, it
will default to XLSX format.  If not given an output file, the results will
only be printed to the terminal.

If the URLs to be dereferenced involve a proxy server (such as EZproxy, a
common type of proxy used by academic institutions), it will be necessary to
supply login credentials for the proxy component.  By default, Turf uses the
operating system's keyring/keychain functionality to remember the user name
and password.  If the information does not exist from a previous run, Turf
will query the user interactively for the user name and password, and (unless
the -X or /X argument is given) store them in the user's keyring/keychain so
that it does not have to ask again in the future.  It is also possible to
supply the information directly on the command line using the -u and -p
options (or /u and /p on Windows), but this is discouraged because it is
insecure on multiuser computer systems.

To reset the user name and password (e.g., if a mistake was made the last time
and the wrong credentials were stored in the keyring/keychain system), add the
-R (or /R on Windows) command-line argument to a command.  The next time
Urlup needs to use a proxy login, it will query for the user name and password
again even if an entry already exists in the keyring or keychain.

This program will print information to the terminal as it processes URLs,
unless the option -q (or /q on Windows) is given to make it more quiet.
'''

    # Our defaults are to do things like color the output, which means the
    # command line flags make more sense as negated values (e.g., "nocolor").
    # Dealing with negated variables is confusing, so turn them around here.
    colorize = 'termcolor' in sys.modules and not no_color
    use_keyring = not no_keyring

    # We use default values that provide more intuitive help text printed by
    # plac.  Rewrite the values to things we actually use.
    if file == 'F' and not path.exists('F'):
        file = None
    if output == 'R':
        output = None
    if start_at and start_at == 'N':
        start_at = 1
    if total and total == 'M':
        total = None
    if user == 'U':
        user = None
    if pswd == 'P':
        pswd = None

    # Process arguments.
    if version:
        print_version()
        sys.exit()
    if file and search:
        raise SystemExit(color('Cannot use a file and search string simultaneously',
                               'error', colorize))
    if file and not file.endswith('.xml'):
        raise SystemExit(color('"{}" does not appear to be an XML file'
                               .format(file), 'error', colorize))
    if search:
        if any(item.startswith(('-', '/')) for item in search):
            raise SystemExit(color('Command not recognized: {}'.format(search),
                                   'error', colorize))
        else:
            search = search[0]  # Compensate for how plac provides arg value.
    if not search:
        search = _DEFAULT_SEARCH
        msg('No search term provided -- will use default:', 'info', colorize)
        msg(search, 'info', colorize)
    if total and not quiet:
        msg('Will stop after getting {} records'.format(total), 'info', colorize)
    if total:
        total = int(total)
    if not output and not quiet:
        msg("No output file specified; results won't be saved.", 'warn', colorize)
    elif not quiet:
        msg('Output will be written to {}'.format(output), 'info', colorize)
        if all:
            msg('Saving all results, including those without URLs', 'info', colorize)
        else:
            msg('Saving only relevant results', 'info', colorize)
    if output:
        name, extension = path.splitext(output)
        if extension and extension.lower() not in ['.csv', '.xlsx']:
            raise SystemExit(color('"{}" has an unrecognized file extension'.format(output),
                                   'error', colorize))
        elif not extension:
            msg('"{}" has no name extension; defaulting to xlsx'.format(output),
                'warn', colorize)
    start_at = int(start_at)

    # General sanity checks.
    if not network_available():
        raise SystemExit(color('No network', 'error', colorize))

    # Let's do this thing.
    uisettings = UIsettings(colorize = colorize, quiet = quiet)
    proxyinfo = ProxyInfo(user, pswd, use_keyring, reset)
    results = []
    try:
        if file:
            input = None
            if path.exists(file):
                input = file
            elif path.exists(path.join(os.getcwd(), file)):
                input = path.join(os.getcwd(), file)
            else:
                raise SystemExit(color('Cannot find file "{}"'.format(file),
                                       'error', colorize))
            if not quiet:
                msg('Reading MARC XML from {}'.format(input), 'info', colorize)
            results = entries_from_file(input, total, start_at, proxyinfo, uisettings)
        else:
            results = entries_from_search(search, total, start_at, proxyinfo, uisettings)
    except Exception as e:
        msg('Exception encountered: {}'.format(e), 'error', colorize)
    finally:
        if not results:
            msg('No results returned.', 'warn', colorize)
        elif output:
            write_results(output, results, unchanged, all)
        else:
            print_results(results)
        if not quiet:
            msg('Done.', 'info', colorize)


# If this is windows, we want the command-line args to use slash intead
# of hyphen.

if sys.platform.startswith('win'):
    main.prefix_chars = '/'


# Miscellaneous utilities.
# ......................................................................

def print_version():
    print('{} version {}'.format(turf.__title__, turf.__version__))
    print('Author: {}'.format(turf.__author__))
    print('URL: {}'.format(turf.__url__))
    print('License: {}'.format(turf.__license__))


def print_results(results):
    for data in results:
        # Need to consume the values from the iterator in order for
        # the underlying object to print itself.
        pass


def network_available():
    '''Return True if it appears we have a network connection, False if not'''
    try:
        r = requests.get("https://www.caltech.edu")
        return True
    except requests.ConnectionError:
        return False


# Main entry point.
# ......................................................................
# The following allows users to invoke this using "python3 -m turf".

if __name__ == '__main__':
    plac.call(main)


# For Emacs users
# ......................................................................
# Local Variables:
# mode: python
# python-indent-offset: 4
# End:
