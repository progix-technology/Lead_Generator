import React, { useState, useEffect, useRef } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import notificationService from '../services/notificationService';
import automationService from '../services/automationService';

const DashboardLayout = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const panelRef = useRef(null);

  // Live Autopilot City & Country Status State
  const [liveStatus, setLiveStatus] = useState({
    isRunning: false,
    activeCountry: 'USA',
    activeCity: '',
    countryFlag: '🇺🇸',
    scheduleTime: '09:00 AM - 03:00 PM IST'
  });

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: '🏠' },
    { name: 'Company Search', href: '/search', icon: '🔍' },
    { name: 'My Companies', href: '/companies', icon: '🏢' },
    { name: 'Email Campaign', href: '/campaign', icon: '✉️' },
    { name: 'Autopilot Outreach', href: '/automation', icon: '🤖' },
    { name: 'Country Templates', href: '/country-templates', icon: '🌐' },
    { name: 'Reports', href: '/reports', icon: '📄' },
    { name: 'Settings', href: '/settings', icon: '⚙️' },
    { name: 'System Logs', href: '/logs', icon: '📋' },
  ];

  // Poll live country schedule and active city progress
  useEffect(() => {
    const checkLiveTarget = async () => {
      // Calculate active country schedule based on current IST time
      const now = new Date();
      // IST offset is UTC+5:30 -> 330 minutes
      const istTime = new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60000);
      const hours = istTime.getHours();

      let country = 'USA';
      let flag = '🇺🇸';
      let timeSlot = '09:00 AM - 03:00 PM IST';

      if (hours >= 15 && hours < 21) {
        country = 'UK';
        flag = '🇬🇧';
        timeSlot = '03:00 PM - 09:00 PM IST';
      } else if (hours >= 21 || hours < 3) {
        country = 'Dubai (UAE)';
        flag = '🇦🇪';
        timeSlot = '09:00 PM - 03:00 AM IST';
      }

      let isRunning = false;
      let activeCity = '';

      try {
        const prog = await automationService.getProgress();
        if (prog) {
          isRunning = prog.is_running === true;
          
          if (prog.active_country) {
            country = prog.active_country === 'UAE' ? 'Dubai (UAE)' : prog.active_country;
            flag = country === 'UK' ? '🇬🇧' : country.includes('UAE') ? '🇦🇪' : '🇺🇸';
          }
          
          if (prog.active_schedule_time) {
            timeSlot = prog.active_schedule_time;
          }
          
          if (prog.active_city) {
            activeCity = prog.active_city;
          } else if (prog.current_query) {
            const parts = prog.current_query.split(' in ');
            if (parts.length > 1) {
              activeCity = parts[1];
            } else {
              activeCity = prog.current_query;
            }
          }
        }
      } catch (e) {}

      setLiveStatus({
        isRunning,
        activeCountry: country,
        activeCity: activeCity || (country === 'UK' ? 'London, England' : country.includes('UAE') ? 'Dubai, UAE' : 'New York, NY'),
        countryFlag: flag,
        scheduleTime: timeSlot
      });
    };

    checkLiveTarget();
    const interval = setInterval(checkLiveTarget, 15000); // refresh every 15 seconds
    return () => clearInterval(interval);
  }, []);

  // Fetch notifications periodically
  useEffect(() => {
    const fetchNotifs = async () => {
      try {
        const data = await notificationService.getNotifications();
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      } catch (err) {
        // Silently ignore fetch errors for notifications
      }
    };

    fetchNotifs();
    const interval = setInterval(fetchNotifs, 60000);
    return () => clearInterval(interval);
  }, []);

  // Close popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setShowNotifPanel(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleTogglePanel = async () => {
    const opening = !showNotifPanel;
    setShowNotifPanel(opening);
    if (opening) {
      try {
        const data = await notificationService.getNotifications();
        setNotifications(data.notifications || []);
        setUnreadCount(data.unread_count || 0);
      } catch (err) {}
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {}
  };

  const handleClearAll = async () => {
    try {
      await notificationService.clearAll();
      setNotifications([]);
      setUnreadCount(0);
    } catch (err) {}
  };

  const getLevelStyles = (level) => {
    switch (level) {
      case 'error': return { bg: 'bg-red-50', border: 'border-red-200', icon: '🔴', text: 'text-red-700' };
      case 'warning': return { bg: 'bg-amber-50', border: 'border-amber-200', icon: '🟡', text: 'text-amber-700' };
      case 'info': return { bg: 'bg-blue-50', border: 'border-blue-200', icon: '🔵', text: 'text-blue-700' };
      default: return { bg: 'bg-gray-50', border: 'border-gray-200', icon: '⚪', text: 'text-gray-700' };
    }
  };

  const getSourceLabel = (source) => {
    switch (source) {
      case 'autopilot': return 'Autopilot';
      case 'email': return 'Email';
      case 'api': return 'API';
      default: return 'System';
    }
  };

  const formatTime = (timestamp) => {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString();
    } catch {
      return '';
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 text-gray-900 font-inter">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col shadow-sm z-10">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <h1 className="text-[15px] font-black text-gray-900 tracking-wider uppercase">PROGIX TECHNOLOGY</h1>
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
        {/* Top Header Navbar */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-8 justify-between shadow-sm z-20">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-gray-800">
              {navigation.find(n => n.href === location.pathname)?.name || 'Dashboard'}
            </h2>

            {/* Live Autopilot Active Country & City Badge */}
            <div className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold transition-all shadow-xs ${
              liveStatus.isRunning 
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200' 
                : 'bg-indigo-50 text-indigo-800 border-indigo-200'
            }`}>
              <span className="relative flex h-2.5 w-2.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  liveStatus.isRunning ? 'bg-emerald-400' : 'bg-indigo-400'
                }`}></span>
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  liveStatus.isRunning ? 'bg-emerald-500' : 'bg-indigo-500'
                }`}></span>
              </span>
              <span className="text-sm">{liveStatus.countryFlag}</span>
              <span>
                {liveStatus.isRunning ? (
                  <span>LIVE TARGET: <span className="font-extrabold text-emerald-950">{liveStatus.activeCity}</span> ({liveStatus.activeCountry})</span>
                ) : (
                  <span>ACTIVE SLOT: <span className="font-extrabold text-indigo-950">{liveStatus.activeCountry}</span> ({liveStatus.scheduleTime})</span>
                )}
              </span>
            </div>
          </div>
          
          {/* Notification Bell */}
          <div className="relative" ref={panelRef}>
            <button
              onClick={handleTogglePanel}
              className="relative p-2 rounded-full text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-all focus:outline-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {/* Unread badge */}
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 flex items-center justify-center h-5 w-5 text-[10px] font-bold text-white bg-red-500 rounded-full shadow-sm animate-pulse">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notification Dropdown Panel */}
            {showNotifPanel && (
              <div className="absolute right-0 top-12 w-96 bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden z-50"
                   style={{ animation: 'fadeInDown 0.2s ease-out' }}>
                {/* Panel Header */}
                <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-slate-800 to-slate-900 text-white">
                  <div className="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                    </svg>
                    <h3 className="text-sm font-bold">System Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="bg-red-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full">{unreadCount} new</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {unreadCount > 0 && (
                      <button onClick={handleMarkAllRead} className="text-[11px] text-blue-300 hover:text-white transition-colors px-2 py-1 rounded hover:bg-white/10">
                        Mark read
                      </button>
                    )}
                    {notifications.length > 0 && (
                      <button onClick={handleClearAll} className="text-[11px] text-red-300 hover:text-white transition-colors px-2 py-1 rounded hover:bg-white/10">
                        Clear all
                      </button>
                    )}
                  </div>
                </div>

                {/* Panel Body */}
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-10 text-gray-400">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 mb-2 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="text-sm font-medium">All clear!</p>
                      <p className="text-xs mt-1">No system errors or warnings.</p>
                    </div>
                  ) : (
                    notifications.map((notif, idx) => {
                      const styles = getLevelStyles(notif.level);
                      return (
                        <div
                          key={notif.id || idx}
                          className={`px-4 py-3 border-b border-gray-100 last:border-b-0 transition-colors ${!notif.read ? styles.bg : 'bg-white hover:bg-gray-50'}`}
                        >
                          <div className="flex items-start gap-2.5">
                            <span className="text-sm mt-0.5 flex-shrink-0">{styles.icon}</span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-0.5">
                                <span className={`text-[10px] font-bold uppercase tracking-wider ${styles.text}`}>
                                  {getSourceLabel(notif.source)}
                                </span>
                                <span className="text-[10px] text-gray-400 flex-shrink-0">
                                  {formatTime(notif.timestamp)}
                                </span>
                              </div>
                              <p className="text-xs text-gray-700 leading-relaxed break-words">
                                {notif.message}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-8 bg-gray-50">
          <Outlet />
        </main>
      </div>

      {/* Animation keyframes */}
      <style>{`
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default DashboardLayout;
