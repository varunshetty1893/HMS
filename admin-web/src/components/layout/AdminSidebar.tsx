import React from 'react';
import { useTheme } from '@/context/ThemeContext';
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
  const { theme } = useTheme();
  const isLight = theme === 'light';

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
      badgeColor: isLight
        ? 'bg-amber-100 text-amber-700 border border-amber-300'
        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
    },
    {
      id: 'billing' as AdminModule,
      label: 'Billing & Payments',
      icon: Receipt,
      badge: unpaidCount > 0 ? unpaidCount : undefined,
      badgeColor: isLight
        ? 'bg-rose-100 text-rose-700 border border-rose-300'
        : 'bg-rose-500/20 text-rose-300 border border-rose-500/30',
    },
    {
      id: 'tables-qr' as AdminModule,
      label: 'Tables & QR Codes',
      icon: QrCode,
    },
    {
      id: 'menu' as AdminModule,
      label: 'Menu Dishes',
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
      label: 'Restaurant Settings',
      icon: Settings,
    },
    {
      id: 'audit-logs' as AdminModule,
      label: 'Activity & Audit Logs',
      icon: ShieldAlert,
    },
  ];

  const sidebarStyle: React.CSSProperties = {
    backgroundColor: isLight ? '#FFF8ED' : '#0f172a',
    borderRightColor: isLight ? '#e4d9c8' : '#1e293b',
  };

  const brandBorderStyle: React.CSSProperties = {
    borderBottomColor: isLight ? '#e4d9c8' : '#1e293b',
  };

  const footerStyle: React.CSSProperties = {
    borderTopColor: isLight ? '#e4d9c8' : 'rgba(30,41,59,0.8)',
    color: isLight ? '#756a56' : '#64748b',
  };

  return (
    <aside
      className="w-64 shrink-0 border-r flex flex-col h-full no-print"
      style={sidebarStyle}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b" style={brandBorderStyle}>
        <img
          src="/logo.png"
          alt="Spice Hub"
          className="w-10 h-10 rounded-full shrink-0 shadow-md shadow-black/20"
        />
        <div>
          <h1 className="text-sm font-bold tracking-tight" style={{ color: isLight ? '#282820' : '#f8fafc' }}>Spice Hub</h1>
          <p className="text-[11px] font-medium" style={{ color: '#D95D2B' }}>Admin Portal</p>
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
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition cursor-pointer"
              style={
                isActive
                  ? {
                      backgroundColor: '#D95D2B',
                      color: '#ffffff',
                      boxShadow: '0 2px 8px rgba(217,93,43,0.35)',
                    }
                  : {
                      color: isLight ? '#5a5545' : '#94a3b8',
                      backgroundColor: 'transparent',
                    }
              }
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = isLight
                    ? '#fef3e2'
                    : 'rgba(30,41,59,0.6)';
                  (e.currentTarget as HTMLButtonElement).style.color = isLight ? '#282820' : '#f1f5f9';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.color = isLight ? '#5a5545' : '#94a3b8';
                }
              }}
            >
              <div className="flex items-center gap-3">
                <Icon className="w-4 h-4" style={{ color: isActive ? '#fff' : (isLight ? '#D95D2B' : '#94a3b8') }} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                    item.badgeColor || (isLight ? 'bg-gray-100 text-gray-700' : 'bg-slate-800 text-slate-200')
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
      <div className="p-4 border-t text-[11px] text-center" style={footerStyle}>
        Single Restaurant Ops v1.0
      </div>
    </aside>
  );
};
