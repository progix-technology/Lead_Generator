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
  const [selectedGraphCountry, setSelectedGraphCountry] = useState('All');

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

  // Helper to determine record country
  const getRecordCountry = (record) => {
    if (record.country) return record.country;
    const loc = (record.location || record.metadata?.location || '').toLowerCase();

    if (loc.includes('uae') || loc.includes('dubai') || loc.includes('abu dhabi') || loc.includes('sharjah') || loc.includes('ajman') || loc.includes('al ain') || loc.includes('jebel ali') || loc.includes('bur dubai')) {
      return 'Dubai (UAE)';
    }
    if (loc.includes('england') || loc.includes('uk') || loc.includes('london') || loc.includes('birmingham') || loc.includes('manchester') || loc.includes('leeds') || loc.includes('glasgow') || loc.includes('scotland') || loc.includes('wales') || loc.includes('edinburgh') || loc.includes('bristol') || loc.includes('brighton') || loc.includes('oxford') || loc.includes('cambridge')) {
      return 'United Kingdom';
    }
    return 'United States';
  };

  // 1. Compute Top Level Metrics
  const totalLeads = companies.length;
  const totalSent = records.length;
  const successCount = records.filter(r => r.status === 'Sent').length;
  const failCount = records.filter(r => r.status === 'Failed').length;
  const successRate = totalSent > 0 ? Math.round((successCount / totalSent) * 100) : 0;

  // 2. Compute Unique Categories and Locations from records for filtering
  const categoriesList = Array.from(
    new Set(
      records
        .map(r => r.category || r.metadata?.industry)
        .filter(Boolean)
    )
  );

  const locationsList = Array.from(
    new Set(
      records
        .map(r => r.location || r.metadata?.location)
        .filter(Boolean)
    )
  );

  // 3. Filter records for breakdown charts based on quick dropdown filters
  const filteredRecords = records.filter(r => {
    const rLoc = r.location || r.metadata?.location;
    const rCat = r.category || r.metadata?.industry;
    if (selectedLocation !== 'All' && rLoc !== selectedLocation) return false;
    if (selectedCategory !== 'All' && rCat !== selectedCategory) return false;
    return true;
  });

  // 4. Compute dynamic Category chart statistics
  const categoryCounts = {};
  filteredRecords.forEach(r => {
    const catName = r.category || r.metadata?.industry;
    if (catName) {
      categoryCounts[catName] = (categoryCounts[catName] || 0) + 1;
    }
  });
  const categoryChartData = Object.entries(categoryCounts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // top 5 categories

  // 5. Compute dynamic Location chart statistics
  const locationCounts = {};
  filteredRecords.forEach(r => {
    const locName = r.location || r.metadata?.location;
    if (locName) {
      locationCounts[locName] = (locationCounts[locName] || 0) + 1;
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
      {/* Header bar with dark theme banner & manual refresh */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 rounded-2xl text-white shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-blue-500/20 text-blue-400 rounded-xl text-xl">🏠</span>
            <h1 className="text-2xl font-black tracking-tight">Outreach Performance Dashboard</h1>
          </div>
          <p className="text-sm text-slate-300">
            Real-time conversion metrics, day-wise mountain chart dispatches, and category breakdown analytics.
          </p>
        </div>
        <button
          onClick={fetchDashboardData}
          className="text-xs bg-blue-600 hover:bg-blue-700 text-white border border-blue-500/50 px-4 py-2.5 rounded-xl font-bold transition-all shadow-md cursor-pointer whitespace-nowrap self-start lg:self-auto flex items-center gap-1.5"
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
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
          <span className="text-[10px] text-gray-400 mt-4 block">Total lead companies currently saved in database.</span>
        </Card>

        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Total Processed Attempts</span>
              <span className="text-3xl font-extrabold text-gray-900 mt-2 block">{totalSent}</span>
            </div>
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-xl border border-indigo-100 shadow-sm">
              <FiMail size={20} />
            </div>
          </div>
          <span className="text-[10px] text-gray-400 mt-4 block">Total campaign pipeline runs executed.</span>
        </Card>

        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Total Emails Sent</span>
              <span className="text-3xl font-extrabold text-green-600 mt-2 block">{successCount}</span>
            </div>
            <div className="p-2.5 bg-green-50 text-green-600 rounded-xl border border-green-100 shadow-sm">
              <FiCheckCircle size={20} />
            </div>
          </div>
          <span className="text-[10px] text-gray-400 mt-4 block">Outreach pitches successfully delivered to leads.</span>
        </Card>

        <Card className="bg-gradient-to-br from-white to-gray-50 border border-gray-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block">Failed Emails</span>
              <span className="text-3xl font-extrabold text-red-600 mt-2 block">{failCount}</span>
            </div>
            <div className="p-2.5 bg-red-50 text-red-600 rounded-xl border border-red-100 shadow-sm">
              <FiAlertCircle size={20} />
            </div>
          </div>
          <span className="text-[10px] text-gray-400 mt-4 block">SMTP dispatches that failed to send.</span>
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

      {/* Day-Wise Mountain Chart (Visual Area Chart) */}
      <Card className="space-y-4">
        <div className="border-b border-gray-100 pb-3 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white">
          <div>
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiActivity className="text-indigo-500" /> Day-Wise Outreach Performance (Mountain Chart)
            </h3>
            <p className="text-xs text-gray-400 mt-1">Graphical progression of sent vs failed email counts over the last 15 days.</p>
          </div>

          {/* Country Selector Dropdown Filter for Mountain Chart */}
          <div className="flex items-center gap-2 border border-gray-200 rounded-xl px-3 py-1.5 bg-gray-50 shadow-sm self-start md:self-auto">
            <span className="text-xs font-bold text-gray-500 uppercase flex items-center gap-1">
              <span>🌐</span> Country Filter:
            </span>
            <select
              value={selectedGraphCountry}
              onChange={(e) => setSelectedGraphCountry(e.target.value)}
              className="text-xs font-bold text-indigo-700 bg-transparent border-0 focus:outline-none focus:ring-0 cursor-pointer pr-2"
            >
              <option value="All">All Countries (Global)</option>
              <option value="United States">🇺🇸 United States (USA)</option>
              <option value="United Kingdom">🇬🇧 United Kingdom (UK)</option>
              <option value="Dubai (UAE)">🇦🇪 Dubai (UAE)</option>
            </select>
          </div>
        </div>

        <div className="w-full pt-4 pb-2">
          {(() => {
            // Filter records by selected graph country
            let graphRecords = records;
            if (selectedGraphCountry !== 'All') {
              graphRecords = records.filter(r => getRecordCountry(r) === selectedGraphCountry);
            }

            const dateGroups = {};
            const sortedRecords = [...graphRecords].sort((a, b) => new Date(a.sent_at || a.created_at) - new Date(b.sent_at || b.created_at));
            
            // Collect the last 15 active days
            sortedRecords.forEach(r => {
              const dateObj = new Date(r.sent_at || r.created_at);
              if (isNaN(dateObj.getTime())) return;
              const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              
              if (!dateGroups[dateStr]) {
                dateGroups[dateStr] = { date: dateStr, sent: 0, failed: 0 };
              }
              if (r.status === 'Sent') {
                dateGroups[dateStr].sent += 1;
              } else if (r.status === 'Failed') {
                dateGroups[dateStr].failed += 1;
              }
            });

            const chartData = Object.values(dateGroups).slice(-15);

            if (chartData.length === 0) {
              return (
                <div className="text-xs text-gray-400 italic text-center py-20 bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
                  No outreach history recorded for {selectedGraphCountry === 'All' ? 'any country' : selectedGraphCountry} yet.
                </div>
              );
            }

            const maxVal = Math.max(...chartData.map(d => d.sent + d.failed), 5);
            const width = 800;
            const height = 220;
            const padding = 35;
            
            const pointsSent = chartData.map((d, i) => {
              const x = padding + (i * (width - 2 * padding)) / Math.max(chartData.length - 1, 1);
              const y = height - padding - (d.sent * (height - 2 * padding)) / maxVal;
              return `${x},${y}`;
            });

            const pointsFailed = chartData.map((d, i) => {
              const x = padding + (i * (width - 2 * padding)) / Math.max(chartData.length - 1, 1);
              const y = height - padding - (d.failed * (height - 2 * padding)) / maxVal;
              return `${x},${y}`;
            });

            const areaSent = [
              `${padding},${height - padding}`,
              ...pointsSent,
              `${width - padding},${height - padding}`
            ].join(' ');

            const areaFailed = [
              `${padding},${height - padding}`,
              ...pointsFailed,
              `${width - padding},${height - padding}`
            ].join(' ');

            return (
              <div className="w-full overflow-x-auto">
                <div className="min-w-[600px] relative">
                  <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full font-sans select-none">
                    <defs>
                      <linearGradient id="gradientSent" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.45"/>
                        <stop offset="100%" stopColor="#4f46e5" stopOpacity="0.0"/>
                      </linearGradient>
                      <linearGradient id="gradientFailed" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3"/>
                        <stop offset="100%" stopColor="#ef4444" stopOpacity="0.0"/>
                      </linearGradient>
                    </defs>

                    {/* Horizontal grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
                      const y = padding + ratio * (height - 2 * padding);
                      const val = Math.round(maxVal * (1 - ratio));
                      return (
                        <g key={idx}>
                          <line x1={padding} y1={y} x2={width - padding} y2={y} stroke="#f1f5f9" strokeWidth="1.5" />
                          <text x={padding - 8} y={y + 4} textAnchor="end" className="text-[10px] fill-gray-400 font-semibold">{val}</text>
                        </g>
                      );
                    })}

                    {/* Filled Mountain Areas */}
                    <polygon points={areaSent} fill="url(#gradientSent)" />
                    <polygon points={areaFailed} fill="url(#gradientFailed)" />

                    {/* Stroke lines */}
                    <polyline points={pointsSent.join(' ')} fill="none" stroke="#4f46e5" strokeWidth="3" strokeLinecap="round" />
                    <polyline points={pointsFailed.join(' ')} fill="none" stroke="#ef4444" strokeWidth="2.5" strokeDasharray="4 4" strokeLinecap="round" />

                    {/* Data circle points */}
                    {chartData.map((d, i) => {
                      const x = padding + (i * (width - 2 * padding)) / Math.max(chartData.length - 1, 1);
                      const ySent = height - padding - (d.sent * (height - 2 * padding)) / maxVal;
                      return (
                        <g key={i}>
                          <circle cx={x} cy={ySent} r="4.5" fill="#ffffff" stroke="#4f46e5" strokeWidth="3" />
                          {/* X Axis Labels */}
                          <text x={x} y={height - 12} textAnchor="middle" className="text-[10px] fill-gray-500 font-bold">{d.date}</text>
                        </g>
                      );
                    })}
                  </svg>

                  {/* Custom Legends */}
                  <div className="absolute top-0 right-4 flex items-center gap-4 text-xs font-semibold">
                    <span className="flex items-center gap-1.5">
                      <span className="h-3 w-5 rounded bg-indigo-600 opacity-80 inline-block border border-indigo-700"></span>
                      <span className="text-gray-700">Sent Success</span>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-3 w-5 rounded bg-red-500 opacity-60 inline-block border border-red-600"></span>
                      <span className="text-gray-700">Sent Failed</span>
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      </Card>

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
            records.slice(0, 10).map((record) => {
              const recordEmail = record.recipient_email || record.email || '';
              const recordCategory = record.category || record.metadata?.industry || 'N/A';
              const recordLocation = record.location || record.metadata?.location || 'N/A';
              const rawDate = record.sent_at || record.created_at;
              const dateObj = rawDate ? new Date(rawDate) : null;
              const dateStr = dateObj && !isNaN(dateObj.getTime()) ? dateObj.toLocaleString() : 'N/A';

              return (
                <div key={record.id || record._id} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-gray-50 transition-colors">
                  {/* Left side: Company Details & Subject */}
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900 text-sm truncate">{record.company_name}</span>
                      <span className="text-xs font-mono text-gray-500 truncate bg-gray-100 px-2 py-0.5 rounded border border-gray-150">
                        {recordEmail || 'No email'}
                      </span>
                    </div>
                    <div className="text-xs text-gray-700 font-semibold truncate bg-blue-50/50 border border-blue-100 rounded-lg p-2 max-w-2xl">
                      <span className="text-gray-400 select-none mr-1 font-bold text-[10px] uppercase">Subject:</span>
                      {record.subject || 'Outreach Email'}
                    </div>
                  </div>

                  {/* Right side: Categories, locations, status & Date */}
                  <div className="flex flex-wrap items-center gap-3 shrink-0">
                    <span className="inline-flex items-center text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
                      {recordCategory}
                    </span>
                    <span className="inline-flex items-center text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium">
                      {recordLocation}
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
                      {dateStr}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>
    </div>
  );
}
