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


# Main module code.
# ......................................................................

# Results are assumed to be a list of the form
#   (id, [UrlData, UrlData, ...])
# where "UrlData" is the UrlData structure retured by urlup for each
# URL found in field 856 (if any are found) for the MARC XML record.

def write_results(filename, results, all):
    if not all:
        results = only_with_urls(results)
    # Iterate through the results and find the one with the largest number of
    # URLs, so we can communicate that to the functions called.
    max_urls = 0
    for data in results:
        max_urls = max(len(data[1]), max_urls)
    # Call on appropriate functions for the desired output format.
    name, extension = os.path.splitext(filename)
    if extension.lower() == '.csv':
        write_csv(filename, results, max_urls)
    else:
        write_xls(filename, results, max_urls)


def write_csv(filename, results, num_urls):
    with open(filename, 'w', newline='') as out:
        out.write('TIND record id' + ',Original URL,Final URL'*num_urls + '\n')
        csvwriter = csv.writer(out, delimiter=',')
        for data in results:
            row = [data[0]]
            for url_data in data[1]:
                row.append(url_data.original)
                if url_data.error:
                    row.append('(error: {})'.format(url_data.error))
                else:
                    row.append(url_data.final or '')
            csvwriter.writerow(row)


def write_xls(filename, results, num_urls):
    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    # Create some things we reuse below.
    bold_font = Font(bold = True, underline = "single")
    hyperlink_style = Font(underline='single', color='0563C1')
    error_style = Font(color='aa2222')

    # Create a sheet in a new workbook and give it a distinctive style.
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = 'Results'
    sheet.sheet_properties.tabColor = 'f7ba0b'

    # Set the headings and format them a little bit.
    header_row = ['TIND record id'] + ['Original URL', 'Final URL']*num_urls
    sheet.append(header_row)
    for cell in sheet["1:1"]:
        cell.font = bold_font

    # Set the widths of the different columngs to something more convenient.
    col_letter = get_column_letter(1)
    sheet.column_dimensions[col_letter].width = 15
    for idx in range(2, num_urls*2 + 2):
        col_letter = get_column_letter(idx)
        sheet.column_dimensions[col_letter].width = 80

    for row, data in enumerate(results, 2):
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
