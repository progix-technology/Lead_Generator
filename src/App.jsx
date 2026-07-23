import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import DashboardLayout from './layouts/DashboardLayout';

// Import all your existing pages from Phase 1
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CompanySearch from './pages/CompanySearch';
import Companies from './pages/Companies';
import LeadDetails from './pages/LeadDetails';
import EmailCampaign from './pages/EmailCampaign';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Logs from './pages/Logs';
import AutomatedCampaigns from './pages/AutomatedCampaigns';
import CountryTemplates from './pages/CountryTemplates';
import WebsiteAudit from './pages/WebsiteAudit';

// A wrapper component that checks if the user is authenticated
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-white bg-slate-900">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

const App = () => {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected Routes (Wrapped in DashboardLayout) */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          {/* Default route redirects to dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />

          <Route path="dashboard" element={<Dashboard />} />
          <Route path="search" element={<CompanySearch />} />
          <Route path="companies" element={<Companies />} />
          <Route path="lead-details" element={<LeadDetails />} />
          <Route path="campaign" element={<EmailCampaign />} />
          <Route path="country-templates" element={<CountryTemplates />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="logs" element={<Logs />} />
          <Route path="automation" element={<AutomatedCampaigns />} />
          <Route path="audit" element={<WebsiteAudit />} />
        </Route>

        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
};

export default App;
