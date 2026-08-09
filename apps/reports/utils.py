"""Report export helpers: CSV and Excel (SRS section 54)."""

import csv
import io


def csv_response(filename, headers, rows):
    from django.http import HttpResponse
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([('' if v is None else v) for v in row])
    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    return response


def excel_response(filename, headers, rows):
    from django.http import HttpResponse
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = filename[:28]
    ws.append(headers)
    for row in rows:
        ws.append([('' if v is None else v) for v in row])
    buffer = io.BytesIO()
    wb.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    return response


def export(filename, headers, rows, fmt='csv'):
    if fmt == 'xlsx':
        return excel_response(filename, headers, rows)
    return csv_response(filename, headers, rows)
