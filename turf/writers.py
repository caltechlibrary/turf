'''
writers.py: output-writing utilities for Turf

Authors
-------

Michael Hucka <mhucka@caltech.edu>

Copyright
---------

Copyright (c) 2018 by the California Institute of Technology.  This code is
open-source software.  Please see the file "LICENSE" for more information.
'''

import csv
import os


# Main module code.
# ......................................................................

def write_results(filename, results, all):
    if not all:
        results = only_with_urls(results)
    name, extension = os.path.splitext(filename)
    if extension.lower() == '.csv':
        write_csv(filename, results)
    else:
        write_xls(filename, results)


def write_csv(filename, results):
    with open(filename, 'w', newline='') as out:
        out.write('TIND record id,Original URL,Updated URL\n')
        csvwriter = csv.writer(out, delimiter=',')
        csvwriter.writerows(results)


def write_xls(filename, results):
    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    # Create some things we reuse below.
    bold_font = Font(bold = True, underline = "single")
    hyperlink_style = Font(underline='single', color='0563C1')

    # Create a sheet in a new workbook and give it a distinctive style.
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = 'Results'
    sheet.sheet_properties.tabColor = 'f7ba0b'

    # Set the headings and format them a little bit.
    sheet.append(['TIND record id', 'Original URL', 'Updated URL'])
    for cell in sheet["1:1"]:
        cell.font = bold_font

    # Set the widths of the different columngs to something more convenient.
    col_letter = get_column_letter(1)
    sheet.column_dimensions[col_letter].width = 15
    col_letter = get_column_letter(2)
    sheet.column_dimensions[col_letter].width = 100
    col_letter = get_column_letter(3)
    sheet.column_dimensions[col_letter].width = 100
    for row, data in enumerate(results, 2):
        tind_id = data[0]
        sheet.cell(row, 1).value = tind_id
        sheet.cell(row, 1).hyperlink = tind_entry_link(tind_id)
        sheet.cell(row, 1).font = hyperlink_style

        for col, value in enumerate(data[1:], 1):
            sheet.cell(row, col + 1).value = data[col]
            sheet.cell(row, col + 1).hyperlink = data[col]
            sheet.cell(row, col + 1).font = hyperlink_style
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
