from django.urls import path
from .views import (
    ProductListCreateView, 
    ProductRetrieveUpdateDestroyView,

    BundleListCreateView,
    BundleDetailView,

    SupplierListCreateAPIView,
    SupplierRetrieveUpdateDeleteAPIView,

    CustomerListCreateAPIView,
    CustomerRetrieveUpdateDeleteAPIView,

    CategoryListCreateView,
    CategoryRetrieveUpdateDeleteAPIView,

    RetriveRevenueAPIView,
    RetriveProfitAPIView,
    ExcelReportAPIView,
    OrderLogAPIView,

    CompanyListCreateAPIView,
    CompanyRetrieveUpdateDeleteAPIView,

    ListOutOFStockProductAPIView,
    CountNearExpirationDateProductAPIView,

    # ExpenseTypesListCreateAPIView,
    ExpenseTypesListCreateView,
    ExpenseRetrieveUpdateDestroy,
    # ExpenseTypesRetrieveUpdateDeleteAPIView,

    OtherExpensesListCreateAPIView,
    OtherExpensesRetrieveUpdateDestroy,

    PerformaCustomerListCreateView,
    PerformaCustomerDetailView,
    PerformaPerformaListCreateView,
    PerformaPerformaDetailView,
    PerformaProductListCreateView,
    PerformaProductDetailView,

    PurchaseExpenseListCreateView,
    PurchaseExpenseDetailView,
    PurchaseProductListCreateView,
    PurchaseProductDetailView,
    PurchaseSupplierListCreateView,
    PurchaseSupplierDetailView,

    SupplierLogListView,
    ExpenseLogListView,
    SupplierReport,
    ExpenseReport,
    SupplierReportView,

    RetriveTotalProductCostAPIView,
    ProductExcelReportAPIView,

    ProductsPerSupplierAPIView,

    OrderReceiptAPIView,
    SalesPersonDashboardAPIView,
    RecentOrderLimitedAPIView,
    RetriveSalesPersonRevenueAPIView,
    RetriveTotalOrdersAPIView,

    DailySalesAPIView,
    WeeklySalesAPIView,
    MonthlySalesAPIView,
    YearlySalesAPIView,

    DailySalesEachUserAPIView,
    WeeklySalesEachUserAPIView,
    MonthlySalesEachUserAPIView,
    YearlySalesEachUserAPIView,

    ExportProductExcelAPIView,
    ImportProductExcelAPIView,

    OrderListCreatView,
    OrderDetailView,
    OrderItemListCreateView,
    OrderItemDetailView,
    OrderCreditListAPIView,
    OrderItemCreditListView,

    OrderLogListView,
    ProductLogAPIView,

    ProductWithBundleAPIView,
    ProductWithOutBundleAPIView,

)

urlpatterns = [
    path('products', ProductListCreateView.as_view(), name='products-list'),
    path('products/<pk>', ProductRetrieveUpdateDestroyView.as_view(), name='products-retrieve'),

    path('bundles/', BundleListCreateView.as_view(), name='bundle-list-create'),
    path('bundles/<int:pk>/', BundleDetailView.as_view(), name='bundle-detail'),

    path('suppliers', SupplierListCreateAPIView.as_view(), name='suppliers-list'),
    path('suppliers/<pk>', SupplierRetrieveUpdateDeleteAPIView.as_view(), name='suppliers-retrieve'),

    path('orders', OrderListCreatView.as_view(), name='orders-create'),
    path('orders/<pk>', OrderDetailView.as_view(), name='orders-retrieve'),

    path('orderitems', OrderItemListCreateView.as_view(), name='orders-items-list'),
    path('orderitems/<pk>', OrderItemDetailView.as_view(), name='orders-items-retrieve'),

    path('orders-credit', OrderCreditListAPIView.as_view(), name='orders-credit-list'),
    path('orderitems-credit', OrderItemCreditListView.as_view(), name='orders-credit-items-list'),
    path('customers', CustomerListCreateAPIView.as_view(), name='customers-list'),
    path('customers/<pk>', CustomerRetrieveUpdateDeleteAPIView.as_view(), name='customers-retrieve'),
    
    path('company', CompanyListCreateAPIView.as_view(), name='company-list'),
    path('company/<pk>', CompanyRetrieveUpdateDeleteAPIView.as_view(), name='company-retrieve'),

    path('category', CategoryListCreateView.as_view(), name='category-list'),
    path('category/<pk>', CategoryRetrieveUpdateDeleteAPIView.as_view(), name='category-retrieve'),

    path('revenue/', RetriveRevenueAPIView.as_view(), name='revenue-retrieve'),
    path('profit/', RetriveProfitAPIView.as_view(), name='profit-retrieve'),
    path('report/', ExcelReportAPIView.as_view(), name='report-retrieve'),
    path('order_log/', OrderLogAPIView.as_view(), name='order-log-retrieve'),
    path('stock/', ListOutOFStockProductAPIView.as_view(), name='stock-shortage-retrieve'),
    path('stock_count/', CountNearExpirationDateProductAPIView.as_view(), name='stock-shortage-count-retrieve'),

    path('expense_type', ExpenseTypesListCreateView.as_view(), name='expense_type-list'),
    path('expense_type/<pk>', ExpenseRetrieveUpdateDestroy.as_view(), name='expense_type-retrieve'),

    path('performa-customers/', PerformaCustomerListCreateView.as_view(), name='performa-customer-list-create'),
    path('performa-customers/<pk>', PerformaCustomerDetailView.as_view(), name='performa-customer-list-create'),
    path('performa-performas/', PerformaPerformaListCreateView.as_view(), name='performa-performas-list-create'),
    path('performa-performas/<pk>', PerformaPerformaDetailView.as_view(), name='performa-performas-list-create'),
    path('performa-products/', PerformaProductListCreateView.as_view(), name='performa-product-list-create'),
    path('performa-products/<pk>', PerformaProductDetailView.as_view(), name='performa-product-list-create'),


    path('purchase-products/', PurchaseProductListCreateView.as_view(), name='purchase-product-list-create'),
    path('purchase-products/<pk>', PurchaseProductDetailView.as_view(), name='purchase-product-list-create'),
    path('purchase-expenses/', PurchaseExpenseListCreateView.as_view(), name='purchase-expense-list-create'),
    path('purchase-expenses/<pk>', PurchaseExpenseDetailView.as_view(), name='purchase-expense-list-create'),
    path('purchase-suppliers/', PurchaseSupplierListCreateView.as_view(), name='purchase-supplier-list-create'),
    path('purchase-suppliers/<pk>', PurchaseSupplierDetailView.as_view(), name='purchase-supplier-list-create'),

    path('purchase-suppliers/<int:supplier_id>/logs', SupplierLogListView.as_view(), name='purchase-supplier-logs'),
    # path('purchase-suppliers/<int:supplier_id>/report', SupplierReport.as_view(), name='purchase-supplier-report'),
    path('purchase-suppliers/<int:supplier_id>/report', SupplierReportView.as_view(), name='purchase-supplier-report'),
    path('purchase-expenses/<int:expense_id>/logs', ExpenseLogListView.as_view(), name='purchase-expense-logs'),
    path('purchase-expenses/<int:expense_id>/report', ExpenseReport.as_view(), name='purchase-expense-report'),

    path('other_expenses', OtherExpensesListCreateAPIView.as_view(), name='other_expenses-list'),
    path('other_expenses/<pk>', OtherExpensesRetrieveUpdateDestroy.as_view(), name='other_expenses-retrieve'),
    path('product_report/', ProductExcelReportAPIView.as_view(), name='product-report-retrieve'),
    path('product_cost/', RetriveTotalProductCostAPIView.as_view(), name='total-product-cost-retrieve'),

    path('products_supplier/<pk>', ProductsPerSupplierAPIView.as_view(), name='products-per-supplier'),

    path('orders/<pk>/receipt/', OrderReceiptAPIView.as_view(), name='order-receipt'),
    path('sales-dashboard/', SalesPersonDashboardAPIView.as_view(), name='salesperson-dashboard'),
    path('recent-orders/', RecentOrderLimitedAPIView.as_view(), name='recent-orders-limited'),
    path('salesperson-revenue/', RetriveSalesPersonRevenueAPIView.as_view(), name='salesperson-revenue-retrieve'),
    path('salesperson-total-orders/', RetriveTotalOrdersAPIView.as_view(), name='total-orders-retrieve'),
    
    path('daily-sales/', DailySalesAPIView.as_view(), name='daily-sales-retrieve'),
    path('monthly-sales/', MonthlySalesAPIView.as_view(), name='monthly-sales-retrieve'),
    path('weekly-sales/', WeeklySalesAPIView.as_view(), name='weekly-sales-retrieve'),
    path('yearly-sales/', YearlySalesAPIView.as_view(), name='yearly-sales-retrieve'),

    path('daily-sales-per-user/', DailySalesEachUserAPIView.as_view(), name='daily-sales-each-user-retrieve'),
    path('weekly-sales-per-user/', WeeklySalesEachUserAPIView.as_view(), name='weekly-sales-each-user-retrieve'),
    path('monthly-sales-per-user/', MonthlySalesEachUserAPIView.as_view(), name='monthly-sales-each-user-retrieve'),
    path('yearly-sales-per-user/', YearlySalesEachUserAPIView.as_view(), name='yearly-sales-each-user-retrieve'),

    path('export/products/', ExportProductExcelAPIView.as_view(), name='export-products-excel'),
    path('import/products/', ImportProductExcelAPIView.as_view(), name='export-products-excel'),

    path('orders/<int:order_id>/logs', OrderLogListView.as_view(), name='order-logs'),
    path('product_log/', ProductLogAPIView.as_view(), name='product-log-retrieve'),

    path('product_with_bundle/', ProductWithBundleAPIView.as_view(), name='product-with-bundle-retrieve'),
    path('product_with_out_bundle/', ProductWithOutBundleAPIView.as_view(), name='product-with-out-bundle-retrieve'),
]