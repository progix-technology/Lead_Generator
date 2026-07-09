import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const DashboardLayout = () => {
  const location = useLocation();
  const { user, logout } = useAuth();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: '🏠' },
    { name: 'Company Search', href: '/search', icon: '🔍' },
    { name: 'My Companies', href: '/companies', icon: '🏢' },
    { name: 'Email Campaign', href: '/campaign', icon: '✉️' },
    { name: 'Autopilot Outreach', href: '/automation', icon: '🤖' },
    { name: 'Reports', href: '/reports', icon: '📄' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
    { name: 'System Logs', href: '/logs', icon: '📋' },
  ];

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-inter">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col shadow-sm z-10">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <h1 className="text-xl font-bold text-blue-600 tracking-tight">LeadGen Pro</h1>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }`}
              >
                <span className="mr-3 text-lg">{item.icon}</span>
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Profile & Logout */}
        <div className="p-4 border-t border-gray-200 bg-gray-50/50">
          <div className="flex items-center mb-4">
            <div className="h-9 w-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm shadow-sm border border-blue-200">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="ml-3 truncate">
              <p className="text-sm font-semibold text-gray-900 truncate">{user?.first_name || 'User'}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors shadow-sm"
          >
            <span className="mr-2">🚪</span> Sign out
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-8 justify-between shadow-sm z-0">
          <h2 className="text-lg font-semibold text-gray-800">
            {navigation.find(n => n.href === location.pathname)?.name || 'Dashboard'}
          </h2>
          <div className="flex items-center space-x-4">
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-8 bg-gray-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
