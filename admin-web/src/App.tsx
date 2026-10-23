import React, { Suspense, lazy, useState } from 'react';
import { ThemeProvider } from '@/context/ThemeContext';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { AdminModule, AdminSidebar } from '@/components/layout/AdminSidebar';
import { TopStatusHeader } from '@/components/layout/TopStatusHeader';
import { LoginPage } from '@/pages/LoginPage';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

// Route-level code splitting: each module is downloaded when first opened.
const OverviewPage = lazy(() => import('@/pages/OverviewPage').then((m) => ({ default: m.OverviewPage })));
const MenuManagementPage = lazy(() => import('@/pages/MenuManagementPage').then((m) => ({ default: m.MenuManagementPage })));
const TablesAndQrPage = lazy(() => import('@/pages/TablesAndQrPage').then((m) => ({ default: m.TablesAndQrPage })));
const LiveOrdersPage = lazy(() => import('@/pages/LiveOrdersPage').then((m) => ({ default: m.LiveOrdersPage })));
const BillingAndPaymentsPage = lazy(() => import('@/pages/BillingAndPaymentsPage').then((m) => ({ default: m.BillingAndPaymentsPage })));
const StaffManagementPage = lazy(() => import('@/pages/StaffManagementPage').then((m) => ({ default: m.StaffManagementPage })));
const ReportsPage = lazy(() => import('@/pages/ReportsPage').then((m) => ({ default: m.ReportsPage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const ChangePasswordPage = lazy(() => import('@/pages/ChangePasswordPage').then((m) => ({ default: m.ChangePasswordPage })));
const AuditLogsPage = lazy(() => import('@/pages/AuditLogsPage').then((m) => ({ default: m.AuditLogsPage })));

const ModuleFallback: React.FC = () => (
  <div className="h-full w-full flex items-center justify-center" style={{ color: 'var(--text-secondary)' }}>
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--spice-orange)', borderTopColor: 'transparent' }} />
      <span className="text-sm font-medium">Loading...</span>
    </div>
  </div>
);

const AdminDashboard: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [currentModule, setCurrentModule] = useState<AdminModule>('overview');

  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center" style={{ backgroundColor: 'var(--bg-base)', color: 'var(--text-secondary)' }}>
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: 'var(--spice-orange)', borderTopColor: 'transparent' }} />
          <span className="text-sm font-medium">Initializing Admin Portal...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onSuccess={() => setCurrentModule('overview')} />;
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden" style={{ backgroundColor: 'var(--bg-base)' }}>
      {/* 8-Section Navigation Sidebar */}
      <AdminSidebar
        currentModule={currentModule}
        onSelectModule={(mod) => setCurrentModule(mod)}
      />

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <TopStatusHeader />
        <main className="flex-1 overflow-y-auto" style={{ backgroundColor: 'var(--bg-base)' }}>
          <Suspense fallback={<ModuleFallback />}>
          {currentModule === 'overview' && <OverviewPage onNavigate={(mod) => setCurrentModule(mod)} />}
          {currentModule === 'menu' && <MenuManagementPage />}
          {currentModule === 'tables-qr' && <TablesAndQrPage />}
          {currentModule === 'live-orders' && <LiveOrdersPage />}
          {currentModule === 'billing' && <BillingAndPaymentsPage />}
          {currentModule === 'staff' && <StaffManagementPage />}
          {currentModule === 'reports' && <ReportsPage />}
          {currentModule === 'settings' && <SettingsPage />}
          {currentModule === 'audit-logs' && <AuditLogsPage />}
          {currentModule === 'account' && <ChangePasswordPage />}
          </Suspense>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ErrorBoundary fallbackTitle="An unexpected admin interface error occurred">
          <AdminDashboard />
        </ErrorBoundary>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
