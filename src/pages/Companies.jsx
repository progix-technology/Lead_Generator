import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import companyService from '../services/companyService';

const Companies = () => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filtering States - Defaults to 'Pending' so the user immediately focuses on leads to email
  const [statusFilter, setStatusFilter] = useState('Pending');
  const [emailFilter, setEmailFilter] = useState('all');

  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      setLoading(true);
      // Fetch the first 100 companies from the backend
      const data = await companyService.getCompanies(0, 100);
      setCompanies(data.data); // data.data because our backend returns { total_count, data: [...] }
    } catch (err) {
      setError('Failed to load companies. Please try again later.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredCompanies = React.useMemo(() => {
    return companies.filter(c => {
      // Status check
      if (statusFilter !== 'all') {
        const status = c.status || 'Pending';
        if (status !== statusFilter) return false;
      }
      // Email existence check
      if (emailFilter === 'has_email') {
        if (!c.email) return false;
      }
      return true;
    });
  }, [companies, statusFilter, emailFilter]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-inter">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">My Companies</h1>
          <p className="text-gray-500 text-sm mt-1">Manage and track your generated leads.</p>
        </div>
        <Link
          to="/search"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm"
        >
          + Find New Leads
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
          {error}
        </div>
      )}

      {/* Segmented Filter Control Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Lead Status</span>
            <div className="flex bg-gray-100 p-0.5 rounded-lg border border-gray-200/50">
              {[
                { id: 'Pending', label: 'Pending Outreach 📩' },
                { id: 'Emailed', label: 'Already Emailed ✅' },
                { id: 'all', label: 'All Leads 📁' }
              ].map(opt => {
                const active = statusFilter === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setStatusFilter(opt.id)}
                    className={`px-3 py-1 text-xs rounded-md transition-all font-semibold cursor-pointer ${
                      active
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1">Email Availability</span>
            <div className="flex bg-gray-100 p-0.5 rounded-lg border border-gray-200/50">
              {[
                { id: 'all', label: 'All' },
                { id: 'has_email', label: 'Has Email ✉️' }
              ].map(opt => {
                const active = emailFilter === opt.id;
                return (
                  <button
                    key={opt.id}
                    onClick={() => setEmailFilter(opt.id)}
                    className={`px-3 py-1 text-xs rounded-md transition-all font-semibold cursor-pointer ${
                      active
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-800'
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        
        <div className="text-xs text-gray-400 font-medium">
          Showing <span className="text-gray-800 font-semibold">{filteredCompanies.length}</span> of {companies.length} Leads
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-gray-600">
            <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 text-xs uppercase font-semibold">
              <tr>
                <th className="px-6 py-4">Company Name</th>
                <th className="px-6 py-4">Industry</th>
                <th className="px-6 py-4">Website</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredCompanies.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-gray-500">
                    <div className="text-base font-semibold text-gray-700 mb-1">No Leads Found</div>
                    <div className="text-xs text-gray-400">No leads match the selected status and email filters.</div>
                  </td>
                </tr>
              ) : (
                filteredCompanies.map((company) => (
                  <tr key={company.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-gray-900">{company.name}</td>
                    <td className="px-6 py-4">{company.industry || '-'}</td>
                    <td className="px-6 py-4">
                      {company.website_url ? (
                        <a
                          href={company.website_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
                        >
                          {company.website_url.replace(/^https?:\/\//, '')}
                        </a>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        company.status === 'Emailed'
                          ? 'bg-blue-50 text-blue-700 border-blue-200'
                          : 'bg-yellow-50 text-yellow-700 border-yellow-200'
                      }`}>
                        {company.status || 'Pending'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right flex items-center justify-end gap-4">
                      <Link
                        to={`/lead-details?id=${company.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium transition-colors text-xs"
                      >
                        View Details
                      </Link>
                      {company.email && (
                        <Link
                          to={`/campaign?companyId=${company.id}`}
                          className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-all ${
                            company.status === 'Emailed'
                              ? 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              : 'bg-blue-50 text-blue-600 hover:bg-blue-100 hover:text-blue-700'
                          }`}
                        >
                          {company.status === 'Emailed' ? 'Resend Email' : 'Send Email'}
                        </Link>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Companies;
