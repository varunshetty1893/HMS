import React, { useState } from 'react';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { AdminModule, AdminSidebar } from '@/components/layout/AdminSidebar';
import { TopStatusHeader } from '@/components/layout/TopStatusHeader';
import { LoginPage } from '@/pages/LoginPage';
import { OverviewPage } from '@/pages/OverviewPage';
import { MenuManagementPage } from '@/pages/MenuManagementPage';
import { TablesAndQrPage } from '@/pages/TablesAndQrPage';
import { LiveOrdersPage } from '@/pages/LiveOrdersPage';
import { BillingAndPaymentsPage } from '@/pages/BillingAndPaymentsPage';
import { StaffManagementPage } from '@/pages/StaffManagementPage';
import { ReportsPage } from '@/pages/ReportsPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { AuditLogsPage } from '@/pages/AuditLogsPage';

const AdminDashboard: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [currentModule, setCurrentModule] = useState<AdminModule>('overview');

  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-slate-950 text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium">Initializing Admin Portal...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onSuccess={() => setCurrentModule('overview')} />;
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950">
      {/* 8-Section Navigation Sidebar */}
      <AdminSidebar
        currentModule={currentModule}
        onSelectModule={(mod) => setCurrentModule(mod)}
      />

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <TopStatusHeader />
        <main className="flex-1 overflow-y-auto bg-slate-950/60">
          {currentModule === 'overview' && <OverviewPage onNavigate={(mod) => setCurrentModule(mod)} />}
          {currentModule === 'menu' && <MenuManagementPage />}
          {currentModule === 'tables-qr' && <TablesAndQrPage />}
          {currentModule === 'live-orders' && <LiveOrdersPage />}
          {currentModule === 'billing' && <BillingAndPaymentsPage />}
          {currentModule === 'staff' && <StaffManagementPage />}
          {currentModule === 'reports' && <ReportsPage />}
          {currentModule === 'settings' && <SettingsPage />}
          {currentModule === 'audit-logs' && <AuditLogsPage />}
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AdminDashboard />
    </AuthProvider>
  );
};

export default App;
