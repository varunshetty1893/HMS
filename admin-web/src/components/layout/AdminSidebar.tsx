import React from 'react';
import {
  LayoutDashboard,
  UtensilsCrossed,
  QrCode,
  Flame,
  Receipt,
  Users,
  BarChart3,
  Settings,
  ShieldAlert,
} from 'lucide-react';

export type AdminModule =
  | 'overview'
  | 'menu'
  | 'tables-qr'
  | 'live-orders'
  | 'billing'
  | 'staff'
  | 'reports'
  | 'settings'
  | 'audit-logs';

interface AdminSidebarProps {
  currentModule: AdminModule;
  onSelectModule: (module: AdminModule) => void;
  unpaidCount?: number;
  activeOrdersCount?: number;
}

export const AdminSidebar: React.FC<AdminSidebarProps> = ({
  currentModule,
  onSelectModule,
  unpaidCount = 0,
  activeOrdersCount = 0,
}) => {
  const navItems = [
    {
      id: 'overview' as AdminModule,
      label: 'Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'live-orders' as AdminModule,
      label: 'Live Orders',
      icon: Flame,
      badge: activeOrdersCount > 0 ? activeOrdersCount : undefined,
      badgeColor: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
    },
    {
      id: 'billing' as AdminModule,
      label: 'Billing & Settle',
      icon: Receipt,
      badge: unpaidCount > 0 ? unpaidCount : undefined,
      badgeColor: 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
    },
    {
      id: 'tables-qr' as AdminModule,
      label: 'Tables & QR',
      icon: QrCode,
    },
    {
      id: 'menu' as AdminModule,
      label: 'Menu Catalog',
      icon: UtensilsCrossed,
    },
    {
      id: 'staff' as AdminModule,
      label: 'Staff Accounts',
      icon: Users,
    },
    {
      id: 'reports' as AdminModule,
      label: 'Sales & Reports',
      icon: BarChart3,
    },
    {
      id: 'settings' as AdminModule,
      label: 'Settings',
      icon: Settings,
    },
    {
      id: 'audit-logs' as AdminModule,
      label: 'Audit Viewer',
      icon: ShieldAlert,
    },
  ];

  return (
    <aside className="w-64 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-full no-print">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#D95D2B] to-[#EB7444] flex items-center justify-center text-white font-black shadow-lg shadow-orange-600/30">
          🌶️
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-tight text-white">HMS Admin</h1>
          <p className="text-[11px] text-[#EB7444] font-medium">SpiceHub Ops</p>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentModule === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectModule(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition cursor-pointer ${
                isActive
                  ? 'bg-[#D95D2B] text-white shadow-md shadow-orange-600/25 font-semibold'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                    item.badgeColor || 'bg-slate-800 text-slate-200'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/80 text-[11px] text-slate-500 text-center">
        Single Restaurant Ops v1.0
      </div>
    </aside>
  );
};
