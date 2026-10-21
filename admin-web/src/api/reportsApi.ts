import { apiClient } from './client';
import {
  AdminDashboardKPIs,
  CancelledRejectedReportItem,
  DailySalesSummary,
  KitchenActivityReportItem,
  OrderReportItem,
  OrderStatusReportItem,
  PaymentMethodReportItem,
  PaymentTransactionReportItem,
  PopularDishReportItem,
  RevenueTimeSeriesItem,
  TableUsageReportItem,
  UnavailableDishReportItem,
  WaiterActivityReportItem,
} from '@/types/api';

export const reportsApi = {
  getDashboardKpis: async (): Promise<AdminDashboardKPIs> => {
    return apiClient<AdminDashboardKPIs>('/admin/dashboard');
  },

  getDailySales: async (from?: string, to?: string): Promise<DailySalesSummary[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<DailySalesSummary[]>(`/admin/reports/daily-sales?${params.toString()}`);
  },

  getPaymentTransactions: async (from?: string, to?: string): Promise<PaymentTransactionReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<PaymentTransactionReportItem[]>(`/admin/reports/payment-transactions?${params.toString()}`);
  },

  getOrdersReport: async (
    from?: string,
    to?: string,
    status?: string,
    source?: string
  ): Promise<OrderReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    if (status) params.append('status', status);
    if (source) params.append('source', source);
    return apiClient<OrderReportItem[]>(`/admin/reports/orders?${params.toString()}`);
  },

  getPopularDishes: async (
    from?: string,
    to?: string,
    limit = 50
  ): Promise<PopularDishReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    params.append('limit', String(limit));
    return apiClient<PopularDishReportItem[]>(`/admin/reports/popular-dishes?${params.toString()}`);
  },

  getRevenueSeries: async (from?: string, to?: string): Promise<RevenueTimeSeriesItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<RevenueTimeSeriesItem[]>(`/admin/reports/revenue?${params.toString()}`);
  },

  getPaymentMethods: async (from?: string, to?: string): Promise<PaymentMethodReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<PaymentMethodReportItem[]>(`/admin/reports/payment-methods?${params.toString()}`);
  },

  getTableUsage: async (from?: string, to?: string): Promise<TableUsageReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<TableUsageReportItem[]>(`/admin/reports/table-usage?${params.toString()}`);
  },

  getOrderStatus: async (from?: string, to?: string): Promise<OrderStatusReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<OrderStatusReportItem[]>(`/admin/reports/order-status?${params.toString()}`);
  },

  getUnavailableDishes: async (): Promise<UnavailableDishReportItem[]> => {
    return apiClient<UnavailableDishReportItem[]>('/admin/reports/unavailable-dishes');
  },

  getCancelledRejected: async (from?: string, to?: string): Promise<CancelledRejectedReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<CancelledRejectedReportItem[]>(`/admin/reports/cancelled-rejected?${params.toString()}`);
  },

  getWaiterActivity: async (from?: string, to?: string): Promise<WaiterActivityReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<WaiterActivityReportItem[]>(`/admin/reports/waiter-activity?${params.toString()}`);
  },

  getKitchenActivity: async (from?: string, to?: string): Promise<KitchenActivityReportItem[]> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<KitchenActivityReportItem[]>(`/admin/reports/kitchen-activity?${params.toString()}`);
  },

  exportSalesCsv: async (from?: string, to?: string): Promise<string> => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    return apiClient<string>(`/admin/reports/export.csv?${params.toString()}`);
  },
};
