import React, { useState, useEffect } from 'react';
import Card from '../components/Card';
import companyService from '../services/companyService';
import automationService from '../services/automationService';
import { 
  FiMail, 
  FiFolder, 
  FiCheckCircle, 
  FiAlertCircle, 
  FiMapPin, 
  FiTag, 
  FiClock, 
  FiActivity, 
  FiSearch 
} from 'react-icons/fi';

export default function Dashboard() {
  const [companies, setCompanies] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Dashboard states
  const [selectedLocation, setSelectedLocation] = useState('All');
  const [selectedCategory, setSelectedCategory] = useState('All');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Fetch saved leads and automation dispatches
      const [leadsRes, recordsRes] = await Promise.all([
        companyService.getCompanies(0, 1000),
        automationService.getRecords(0, 1000)
      ]);
      
      setCompanies(leadsRes.data || []);
      setRecords(recordsRes.data || []);
    } catch (err) {
      console.error(err);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // 1. Compute Top Level Metrics
  const totalLeads = companies.length;
  const totalSent = records.length;
  const successCount = records.filter(r => r.status === 'Sent').length;
  const failCount = records.filter(r => r.status === 'Failed').length;
  const successRate = totalSent > 0 ? Math.round((successCount / totalSent) * 100) : 0;

  // 2. Compute Unique Categories and Locations from records for filtering
  const categoriesList = Array.from(new Set(records.map(r => r.category).filter(Boolean)));
  const locationsList = Array.from(new Set(records.map(r => r.location).filter(Boolean)));

  // 3. Filter records for breakdown charts based on quick dropdown filters
  const filteredRecords = records.filter(r => {
    if (selectedLocation !== 'All' && r.location !== selectedLocation) return false;
    if (selectedCategory !== 'All' && r.category !== selectedCategory) return false;
    return true;
  });

  // 4. Compute dynamic Category chart statistics
  const categoryCounts = {};
  filteredRecords.forEach(r => {
    if (r.category) {
      categoryCounts[r.category] = (categoryCounts[r.category] || 0) + 1;
    }
  });
  const categoryChartData = Object.entries(categoryCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // top 5 categories

  // 5. Compute dynamic Location chart statistics
  const locationCounts = {};
  filteredRecords.forEach(r => {
    if (r.location) {
      locationCounts[r.location] = (locationCounts[r.location] || 0) + 1;
    }
  });
  const locationChartData = Object.entries(locationCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // top 5 locations

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-inter">
      {/* Header bar with welcome message & manual refresh */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-gray-800 tracking-tight">Outreach Performance Dashboard</h2>
          <p className="text-gray-500 text-xs mt-1">Real-time statistics of cold email dispatches, categories, and target locations.</p>
        </div>
        <button 
          onClick={fetchDashboardData}
          className="text-xs bg-blue-50 border border-blue-200 text-blue-700 px-4 py-2 rounded-xl font-semibold hover:bg-blue-100 transition-colors shadow-sm cursor-pointer whitespace-nowrap self-start md:self-auto"
        >
          🔄 Refresh Metrics
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <FiAlertCircle className="text-base animate-bounce" /> {error}
        </div>
      )}

      {/* Primary Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Total Saved Leads</span>
              <span className="text-3xl font-extrabold text-gray-900 mt-2 block">{totalLeads}</span>
            </div>
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100 shadow-sm">
              <FiFolder size={20} />
            </div>
          </div>
          <span className="text-[10px] text-gray-400 mt-4 block">Total list matches currently saved in DB.</span>
        </Card>

        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Total Emails Sent</span>
              <span className="text-3xl font-extrabold text-gray-900 mt-2 block">{totalSent}</span>
            </div>
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl border border-indigo-100 shadow-sm">
              <FiMail size={20} />
            </div>
          </div>
          <span className="text-[10px] text-gray-400 mt-4 block">Outreach pitches sent to website-less leads.</span>
        </Card>

        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Delivery Success</span>
              <span className="text-3xl font-extrabold text-green-600 mt-2 block">{successCount}</span>
            </div>
            <div className="p-2.5 bg-green-50 text-green-600 rounded-xl border border-green-100 shadow-sm">
              <FiCheckCircle size={20} />
            </div>
          </div>
          <span className="text-[10px] text-gray-400 mt-4 block">SMTP verified successful dispatches.</span>
        </Card>

        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Outreach Success Rate</span>
              <span className="text-3xl font-extrabold text-blue-600 mt-2 block">{successRate}%</span>
            </div>
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100 shadow-sm">
              <FiActivity size={20} />
            </div>
          </div>
          <div className="w-full bg-gray-150 h-1.5 rounded-full mt-4 overflow-hidden">
            <div className="bg-blue-600 h-full rounded-full transition-all duration-500" style={{ width: `${successRate}%` }}></div>
          </div>
        </Card>
      </div>

      {/* Visual breakdown graphs (Sundar charts) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Categories Bar Chart Card */}
        <Card className="lg:col-span-2 space-y-4">
          <div className="border-b border-gray-100 pb-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiTag className="text-blue-500" /> Top Targeted Business Fields (Industries)
            </h3>
            
            {/* Filter controls */}
            <div className="flex items-center gap-1.5 border border-gray-200 rounded-lg px-2.5 py-1 bg-gray-50 shadow-sm self-start">
              <span className="text-[10px] font-bold text-gray-400 uppercase">City:</span>
              <select
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
                className="text-[11px] font-semibold text-gray-700 bg-transparent border-0 focus:outline-none focus:ring-0 cursor-pointer pr-3"
              >
                <option value="All">All Cities</option>
                {locationsList.map(loc => (
                  <option key={loc} value={loc}>{loc}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-4 min-h-[220px] flex flex-col justify-center">
            {categoryChartData.length === 0 ? (
              <div className="text-xs text-gray-400 italic text-center py-10">No category statistics recorded for the current filter.</div>
            ) : (
              categoryChartData.map((stat, idx) => {
                const maxCount = Math.max(...categoryChartData.map(d => d.count), 1);
                const percentWidth = Math.round((stat.count / maxCount) * 100);
                const percentOfTotal = totalSent > 0 ? Math.round((stat.count / totalSent) * 100) : 0;
                
                // Colors mapping for premium look
                const barColors = [
                  'bg-gradient-to-r from-blue-500 to-indigo-500',
                  'bg-gradient-to-r from-cyan-500 to-blue-500',
                  'bg-gradient-to-r from-indigo-500 to-purple-500',
                  'bg-gradient-to-r from-purple-500 to-pink-500',
                  'bg-gradient-to-r from-teal-500 to-cyan-500'
                ];
                
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-gray-700">
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-blue-500"></span>
                        {stat.name}
                      </span>
                      <span>{stat.count} sent <span className="text-[10px] text-gray-400 font-normal">({percentOfTotal}%)</span></span>
                    </div>
                    <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden shadow-inner border border-gray-150">
                      <div 
                        className={`${barColors[idx % barColors.length]} h-full rounded-full transition-all duration-700 ease-out shadow-md`} 
                        style={{ width: `${percentWidth}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* Locations Pie Chart Card */}
        <Card className="space-y-4">
          <div className="border-b border-gray-100 pb-3 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiMapPin className="text-green-500" /> Top Targeted Cities (Locations)
            </h3>
            
            {/* Filter controls */}
            <div className="flex items-center gap-1.5 border border-gray-200 rounded-lg px-2.5 py-1 bg-gray-50 shadow-sm self-start">
              <span className="text-[10px] font-bold text-gray-400 uppercase">Field:</span>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="text-[11px] font-semibold text-gray-700 bg-transparent border-0 focus:outline-none focus:ring-0 cursor-pointer pr-3"
              >
                <option value="All">All Fields</option>
                {categoriesList.map(cat => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-4 min-h-[220px] flex flex-col justify-center">
            {locationChartData.length === 0 ? (
              <div className="text-xs text-gray-400 italic text-center py-10">No location statistics recorded for the current filter.</div>
            ) : (
              locationChartData.map((stat, idx) => {
                const maxCount = Math.max(...locationChartData.map(d => d.count), 1);
                const percentWidth = Math.round((stat.count / maxCount) * 100);
                const percentOfTotal = totalSent > 0 ? Math.round((stat.count / totalSent) * 100) : 0;
                
                const barColors = [
                  'bg-gradient-to-r from-green-500 to-teal-500',
                  'bg-gradient-to-r from-teal-500 to-emerald-500',
                  'bg-gradient-to-r from-emerald-500 to-lime-600',
                  'bg-gradient-to-r from-green-400 to-green-600',
                  'bg-gradient-to-r from-teal-400 to-teal-600'
                ];
                
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-gray-700">
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-green-500"></span>
                        {stat.name}
                      </span>
                      <span>{stat.count} sent <span className="text-[10px] text-gray-400 font-normal">({percentOfTotal}%)</span></span>
                    </div>
                    <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden shadow-inner border border-gray-150">
                      <div 
                        className={`${barColors[idx % barColors.length]} h-full rounded-full transition-all duration-700 ease-out shadow-md`} 
                        style={{ width: `${percentWidth}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>
      </div>

      {/* Activity Timeline ("Kya bheji gayi, kisko bheji gyi") */}
      <Card className="p-0 overflow-hidden shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-white">
          <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
            <FiClock className="text-blue-500" /> Recent Outreach Activities (Dispatches)
          </h3>
          <span className="text-xs text-gray-400">Total sent: {totalSent}</span>
        </div>

        <div className="divide-y divide-gray-100 bg-white">
          {records.length === 0 ? (
            <div className="p-12 text-center text-xs text-gray-400 italic">
              No recent email dispatches recorded. Turn Autopilot Status switch ON to start campaigning.
            </div>
          ) : (
            records.slice(0, 7).map((record) => (
              <div key={record.id} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-gray-50 transition-colors">
                {/* Left side: Company Details & Subject */}
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900 text-sm truncate">{record.company_name}</span>
                    <span className="text-xs font-mono text-gray-500 truncate bg-gray-100 px-2 py-0.5 rounded border border-gray-150">{record.email}</span>
                  </div>
                  <div className="text-xs text-gray-700 font-semibold truncate bg-blue-50/50 border border-blue-100 rounded-lg p-2 max-w-2xl">
                    <span className="text-gray-400 select-none mr-1 font-bold text-[10px] uppercase">Subject:</span>
                    {record.subject}
                  </div>
                </div>

                {/* Right side: Categories, locations, status & Date */}
                <div className="flex flex-wrap items-center gap-3 shrink-0">
                  <span className="inline-flex items-center text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
                    {record.category || 'N/A'}
                  </span>
                  <span className="inline-flex items-center text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
                    {record.location || 'N/A'}
                  </span>

                  <span className={`inline-flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${
                    record.status === 'Sent' 
                      ? 'bg-green-50 border-green-200 text-green-700' 
                      : 'bg-red-50 border-red-200 text-red-600'
                  }`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${record.status === 'Sent' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                    {record.status}
                  </span>

                  <div className="text-[10px] text-gray-400 font-medium whitespace-nowrap">
                    {record.sent_at ? new Date(record.sent_at).toLocaleString() : 'N/A'}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
