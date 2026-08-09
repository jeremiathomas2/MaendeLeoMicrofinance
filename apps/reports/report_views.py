from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from apps.audit.models import audit
from apps.reports.report_defs import HEADERS, REPORT_CATEGORIES, _rows_for
from apps.reports.utils import export


@login_required
def report_generate(request, kind):
    start = request.GET.get('start') or ''
    end = request.GET.get('end') or ''
    branch_id = request.GET.get('branch') or ''
    product_id = request.GET.get('product') or ''
    status = request.GET.get('status') or ''

    start_date = parse_date(start) if start else None
    end_date = parse_date(end) if end else None

    rows = _rows_for(kind, request, start_date, end_date, branch_id, product_id, status)
    fmt = request.GET.get('fmt', 'html')

    if fmt in ('csv', 'xlsx'):
        from django.utils import timezone
        audit(request.user, 'DATA_EXPORTED', None,
              new={'report': kind, 'format': fmt, 'rows': len(rows)}, request=request)
        return export(f'{kind}_report_{timezone.now().date()}', HEADERS.get(kind, []), rows, fmt)

    # All categories flat for rendering
    all_categories = {}
    for cat, items in REPORT_CATEGORIES.items():
        for slug, title, icon, desc in items:
            all_categories[slug] = {'title': title, 'cat': cat}
    meta = all_categories.get(kind, {})
    return render(request, 'pages/report_view.html', {
        'kind': kind,
        'title': meta.get('title', kind.replace('_', ' ').title()),
        'category': meta.get('cat', ''),
        'headers': HEADERS.get(kind, []),
        'rows': rows,
        'branches': request.user.accessible_branches(),
    })
