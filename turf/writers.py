'''
writers.py: output-writing utilities for Turf.

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2018 by the California Institute of Technology.  This code is
open-source software released under a 3-clause BSD license.  Please see the
file "LICENSE" for more information.
'''

import csv
import os
import sys

try:
    thisdir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(thisdir, '../..'))
except:
    sys.path.append('../..')

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
    def log(s, *other_args): logger.debug('writers: ' + s.format(*other_args))


# Global constants.
# .............................................................................

_NUM_URLS = 5


# Main module code.
# ......................................................................

# Results are assumed to be a list of the form
#   (id, [UrlData, UrlData, ...])
# where "UrlData" is the UrlData structure retured by urlup for each
# URL found in field 856 (if any are found) for the MARC XML record.

def write_results(filename, results, all):
    # Call on appropriate functions for the desired output format.
    name, extension = os.path.splitext(filename)
    if extension.lower() == '.csv':
        write_csv(filename, results, all)
    else:
        write_xls(filename, results, all)


def write_csv(filename, results, all):
    file = open(filename, 'w', newline='')
    file.write('TIND record id' + ',Original URL,Final URL'*_NUM_URLS + '\n')
    csvwriter = csv.writer(file, delimiter=',')
    try:
        for data in results:
            row = [data[0]]
            if __debug__: log('writing row for {}'.format(data[0]))
            for url_data in data[1]:
                row.append(url_data.original)
                if url_data.error:
                    row.append('(error: {})'.format(url_data.error))
                else:
                    row.append(url_data.final or '')
            csvwriter.writerow(row)
    except KeyboardInterrupt:
        msg('Interrupted -- closing "{}" and exiting'.format(filename))
    except Exception:
        raise
    finally:
        file.close()


def write_xls(filename, results, all):
    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    # Create some things we reuse below.
    bold_style = Font(bold = True, underline = "single")
    hyperlink_style = Font(underline='single', color='0563C1')
    error_style = Font(color='aa2222')

    # Create a sheet in a new workbook and give it a distinctive style.
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = 'Results'
    sheet.sheet_properties.tabColor = 'f7ba0b'

    # Set the headings and format them a little bit.
    header_row = ['TIND record id'] + ['Original URL', 'Final URL']*_NUM_URLS
    sheet.append(header_row)
    for cell in sheet["1:1"]:
        cell.font = bold_style

    # Set the widths of the different columngs to something more convenient.
    column = get_column_letter(1)
    sheet.column_dimensions[column].width = 15
    for idx in range(2, _NUM_URLS*2 + 2):
        column = get_column_letter(idx)
        sheet.column_dimensions[column].width = 80

    try:
        for row, data in enumerate(results, 2):
            if __debug__: log('writing row {}'.format(row))
            tind_id = data[0]
            sheet.cell(row, 1).value = tind_id
            sheet.cell(row, 1).hyperlink = tind_entry_link(tind_id)
            sheet.cell(row, 1).font = hyperlink_style

            col = 2
            for url_data in data[1]:
                sheet.cell(row, col).value = url_data.original
                sheet.cell(row, col).hyperlink = url_data.original
                sheet.cell(row, col).font = hyperlink_style
                col += 1
                if url_data.error:
                    sheet.cell(row, col).value = '(error: {})'.format(url_data.error)
                    sheet.cell(row, col).font = error_style
                else:
                    sheet.cell(row, col).value = url_data.final
                    sheet.cell(row, col).hyperlink = (url_data.final or '')
                    sheet.cell(row, col).font = hyperlink_style
                col += 1
    except KeyboardInterrupt:
        msg('Interrupted -- closing "{}" and exiting'.format(filename))
    except Exception:
        raise
    finally:
        wb.save(filename = filename)



# Miscellaneous utilities.
# ......................................................................

def only_with_urls(results):
    return [r for r in results if r[1]]


def tind_entry_link(tind_id):
    return 'https://caltech.TIND.io/record/{}'.format(tind_id)


# For Emacs users
# ......................................................................
# Local Variables:
# mode: python
# python-indent-offset: 4
# End:
