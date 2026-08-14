from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import (
    MaendeleoLoginView, mark_notifications_read, profile_page, profile_photo_upload, splash,
    users_page, users_toggle_status,
)
from apps.accounting.views import accounting_page, expense_approve, expense_create, journal_create, statements
from apps.audit.views import audit_export, audit_page
from apps.cash_management.views import cash_page, session_close, session_open, session_reconcile
from apps.collections.views import collection_action_create, collection_action_resolve, collections_page
from apps.customers.views import (
    customer_detail, customer_document_upload, customer_document_verify, customer_register,
    customer_edit, customer_toggle_status, customers_page, group_add_member, group_create,
)
from apps.loans.views import (
    loan_application_create, loan_application_detail, loan_application_submit, loan_approve,
    loan_assess, loan_disburse, loan_reject, loan_repay, loans_page, repayment_reverse,
)
from apps.organization.views import branch_create, branch_delete, branch_edit, branches_page, settings_page, settings_save
from apps.reports.report_views import report_generate
from apps.reports.views import dashboard, reports_page
from apps.savings.views import savings_deposit, savings_open, savings_page, savings_withdraw

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.api.urls')),

    path('', splash, name='splash'),
    path('login/', MaendeleoLoginView.as_view(), name='login'),
    path('logout/', __import__('django.contrib.auth.views', fromlist=['LogoutView']).LogoutView.as_view(), name='logout'),
    path('profile/', profile_page, name='profile_page'),
    path('profile/photo/', profile_photo_upload, name='profile_photo_upload'),
    path('notifications/read/', mark_notifications_read, name='mark_notifications_read'),

    path('dashboard/', dashboard, name='dashboard'),

    path('customers/', customers_page, name='customers_page'),
    path('customers/register/', customer_register, name='customer_register'),
    path('customers/<int:pk>/', customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', customer_edit, name='customer_edit'),
    path('customers/<int:pk>/status/', customer_toggle_status, name='customer_toggle_status'),
    path('customers/<int:pk>/documents/upload/', customer_document_upload, name='customer_document_upload'),
    path('documents/<int:pk>/verify/', customer_document_verify, name='customer_document_verify'),
    path('groups/create/', group_create, name='group_create'),
    path('groups/<int:pk>/add-member/', group_add_member, name='group_add_member'),

    path('loans/', loans_page, name='loans_page'),
    path('loans/new/', loan_application_create, name='loan_application_create'),
    path('loans/<int:pk>/', loan_application_detail, name='loan_application_detail'),
    path('loans/<int:pk>/submit/', loan_application_submit, name='loan_application_submit'),
    path('loans/<int:pk>/assess/', loan_assess, name='loan_assess'),
    path('loans/<int:pk>/approve/', loan_approve, name='loan_approve'),
    path('loans/<int:pk>/reject/', loan_reject, name='loan_reject'),
    path('loans/<int:pk>/disburse/', loan_disburse, name='loan_disburse'),
    path('loans/<int:pk>/repay/', loan_repay, name='loan_repay'),
    path('repayments/<int:pk>/reverse/', repayment_reverse, name='repayment_reverse'),

    path('savings/', savings_page, name='savings_page'),
    path('savings/open/', savings_open, name='savings_open'),
    path('savings/deposit/', savings_deposit, name='savings_deposit'),
    path('savings/withdraw/', savings_withdraw, name='savings_withdraw'),

    path('collections/', collections_page, name='collections_page'),
    path('collections/action/', collection_action_create, name='collection_action_create'),
    path('collections/action/<int:pk>/resolve/', collection_action_resolve, name='collection_action_resolve'),

    path('cash/', cash_page, name='cash_page'),
    path('cash/session/open/', session_open, name='session_open'),
    path('cash/session/<int:pk>/reconcile/', session_reconcile, name='session_reconcile'),
    path('cash/session/<int:pk>/close/', session_close, name='session_close'),

    path('accounting/', accounting_page, name='accounting_page'),
    path('accounting/journal/new/', journal_create, name='journal_create'),
    path('accounting/expense/new/', expense_create, name='expense_create'),
    path('accounting/expense/<int:pk>/action/', expense_approve, name='expense_approve'),
    path('accounting/statements/<str:statement>/', statements, name='statements'),

    path('reports/', reports_page, name='reports_page'),
    path('reports/<str:kind>/', report_generate, name='report_generate'),

    path('audit/', audit_page, name='audit_page'),
    path('audit/export/', audit_export, name='audit_export'),

    path('users/', users_page, name='users_page'),
    path('users/<int:user_id>/toggle/', users_toggle_status, name='users_toggle_status'),

    path('branches/', branches_page, name='branches_page'),
    path('branches/add/', branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/', branch_edit, name='branch_edit'),
    path('branches/<int:pk>/delete/', branch_delete, name='branch_delete'),

    path('settings/', settings_page, name='settings_page'),
    path('settings/save/', settings_save, name='settings_save'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
