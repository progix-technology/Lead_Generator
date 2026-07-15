import React, { useState, useEffect } from 'react';
import Card from '../components/Card';
import Button from '../components/Button';
import automationService from '../services/automationService';
import { 
  FiDownload, 
  FiFileText, 
  FiDatabase, 
  FiCalendar, 
  FiCheckCircle, 
  FiAlertCircle, 
  FiTrendingUp, 
  FiSearch, 
  FiEye,
  FiActivity,
  FiMail,
  FiSend,
  FiLayout
} from 'react-icons/fi';

export default function Reports() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Day-wise filter (format YYYY-MM-DD or empty for "All Time")
  const [selectedDate, setSelectedDate] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [campaignType, setCampaignType] = useState('all'); // 'all', 'standard', 'redesign'
  
  // Modal Preview States
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');
      // Fetch up to 1000 outreach records to compute day-wise metrics in client memory
      const response = await automationService.getRecords(0, 1000);
      setRecords(response.data || []);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch outreach history logs.');
    } finally {
      setLoading(false);
    }
  };

  // 1. Group records by unique date to let user pick from existing days in database
  const uniqueDates = Array.from(
    new Set(
      records
        .map(r => r.sent_at ? r.sent_at.split('T')[0] : '')
        .filter(d => d !== '')
    )
  ).sort((a, b) => b.localeCompare(a)); // Sort descending (latest dates first)

  // 2. Filter records based on selected date & search keyword
  const filteredRecords = records.filter(record => {
    // Date filter
    if (selectedDate) {
      const recordDate = record.sent_at ? record.sent_at.split('T')[0] : '';
      if (recordDate !== selectedDate) return false;
    }
    // Campaign Type filter
    if (campaignType === 'redesign') {
      const isRedesign = (record.subject || '').toLowerCase().includes('website') || 
                         (record.body || '').toLowerCase().includes('score:');
      if (!isRedesign) return false;
    } else if (campaignType === 'standard') {
      const isRedesign = (record.subject || '').toLowerCase().includes('website') || 
                         (record.body || '').toLowerCase().includes('score:');
      if (isRedesign) return false;
    }
    // Search keyword filter
    if (searchTerm.trim()) {
      const query = searchTerm.toLowerCase();
      const name = (record.company_name || '').toLowerCase();
      const email = (record.email || '').toLowerCase();
      const cat = (record.category || '').toLowerCase();
      const loc = (record.location || '').toLowerCase();
      if (!name.includes(query) && !email.includes(query) && !cat.includes(query) && !loc.includes(query)) {
        return false;
      }
    }
    return true;
  });

  // 3. Compute Metrics for Filtered Dataset
  const totalSent = filteredRecords.length;
  const succeededCount = filteredRecords.filter(r => r.status === 'Sent').length;
  const failedCount = filteredRecords.filter(r => r.status === 'Failed').length;
  const successRate = totalSent > 0 ? Math.round((succeededCount / totalSent) * 100) : 0;

  // 4. Compute Category Breakdown (Top Categories)
  const categoryMap = {};
  filteredRecords.forEach(r => {
    if (r.category) {
      categoryMap[r.category] = (categoryMap[r.category] || 0) + 1;
    }
  });
  const categoryStats = Object.entries(categoryMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // top 5

  // 5. Compute Location Breakdown (Top Locations)
  const locationMap = {};
  filteredRecords.forEach(r => {
    if (r.location) {
      locationMap[r.location] = (locationMap[r.location] || 0) + 1;
    }
  });
  const locationStats = Object.entries(locationMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5); // top 5

  // 6. CSV Exporter for local data
  const handleExportCSV = () => {
    if (filteredRecords.length === 0) return;
    
    // Headers
    const headers = ['Company Name', 'Email Address', 'Category', 'Location', 'Subject', 'Status', 'Sent At'];
    
    // Rows
    const rows = filteredRecords.map(r => [
      r.company_name || '',
      r.email || '',
      r.category || '',
      r.location || '',
      r.subject || '',
      r.status || '',
      r.sent_at ? new Date(r.sent_at).toLocaleString() : ''
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8,\uFEFF" 
      + [headers.join(','), ...rows.map(e => e.map(val => `"${String(val).replace(/"/g, '""')}"`).join(','))].join('\n');
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `autopilot_report_${selectedDate || 'all_time'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleOpenPreview = (record) => {
    setSelectedRecord(record);
    setShowPreviewModal(true);
  };

  const handleClearFilters = () => {
    setSelectedDate('');
    setSearchTerm('');
    setCampaignType('all');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-inter">
      {/* Top Filter Bar Header */}
      <Card className="p-4 bg-white shadow-sm border border-gray-200">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Quick Presets */}
            <button
              onClick={() => setSelectedDate('')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                !selectedDate 
                  ? 'bg-blue-50 border-blue-200 text-blue-700' 
                  : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              All Time
            </button>

            {uniqueDates.slice(0, 3).map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDate(d)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                  selectedDate === d
                    ? 'bg-blue-50 border-blue-200 text-blue-700' 
                    : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {new Date(d).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
              </button>
            ))}

            {/* Date Select Dropdown */}
            <div className="flex items-center gap-1.5 ml-2 border-l border-gray-250 pl-4">
              <FiCalendar className="text-gray-400 text-sm" />
              <select
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="text-xs font-semibold text-gray-700 bg-transparent border-0 focus:outline-none focus:ring-0 cursor-pointer pr-4"
              >
                <option value="">Choose Custom Date...</option>
                {uniqueDates.map((d) => (
                  <option key={d} value={d}>
                    {new Date(d).toLocaleDateString(undefined, { dateStyle: 'medium' })}
                  </option>
                ))}
              </select>
            </div>

            {/* Campaign Type Segmented Control */}
            <div className="flex bg-gray-150 p-0.5 rounded-lg border border-gray-200/80 ml-2">
              <button
                type="button"
                onClick={() => setCampaignType('all')}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all flex items-center gap-1 cursor-pointer ${
                  campaignType === 'all'
                    ? 'bg-white text-gray-850 shadow-xs'
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                <FiMail size={11} /> All
              </button>
              <button
                type="button"
                onClick={() => setCampaignType('standard')}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all flex items-center gap-1 cursor-pointer ${
                  campaignType === 'standard'
                    ? 'bg-white text-gray-850 shadow-xs'
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                <FiSend size={11} /> Standard
              </button>
              <button
                type="button"
                onClick={() => setCampaignType('redesign')}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-md transition-all flex items-center gap-1 cursor-pointer ${
                  campaignType === 'redesign'
                    ? 'bg-white text-gray-850 shadow-xs'
                    : 'text-gray-500 hover:text-gray-800'
                }`}
              >
                <FiLayout size={11} /> Redesign
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Keyword search filter */}
            <div className="relative flex-1 lg:w-64">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiSearch className="h-4 w-4 text-gray-400" />
              </span>
              <input
                type="text"
                placeholder="Search report logs..."
                className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-gray-300 text-xs text-gray-800 placeholder-gray-450 focus:border-blue-500 focus:outline-none"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            {(selectedDate || searchTerm || campaignType !== 'all') && (
              <button
                onClick={handleClearFilters}
                className="text-xs text-red-500 hover:text-red-700 font-semibold cursor-pointer whitespace-nowrap"
              >
                Clear Filter
              </button>
            )}

            <Button
              variant="secondary"
              onClick={handleExportCSV}
              disabled={filteredRecords.length === 0}
              className="flex items-center gap-1.5 text-xs px-4 py-1.5 border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 cursor-pointer shadow-sm ml-auto"
            >
              <FiDownload size={14} /> Export CSV
            </Button>
          </div>
        </div>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <FiAlertCircle className="text-base" /> {error}
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Total Scanned Leads</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-gray-900">{totalSent}</span>
            <span className="text-xs text-gray-400">runs executed</span>
          </div>
          <span className="text-[10px] text-gray-400 mt-2 block">Matches scanned for target criteria.</span>
        </Card>

        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Emails Sent (Delivered)</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-green-600">{succeededCount}</span>
            <span className="text-xs text-gray-400">delivered</span>
          </div>
          <span className="text-[10px] text-gray-400 mt-2 block">SMTP verified dispatches.</span>
        </Card>

        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Bounced / Failed Mails</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-red-500">{failedCount}</span>
            <span className="text-xs text-gray-400">errors</span>
          </div>
          <span className="text-[10px] text-gray-400 mt-2 block">Invalid mailboxes or SMTP blocks.</span>
        </Card>

        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Outreach Success Rate</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-blue-600">{successRate}%</span>
            <FiTrendingUp className="text-blue-500 text-lg" />
          </div>
          <div className="w-full bg-gray-100 h-1.5 rounded-full mt-3 overflow-hidden">
            <div className="bg-blue-600 h-full rounded-full transition-all duration-500" style={{ width: `${successRate}%` }}></div>
          </div>
        </Card>
      </div>

      {/* Target Breakdown Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Categories Breakdown */}
        <Card className="space-y-4">
          <div className="border-b border-gray-100 pb-3 flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiActivity className="text-blue-500" /> Target Categories Performance
            </h3>
            <span className="text-[11px] text-gray-400">Lead distribution</span>
          </div>
          
          <div className="space-y-3.5 min-h-[160px] flex flex-col justify-center">
            {categoryStats.length === 0 ? (
              <div className="text-xs text-gray-400 italic text-center">No categories recorded in this filter date.</div>
            ) : (
              categoryStats.map((stat, idx) => {
                const percent = totalSent > 0 ? Math.round((stat.count / totalSent) * 100) : 0;
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-gray-700">
                      <span>{stat.name}</span>
                      <span>{stat.count} ({percent}%)</span>
                    </div>
                    <div className="w-full bg-gray-150 h-2 rounded-full overflow-hidden">
                      <div className="bg-blue-500 h-full rounded-full transition-all" style={{ width: `${percent}%` }}></div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>

        {/* Locations Breakdown */}
        <Card className="space-y-4">
          <div className="border-b border-gray-100 pb-3 flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiActivity className="text-green-500" /> Target Locations Performance
            </h3>
            <span className="text-[11px] text-gray-400">Geographical distribution</span>
          </div>

          <div className="space-y-3.5 min-h-[160px] flex flex-col justify-center">
            {locationStats.length === 0 ? (
              <div className="text-xs text-gray-400 italic text-center">No locations recorded in this filter date.</div>
            ) : (
              locationStats.map((stat, idx) => {
                const percent = totalSent > 0 ? Math.round((stat.count / totalSent) * 100) : 0;
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold text-gray-700">
                      <span>{stat.name}</span>
                      <span>{stat.count} ({percent}%)</span>
                    </div>
                    <div className="w-full bg-gray-150 h-2 rounded-full overflow-hidden">
                      <div className="bg-green-500 h-full rounded-full transition-all" style={{ width: `${percent}%` }}></div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>
      </div>

      {/* Filtered Records Details Table */}
      <Card className="p-0 overflow-hidden shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-white">
          <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider">Outreach Performance Logs</h2>
          <span className="text-xs text-gray-400 font-medium">Filtered Results: {filteredRecords.length} records.</span>
        </div>

        <div className="max-h-[500px] overflow-y-auto overflow-x-hidden">
          <table className="w-full text-left text-sm table-fixed">
            <thead className="bg-gray-50 border-b border-gray-100 text-gray-600 sticky top-0 z-10 shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
              <tr>
                <th className="px-6 py-3 w-[25%] text-[11px] font-bold uppercase tracking-wider">Company</th>
                <th className="px-6 py-3 w-[25%] text-[11px] font-bold uppercase tracking-wider">Target Email</th>
                <th className="px-6 py-3 w-[25%] text-[11px] font-bold uppercase tracking-wider">Target Criteria</th>
                <th className="px-6 py-3 w-[15%] text-[11px] font-bold uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 w-[10%] text-center text-[11px] font-bold uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-gray-700 bg-white">
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-xs text-gray-450 italic">
                    No matching outreach records found for this filter selection.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((record) => (
                  <tr key={record.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 truncate">
                      <div className="font-semibold text-gray-900 truncate">{record.company_name}</div>
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        Sent: {record.sent_at ? new Date(record.sent_at).toLocaleString() : 'N/A'}
                      </div>
                    </td>
                    <td className="px-6 py-4 truncate">
                      <span className="font-mono text-xs block">{record.email}</span>
                      <div className="text-[10px] text-gray-400 font-medium select-none mt-1">
                        source: <span className="font-semibold text-gray-500">{(() => {
                          const src = (record.email_source || "").toLowerCase();
                          const webUrl = record.metadata?.website || "";
                          
                          if (src.includes("facebook")) return "facebook.com";
                          if (src.includes("instagram")) return "instagram.com";
                          if (src.includes("linkedin")) return "linkedin.com";
                          
                          if (webUrl && webUrl !== "your business" && !webUrl.includes("their website")) {
                            return webUrl.replace(/https?:\/\/(www\.)?/, 'www.').split('/')[0];
                          }
                          if (!record.email.includes("gmail.com") && !record.email.includes("yahoo.com") && !record.email.includes("outlook.com")) {
                            return `www.${record.email.split('@')[1]}`;
                          }
                          return "facebook.com";
                        })()}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 truncate">
                      <span className="inline-flex items-center text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded border border-gray-200 mr-1.5 font-medium">
                        {record.category || 'N/A'}
                      </span>
                      <span className="inline-flex items-center text-[10px] bg-gray-100 text-gray-600 px-2 py-0.5 rounded border border-gray-200 font-medium">
                        {record.location || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1 text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${
                        record.status === 'Sent' 
                          ? 'bg-green-50 border-green-200 text-green-700' 
                          : 'bg-red-50 border-red-200 text-red-600'
                      }`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${record.status === 'Sent' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                        {record.status}
                      </span>
                      {record.error_message && (
                        <div className="text-[9px] text-red-500 mt-1 italic truncate max-w-xs">{record.error_message}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <button
                        onClick={() => handleOpenPreview(record)}
                        className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 border border-transparent hover:border-blue-100 rounded-lg transition-all cursor-pointer inline-flex items-center justify-center"
                        title="Preview Sent Pitch"
                      >
                        <FiEye size={14} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Modal Preview Sent Email Pitch */}
      {showPreviewModal && selectedRecord && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-xl flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-gray-800">Preview Sent Pitch</h3>
                <p className="text-[11px] text-gray-400 mt-0.5">Delivered to: {selectedRecord.company_name} ({selectedRecord.email})</p>
              </div>
              <button 
                onClick={() => setShowPreviewModal(false)}
                className="text-gray-400 hover:text-gray-600 font-semibold cursor-pointer text-sm"
              >
                ✕ Close
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              <div>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Subject Line</span>
                <div className="text-xs font-semibold text-gray-800 bg-gray-50 border border-gray-200 rounded-lg p-2.5 mt-1 font-mono">
                  {selectedRecord.subject}
                </div>
              </div>

              <div>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block">Email Message Body</span>
                <div className="text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded-xl p-4 mt-1 font-sans whitespace-pre-wrap leading-relaxed min-h-[220px]">
                  {selectedRecord.body}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-gray-100 flex justify-end">
              <Button 
                variant="secondary" 
                onClick={() => setShowPreviewModal(false)}
                className="text-xs px-4 py-2 cursor-pointer"
              >
                Dismiss
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
