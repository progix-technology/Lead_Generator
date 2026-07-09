import React, { useState, useEffect, useRef } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import automationService from '../services/automationService';
import { FiCpu, FiPlay, FiMail, FiCheckCircle, FiAlertCircle, FiSettings } from 'react-icons/fi';

export default function AutomatedCampaigns() {
  const [enabled, setEnabled] = useState(false);
  const [subjectTemplate, setSubjectTemplate] = useState('');
  const [bodyTemplate, setBodyTemplate] = useState('');
  const [categories, setCategories] = useState([]);
  const [locations, setLocations] = useState([]);
  const [facebookOnly, setFacebookOnly] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const [newLocation, setNewLocation] = useState('');
  
  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [todayCount, setTodayCount] = useState(0);
  
  const [loading, setLoading] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [triggeringCycle, setTriggeringCycle] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Live Console Log States
  const [consoleLogs, setConsoleLogs] = useState([]);
  const [showConsole, setShowConsole] = useState(false);
  
  // Modal Preview States
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  
  // Ref to body template textarea for injecting tags
  const bodyRef = useRef(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');
      
      // Fetch settings
      const settings = await automationService.getSettings();
      setEnabled(settings.enabled);
      setSubjectTemplate(settings.subject_template || '');
      setBodyTemplate(settings.body_template || '');
      setCategories(settings.categories || []);
      setLocations(settings.locations || []);
      setFacebookOnly(!!settings.facebook_only);
      
      // Fetch history records
      const history = await automationService.getRecords(0, 100);
      setRecords(history.data || []);
      setTotalCount(history.total_count || 0);
      setTodayCount(history.today_count || 0);
    } catch (err) {
      console.error(err);
      setError('Failed to load autopilot configuration.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddCategory = (e) => {
    e.preventDefault();
    if (newCategory.trim() && !categories.includes(newCategory.trim())) {
      setCategories([...categories, newCategory.trim()]);
      setNewCategory('');
    }
  };

  const handleRemoveCategory = (catToRemove) => {
    setCategories(categories.filter(c => c !== catToRemove));
  };

  const handleAddLocation = (e) => {
    e.preventDefault();
    if (newLocation.trim() && !locations.includes(newLocation.trim())) {
      setLocations([...locations, newLocation.trim()]);
      setNewLocation('');
    }
  };

  const handleRemoveLocation = (locToRemove) => {
    setLocations(locations.filter(l => l !== locToRemove));
  };

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    setError('');
    setSuccessMsg('');
    try {
      await automationService.updateSettings({
        enabled,
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        categories,
        locations,
        facebook_only: facebookOnly
      });
      setSuccessMsg('Autopilot configurations saved successfully!');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error(err);
      setError('Failed to save settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  const handleToggleAutopilot = async (checked) => {
    setEnabled(checked);
    setError('');
    setSuccessMsg('');
    try {
      await automationService.updateSettings({
        enabled: checked,
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        categories,
        locations,
        facebook_only: facebookOnly
      });
      setSuccessMsg(checked ? 'Autopilot is now active! 🤖⚡' : 'Autopilot has been disabled.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error(err);
      setEnabled(!checked); // Revert state
      setError('Failed to update toggle state.');
    }
  };

  const handleRunCycleNow = async () => {
    setTriggeringCycle(true);
    setError('');
    setSuccessMsg('');
    setConsoleLogs(['Initializing connection to Autopilot worker daemon...']);
    setShowConsole(true);
    
    // Set up polling interval to fetch progress logs
    let pollingActive = true;
    const pollLogs = async () => {
      while (pollingActive) {
        try {
          const res = await automationService.getProgress();
          if (res && res.progress) {
            setConsoleLogs(res.progress);
          }
        } catch (err) {
          console.error("Failed to poll progress:", err);
        }
        await new Promise(resolve => setTimeout(resolve, 1500));
      }
    };
    
    // Start polling in background
    pollLogs();

    try {
      const res = await automationService.triggerAutopilot();
      if (res.status === 'success') {
        const result = res.result;
        if (result.status === 'skipped') {
          setSuccessMsg(`Autopilot cycle completed: Skipped (${result.reason})`);
        } else {
          setSuccessMsg(`Autopilot cycle completed successfully! Scanned: ${result.scanned_count}, Sent: ${result.sent_count}`);
        }
        // Force get final logs
        const finalLogs = await automationService.getProgress();
        if (finalLogs && finalLogs.progress) {
          setConsoleLogs(finalLogs.progress);
        }
        // Refresh records
        const history = await automationService.getRecords(0, 100);
        setRecords(history.data || []);
        setTotalCount(history.total_count || 0);
        setTodayCount(history.today_count || 0);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Manual autopilot execution cycle failed.');
    } finally {
      pollingActive = false; // Stop polling
      setTriggeringCycle(false);
    }
  };

  const insertVariable = (variable) => {
    const textarea = bodyRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const before = text.substring(0, start);
    const after = text.substring(end, text.length);

    const replacement = `{{${variable}}}`;
    setBodyTemplate(before + replacement + after);

    // Reposition cursor after injection
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + replacement.length, start + replacement.length);
    }, 0);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const variables = [
    { code: 'company', label: 'Company Name' },
    { code: 'first_name', label: 'First Name' },
    { code: 'website', label: 'Website URL' },
    { code: 'industry', label: 'Industry Name' },
    { code: 'location', label: 'Location/City' },
    { code: 'current_platform', label: 'Email Source (Facebook)' },
    { code: 'service_type', label: 'Offer Type' }
  ];

  return (
    <div className="space-y-6 font-inter">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight flex items-center gap-2">
            Autopilot Outreach <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full font-bold select-none">BETA</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">Autonomous Google Maps lead generation & Facebook-scraped outreach.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Autopilot Master Switch */}
          <div className="flex items-center bg-white border border-gray-200 px-4 py-2 rounded-xl shadow-sm">
            <span className="text-sm font-semibold text-gray-700 mr-3 flex items-center gap-1.5">
              <FiCpu className={`${enabled ? 'text-blue-500 animate-spin' : 'text-gray-400'}`} style={{ animationDuration: '3s' }} /> 
              Autopilot Status:
            </span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={enabled} 
                onChange={(e) => handleToggleAutopilot(e.target.checked)}
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <Button 
            variant="primary" 
            className="flex items-center gap-1.5 shadow-sm text-xs py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 cursor-pointer"
            onClick={handleRunCycleNow}
            disabled={triggeringCycle}
          >
            <FiPlay /> {triggeringCycle ? 'Running Cycle...' : 'Run Autopilot Now ⚡'}
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium flex items-center gap-2">
          <FiAlertCircle className="text-base" /> {error}
        </div>
      )}

      {successMsg && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm font-medium flex items-center gap-2">
          <FiCheckCircle className="text-base" /> {successMsg}
        </div>
      )}

      {showConsole && (
        <Card className="bg-slate-950 text-green-400 border border-slate-800 p-5 rounded-2xl shadow-xl font-mono text-xs space-y-3 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 text-[10px] text-slate-500 uppercase tracking-widest font-bold font-sans">
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse"></span> Live Autopilot Progress Terminal
            </span>
            <button 
              onClick={() => setShowConsole(false)}
              className="text-slate-400 hover:text-slate-200 cursor-pointer font-sans normal-case"
            >
              ✕ Close Terminal
            </button>
          </div>
          
          <div className="max-h-[220px] overflow-y-auto space-y-1.5">
            {consoleLogs.length === 0 ? (
              <div className="text-slate-500 italic">Awaiting worker log dispatch...</div>
            ) : (
              consoleLogs.map((log, index) => (
                <div key={index} className="leading-relaxed whitespace-pre-wrap select-text">
                  {log}
                </div>
              ))
            )}
            <div ref={(el) => el?.scrollIntoView({ behavior: 'smooth' })}></div>
          </div>
        </Card>
      )}

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Autopilot Health</span>
          <div className="flex items-center gap-2 mt-2">
            <span className={`h-2.5 w-2.5 rounded-full ${enabled ? 'bg-green-500 animate-ping' : 'bg-gray-400'}`}></span>
            <span className="text-xl font-bold text-gray-900">
              {enabled ? 'Active & Running' : 'Idle / Sleeping'}
            </span>
          </div>
          <span className="text-xs text-gray-400 mt-2">Runs automated cycles daily between 10:00 AM - 12:00 PM.</span>
        </Card>

        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Daily Outreach Progress</span>
          <div className="flex items-end justify-between mt-2">
            <span className="text-3xl font-extrabold text-gray-900">{todayCount} <span className="text-sm font-normal text-gray-400">/ 20 sent today</span></span>
            <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">Limit: 20/day</span>
          </div>
          <div className="w-full bg-gray-100 h-2 rounded-full mt-3 overflow-hidden">
            <div className="bg-blue-600 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((todayCount/20)*100, 100)}%` }}></div>
          </div>
        </Card>

        <Card className="flex flex-col justify-between">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider block">Total Auto-dispatched</span>
          <div className="flex items-center gap-2 mt-2">
            <FiMail className="text-2xl text-blue-500" />
            <span className="text-3xl font-extrabold text-gray-900">{totalCount}</span>
          </div>
          <span className="text-xs text-gray-400 mt-2">Emails successfully delivered via Autopilot.</span>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Autopilot Template Configurations */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
                <FiSettings className="text-blue-500" /> Autopilot Template
              </h3>
              <span className="text-xs text-gray-400">Pitches sent exclusively to Facebook leads.</span>
            </div>

            <Input 
              label="Autopilot Subject Line" 
              placeholder="Helping {{company}} strengthen its online presence" 
              value={subjectTemplate}
              onChange={(e) => setSubjectTemplate(e.target.value)}
            />

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-3">
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Email Body Template</label>
                <textarea 
                  ref={bodyRef}
                  rows="14"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
                  placeholder="Write your Autopilot outreach email here..."
                  value={bodyTemplate}
                  onChange={(e) => setBodyTemplate(e.target.value)}
                />
              </div>
              
              {/* Template Variables Helper */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Available Tags:</label>
                <div className="flex flex-col gap-1.5">
                  {variables.map((variable) => (
                    <button
                      key={variable.code}
                      onClick={() => insertVariable(variable.code)}
                      className="text-left px-2.5 py-1.5 text-[11px] font-semibold text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 hover:border-gray-300 transition-all cursor-pointer flex items-center justify-between"
                    >
                      <span>{variable.label}</span>
                      <span className="text-blue-600 font-mono">+{variable.code}</span>
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-gray-400 leading-normal mt-3 italic">Click any tag button to insert placeholder at cursor.</p>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-gray-100">
              <Button 
                variant="primary" 
                onClick={handleSaveSettings}
                disabled={savingSettings}
                className="text-xs px-6 py-2"
              >
                {savingSettings ? 'Saving...' : 'Save Autopilot Template'}
              </Button>
            </div>
          </Card>

          {/* How Autopilot Works Card (2-column layout inside Column 1) */}
          <div className="space-y-4 bg-slate-900 text-slate-200 rounded-xl p-6 shadow-md border border-slate-800">
            <h3 className="text-sm font-bold uppercase tracking-wider text-blue-400">How Autopilot Works</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs leading-relaxed">
              <div className="space-y-2">
                <div className="flex gap-2">
                  <span className="font-bold text-blue-400">1.</span>
                  <p>The scheduler runs every 30 minutes, automatically triggering email outreach cycles only between **10:00 AM and 12:00 PM** local time.</p>
                </div>
                <div className="flex gap-2">
                  <span className="font-bold text-blue-400">2.</span>
                  <p>It processes Google Places and filters for businesses **without a website**.</p>
                </div>
                <div className="flex gap-2">
                  <span className="font-bold text-blue-400">3.</span>
                  <p>It deep-scrapes their social links and **only emails** leads whose verified emails are found on Facebook, Instagram, or LinkedIn.</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <span className="font-bold text-blue-400">4.</span>
                  <p>It runs **SMTP verification checks** on the email address before triggering the outreach pipeline.</p>
                </div>
                <div className="flex gap-2">
                  <span className="font-bold text-blue-400">5.</span>
                  <p>Outreach emails are sent automatically. The daily limit is capped at **20 sent emails per day** to preserve domain IP reputation.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Outreach Search Criteria Card (Vertical layout stacked on the right column) */}
        <Card className="space-y-5 h-fit">
          <div className="flex items-center justify-between border-b border-gray-100 pb-3">
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiSettings className="text-blue-500" /> Search Criteria
            </h3>
            <span className="text-xs text-gray-400">Target config.</span>
          </div>

          {/* Category Input & Chips */}
          <div className="space-y-3">
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Target Categories ({categories.length})</label>
            <form onSubmit={handleAddCategory} className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. Bakeries, Plumbers"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-850 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
              />
              <Button type="submit" variant="secondary" className="text-xs px-3 py-1.5 border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 cursor-pointer">Add</Button>
            </form>
            
            <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 border border-gray-200 rounded-xl min-h-[90px] align-content-start">
              {categories.length === 0 ? (
                <span className="text-[11px] text-gray-400 italic m-auto text-center">No categories. All categories will rotate.</span>
              ) : (
                categories.map((cat) => (
                  <span 
                    key={cat} 
                    className="inline-flex items-center gap-1 text-[10px] font-semibold bg-blue-50 text-blue-800 border border-blue-200 rounded-full px-2.5 py-0.5"
                  >
                    {cat}
                    <button 
                      type="button" 
                      onClick={() => handleRemoveCategory(cat)}
                      className="hover:text-blue-900 font-bold ml-0.5 text-[9px] text-blue-400 cursor-pointer"
                    >
                      ✕
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Location Input & Chips */}
          <div className="space-y-3">
            <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">Target Locations ({locations.length})</label>
            <form onSubmit={handleAddLocation} className="flex gap-2">
              <input
                type="text"
                placeholder="e.g. Kingsburg CA"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-850 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={newLocation}
                onChange={(e) => setNewLocation(e.target.value)}
              />
              <Button type="submit" variant="secondary" className="text-xs px-3 py-1.5 border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 cursor-pointer">Add</Button>
            </form>

            <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 border border-gray-200 rounded-xl min-h-[90px] align-content-start">
              {locations.length === 0 ? (
                <span className="text-[11px] text-gray-400 italic m-auto text-center">No locations. All locations will rotate.</span>
              ) : (
                locations.map((loc) => (
                  <span 
                    key={loc} 
                    className="inline-flex items-center gap-1 text-[10px] font-semibold bg-green-50 text-green-800 border border-green-200 rounded-full px-2.5 py-0.5"
                  >
                    {loc}
                    <button 
                      type="button" 
                      onClick={() => handleRemoveLocation(loc)}
                      className="hover:text-green-900 font-bold ml-0.5 text-[9px] text-green-400 cursor-pointer"
                    >
                      ✕
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Target Facebook Only Toggle */}
          <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-xl">
            <div className="flex flex-col pr-2">
              <span className="text-[11px] font-bold text-gray-700 uppercase tracking-wider">Facebook Leads Only</span>
              <span className="text-[9px] text-gray-400 mt-0.5 leading-normal">
                {facebookOnly 
                  ? "Strictly sends pitches to emails found on Facebook." 
                  : "Sends pitches to emails from Facebook, Instagram, or LinkedIn (blocks directory spam like Yelp/support emails)."}
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={facebookOnly} 
                onChange={(e) => setFacebookOnly(e.target.checked)}
              />
              <div className="w-8 h-4.5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          <div className="pt-2 border-t border-gray-150">
            <Button 
              variant="primary" 
              onClick={handleSaveSettings}
              disabled={savingSettings}
              className="w-full text-xs py-2.5 font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white cursor-pointer"
            >
              {savingSettings ? 'Saving...' : 'Save Settings & Criteria'}
            </Button>
          </div>
        </Card>
      </div>

      {/* Autopilot Outreach Logs Table */}
      <Card className="p-0 overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-white">
          <h2 className="text-base font-bold text-gray-800 uppercase tracking-wider">Automated Send Email Records</h2>
          <span className="text-xs text-gray-400 font-medium">Outreach history logs.</span>
        </div>

        <div className="max-h-[500px] overflow-y-auto overflow-x-hidden">
          <table className="w-full text-left text-sm table-fixed">
            <thead className="bg-gray-50 border-b border-gray-100 text-gray-600 sticky top-0 z-10 shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
              <tr>
                <th className="px-6 py-3 w-[25%] text-xs font-bold uppercase tracking-wider">Company</th>
                <th className="px-6 py-3 w-[25%] text-xs font-bold uppercase tracking-wider">Email Address</th>
                <th className="px-6 py-3 w-[20%] text-xs font-bold uppercase tracking-wider">Target Query</th>
                <th className="px-6 py-3 w-[15%] text-xs font-bold uppercase tracking-wider">Sent Date</th>
                <th className="px-6 py-3 w-[15%] text-xs font-bold uppercase tracking-wider text-right">Outreach</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {records.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-12 text-center text-gray-400 italic">
                    No automated campaigns sent yet. Toggle Autopilot to begin!
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr key={record.id} className="hover:bg-gray-50/50 transition-colors">
                    <td className="px-6 py-4 font-semibold text-gray-900 align-middle truncate" title={record.company_name}>
                      {record.company_name}
                    </td>
                    <td className="px-6 py-4 align-middle">
                      <div className="flex items-center gap-1.5 overflow-hidden">
                        <span className="text-green-600 font-semibold text-xs font-mono truncate block" title={record.email}>
                          {record.email}
                        </span>
                        <span className="text-[8px] bg-green-50 text-green-700 px-1 py-0.2 rounded border border-green-200 font-extrabold flex-shrink-0">
                          ✓ Verified
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600 align-middle truncate text-xs" title={`${record.category} in ${record.location}`}>
                      {record.category} / {record.location}
                    </td>
                    <td className="px-6 py-4 text-gray-500 align-middle text-xs">
                      {new Date(record.sent_at).toLocaleDateString()} {new Date(record.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-6 py-4 text-right align-middle">
                      <button
                        onClick={() => {
                          setSelectedRecord(record);
                          setShowPreviewModal(true);
                        }}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all cursor-pointer ${
                          record.status === 'Sent'
                            ? 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100/50'
                            : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100/50'
                        }`}
                      >
                        {record.status === 'Sent' ? 'View Mail ✓' : 'Failed ⚠'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Modal Preview Email Component */}
      {showPreviewModal && selectedRecord && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full border border-gray-100 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-gray-150 flex justify-between items-center bg-gray-50/50">
              <h3 className="font-bold text-gray-800 text-sm flex items-center gap-1.5">
                <FiMail className="text-blue-500 text-base" /> Sent Outreach Template
              </h3>
              <button 
                onClick={() => setShowPreviewModal(false)}
                className="text-gray-400 hover:text-gray-600 text-lg cursor-pointer"
              >
                ✕
              </button>
            </div>
            
            <div className="p-6 space-y-4 text-sm text-gray-800">
              <div>
                <span className="font-semibold text-gray-400 text-xs block mb-0.5">Recipients:</span>
                <span className="font-mono text-gray-700">{selectedRecord.company_name} ({selectedRecord.email})</span>
              </div>
              
              <div>
                <span className="font-semibold text-gray-400 text-xs block mb-0.5">Subject Line:</span>
                <span className="font-bold text-gray-900 text-base">{selectedRecord.subject}</span>
              </div>

              <div>
                <span className="font-semibold text-gray-400 text-xs block mb-1">Email Body Content:</span>
                <div className="border border-gray-200 rounded-xl p-4 bg-gray-50/50 whitespace-pre-line text-xs leading-relaxed max-h-[300px] overflow-y-auto font-sans text-gray-700">
                  {selectedRecord.body}
                </div>
              </div>

              {selectedRecord.error_message && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-xs flex items-center gap-1.5">
                  <FiAlertCircle /> <strong>Error:</strong> {selectedRecord.error_message}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-gray-150 flex justify-end bg-gray-50/50">
              <Button 
                variant="secondary" 
                onClick={() => setShowPreviewModal(false)}
                className="text-xs px-5 py-2 font-semibold"
              >
                Close Preview
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
