'''TIND.io URL Fixer: fix up URLs of entries in caltech.tind.io.

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
alternative, it can read MARC XML input from a file when given the -f option.

Turf is a command-line application.  On Linux and macOS systems, the
installation _should_ place a new program on your shell's search path, so
that you can start Turf with a simple shell command:

    turf

If that fails because the shell cannot find the command, you should be able
to run it using the alternative approach:

   python3 -m turf

When run without any arguments, Turf will execute a search in
https://caltech.tind.io that looks for records containing URLs in MARC field
856.  It will dereference each URL it finds and print to the terminal each
record's identifier, the original URL(s), the final URL(s), and any errors
encountered.  Turf can also accept an explicit search query in the form of a
complete search URL as would be typed into a web browser address bar (or more
practically, copied from the browser address bar after performing some
exploratory searches in caltech.tind.io).

It accepts various command-line arguments.  To get information about the
available options, use the -h argument:

   turf -h
'''

from .__version__ import __version__, __title__, __description__, __url__
from .__version__ import __author__, __email__
from .__version__ import __license__, __copyright__

# Main modules.
from .turf import entries_from_search, entries_from_file

# Supporting modules.
from .messages import msg, color
