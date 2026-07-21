import React, { useState, useEffect, useRef } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import automationService from '../services/automationService';
import { FiCpu, FiPlay, FiMail, FiCheckCircle, FiAlertCircle, FiSettings } from 'react-icons/fi';

const AUTOPILOT_RUN_LOCK_KEY = 'autopilot_manual_run_locked';

export default function AutomatedCampaigns() {
  const [enabled, setEnabled] = useState(false);
  const [subjectTemplate, setSubjectTemplate] = useState('');
  const [bodyTemplate, setBodyTemplate] = useState('');
  const [redesignSubjectTemplate, setRedesignSubjectTemplate] = useState('');
  const [redesignBodyTemplate, setRedesignBodyTemplate] = useState('');
  const [categories, setCategories] = useState([]);
  const [locations, setLocations] = useState([]);
  const [facebookOnly, setFacebookOnly] = useState(false);
  const [targetNewBusinessesOnly, setTargetNewBusinessesOnly] = useState(false);
  const [enableRedesign, setEnableRedesign] = useState(true);
  const [dailyEmailLimit, setDailyEmailLimit] = useState(20);
  const [batchEmailLimit, setBatchEmailLimit] = useState(5);
  const [newCategory, setNewCategory] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [showCategories, setShowCategories] = useState(false);
  const [showLocations, setShowLocations] = useState(false);

  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [todayCount, setTodayCount] = useState(0);
  const [queueMetrics, setQueueMetrics] = useState({ pending_count: 0, pending_standard_count: 0, pending_redesign_count: 0, sent_today: 0 });

  const [loading, setLoading] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [triggeringCycle, setTriggeringCycle] = useState(false);
  const [manualRunLocked, setManualRunLocked] = useState(false);
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
  const redesignBodyRef = useRef(null);
  const consoleContainerRef = useRef(null);

  // Auto-scroll terminal inner container only (does not bounce the browser window)
  useEffect(() => {
    if (consoleContainerRef.current) {
      consoleContainerRef.current.scrollTop = consoleContainerRef.current.scrollHeight;
    }
  }, [consoleLogs]);

  // Polling loop triggered by triggeringCycle or showConsole to keep UI synced with server background thread
  useEffect(() => {
    let pollingActive = triggeringCycle || showConsole;

    const pollLogs = async () => {
      let isFirstFetch = true;
      let tick = 0;
      while (pollingActive) {
        try {
          const res = await automationService.getProgress();
          if (res && res.progress) {
            setConsoleLogs(res.progress);

            // Periodically refresh records list and stats (every 4.5s / 3 ticks) to update counts and emails live
            if (tick % 3 === 0 || res.is_running === false) {
              const history = await automationService.getRecords(0, 100);
              setRecords(history.data || []);
              setTotalCount(history.total_count || 0);
              setTodayCount(history.today_count || 0);
            }

            // Stop polling if the server says autopilot is not running and we've fetched once
            if (res.is_running === false) {
              setTriggeringCycle(false);
              if (!isFirstFetch) {
                pollingActive = false;
              }
            }
          }
        } catch (err) {
          console.error("Failed to poll progress:", err);
        }
        isFirstFetch = false;
        tick++;
        if (pollingActive) {
          await new Promise(resolve => setTimeout(resolve, 1500));
        }
      }
    };

    if (pollingActive) {
      pollLogs();
    }

    return () => {
      pollingActive = false;
    };
  }, [triggeringCycle, showConsole]);

  useEffect(() => {
    fetchData();
  }, []);

  // Poll queue status, records and stats concurrently for a unified Live Dashboard
  useEffect(() => {
    let interval;
    const fetchQueueStatus = async () => {
      try {
        const stats = await automationService.getQueueStatus();
        if (stats) setQueueMetrics(stats);
        
        // Concurrently fetch the latest records and stats to keep the entire dashboard in sync
        const history = await automationService.getRecords(0, 100);
        setRecords(history.data || []);
        setTotalCount(history.total_count || 0);
        setTodayCount(history.today_count || 0);
      } catch (err) { }
    };
    fetchQueueStatus();
    interval = setInterval(fetchQueueStatus, 30000); // Poll every 30 seconds (reduced from 5s to save server load)
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');

      // Fetch settings
      const settings = await automationService.getSettings();
      setEnabled(settings.enabled);
      const runLockFlag = localStorage.getItem(AUTOPILOT_RUN_LOCK_KEY) === '1';
      setManualRunLocked(settings.enabled ? runLockFlag : false);
      if (!settings.enabled) {
        localStorage.removeItem(AUTOPILOT_RUN_LOCK_KEY);
      }
      setSubjectTemplate(settings.subject_template || '');
      setBodyTemplate(settings.body_template || '');
      setRedesignSubjectTemplate(settings.redesign_subject_template || '');
      setRedesignBodyTemplate(settings.redesign_body_template || '');
      setCategories(settings.categories || []);
      setLocations(settings.locations || []);
      setFacebookOnly(!!settings.facebook_only);
      setTargetNewBusinessesOnly(!!settings.target_new_businesses_only);
      setEnableRedesign(settings.enable_redesign !== false); // Default to true
      setDailyEmailLimit(settings.daily_email_limit || 20);
      setBatchEmailLimit(settings.batch_email_limit || 5);

      // Fetch history records
      const history = await automationService.getRecords(0, 100);
      setRecords(history.data || []);
      setTotalCount(history.total_count || 0);
      setTodayCount(history.today_count || 0);

      // Auto-detect and sync active background campaign runs on mount
      try {
        const prog = await automationService.getProgress();
        if (prog && prog.progress && prog.progress.length > 0) {
          setConsoleLogs(prog.progress);
          const isActive = prog.is_running === true;
          if (isActive) {
            setShowConsole(true);
            setTriggeringCycle(true);
            setManualRunLocked(true);
            localStorage.setItem(AUTOPILOT_RUN_LOCK_KEY, '1');
          }
        }
      } catch (err) {
        console.error("Failed to auto-detect active autopilot state:", err);
      }
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
        redesign_subject_template: redesignSubjectTemplate,
        redesign_body_template: redesignBodyTemplate,
        categories,
        locations,
        facebook_only: facebookOnly,
        target_new_businesses_only: targetNewBusinessesOnly,
        enable_redesign: enableRedesign,
        daily_email_limit: parseInt(dailyEmailLimit) || 20,
        batch_email_limit: parseInt(batchEmailLimit) || 5
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
        redesign_subject_template: redesignSubjectTemplate,
        redesign_body_template: redesignBodyTemplate,
        categories,
        locations,
        facebook_only: facebookOnly,
        target_new_businesses_only: targetNewBusinessesOnly,
        enable_redesign: enableRedesign,
        daily_email_limit: parseInt(dailyEmailLimit) || 20,
        batch_email_limit: parseInt(batchEmailLimit) || 5
      });

      // Any successful toggle re-arms the manual trigger state to prevent stale lock bugs.
      setManualRunLocked(false);
      localStorage.removeItem(AUTOPILOT_RUN_LOCK_KEY);

      setSuccessMsg(checked ? 'Autopilot is now active! 🤖⚡' : 'Autopilot has been disabled.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error(err);
      setEnabled(!checked); // Revert state
      setError('Failed to update toggle state.');
    }
  };

  const handleRunCycleNow = async () => {
    if (!enabled || manualRunLocked) {
      if (!enabled) {
        setError('Please enable Autopilot first, then run a cycle.');
      } else {
        setError('Manual run is locked. Toggle OFF and then ON to run again.');
      }
      return;
    }

    setTriggeringCycle(true);
    setError('');
    setSuccessMsg('');
    setConsoleLogs(['Initializing connection to Autopilot worker daemon...']);
    setShowConsole(true);

    try {
      const res = await automationService.triggerAutopilot();
      if (res.status === 'success') {
        setManualRunLocked(true);
        localStorage.setItem(AUTOPILOT_RUN_LOCK_KEY, '1');
        setSuccessMsg('Autopilot batch running in the background... See live logs below!');
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Manual autopilot execution cycle failed to start.');
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

  const insertRedesignVariable = (variable) => {
    const textarea = redesignBodyRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const before = text.substring(0, start);
    const after = text.substring(end, text.length);

    const replacement = `{{${variable}}}`;
    setRedesignBodyTemplate(before + replacement + after);

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

  const redesignVariables = [
    { code: 'company', label: 'Company Name' },
    { code: 'first_name', label: 'First Name' },
    { code: 'website', label: 'Website URL' },
    { code: 'industry', label: 'Industry Name' },
    { code: 'location', label: 'Location/City' },
    { code: 'performance_score', label: 'Speed Score' },
    { code: 'ui_score', label: 'UI Score' },
    { code: 'seo_score', label: 'SEO Score' },
    { code: 'suggestions', label: 'Audit Suggestions' }
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
            variant="secondary"
            className="flex items-center gap-1.5 shadow-sm text-xs py-2.5 px-4 border border-gray-200 hover:bg-gray-50 text-gray-700 font-semibold cursor-pointer"
            onClick={() => setShowConsole(prev => !prev)}
          >
            <span className="flex items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full ${showConsole ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></span>
              {showConsole ? 'Hide Terminal 📺' : 'Show Terminal 📺'}
            </span>
          </Button>

          <Button
            variant="primary"
            className="flex items-center gap-1.5 shadow-sm text-xs py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 cursor-pointer"
            onClick={handleRunCycleNow}
            disabled={triggeringCycle || !enabled || manualRunLocked}
          >
            <FiPlay /> {
              !enabled
                ? 'Enable Autopilot First'
                : triggeringCycle
                  ? 'Running Cycle...'
                  : manualRunLocked
                    ? 'Toggle OFF-ON to Run Again'
                    : 'Run Autopilot Now ⚡'
            }
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

      {/* Live Queue Counter Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-2">
        <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 flex flex-col justify-center items-center py-6 shadow-sm">
          <div className="text-xs font-bold text-blue-800 uppercase tracking-wider mb-2 text-center">Website Creation Queue (No Website)</div>
          <div className="text-4xl font-black text-blue-600 drop-shadow-sm">{queueMetrics.pending_standard_count || 0}</div>
          <div className="text-[10px] text-blue-500 font-medium mt-2">Pitches ready to send automatically</div>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-fuchsia-50 border border-purple-100 flex flex-col justify-center items-center py-6 shadow-sm">
          <div className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-2 text-center">Redesign Campaign Queue</div>
          <div className="text-4xl font-black text-purple-600 drop-shadow-sm">{queueMetrics.pending_redesign_count || 0}</div>
          <div className="text-[10px] text-purple-500 font-medium mt-2">
            {enableRedesign 
              ? "🟢 Active - sending smoothly" 
              : "⏸️ Paused (Turn ON toggle to send)"}
          </div>
        </Card>
        <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 flex flex-col justify-center items-center py-6 shadow-sm">
          <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider mb-2 text-center">Emails Successfully Sent (Today)</div>
          <div className="text-4xl font-black text-emerald-600 drop-shadow-sm">
            {queueMetrics.sent_today} <span className="text-xl text-emerald-400">/ {dailyEmailLimit}</span>
          </div>
          <div className="text-[10px] text-emerald-500 font-medium mt-2">Outbox count today</div>
        </Card>
      </div>

      {showConsole && (
        <div className="fixed bottom-6 right-6 w-[450px] max-w-[90vw] z-50 transition-all duration-300">
          <div className="bg-slate-950/95 border border-slate-800 text-green-400 p-5 rounded-2xl shadow-2xl font-mono text-xs space-y-3 relative overflow-hidden backdrop-blur-md">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 text-[10px] text-slate-500 uppercase tracking-widest font-bold font-sans">
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full bg-green-500 animate-pulse"></span> Live Autopilot Terminal
              </span>
              <button
                onClick={() => setShowConsole(false)}
                className="text-slate-400 hover:text-slate-200 cursor-pointer font-sans normal-case text-xs"
              >
                ✕ Close
              </button>
            </div>

            <div ref={consoleContainerRef} className="h-[250px] overflow-y-auto space-y-1.5 scroll-smooth pr-1">
              {consoleLogs.length === 0 ? (
                <div className="text-slate-500 italic">Awaiting worker log dispatch...</div>
              ) : (
                consoleLogs.map((log, index) => {
                  const isSleeping = log.toLowerCase().includes("sleeping") || log.toLowerCase().includes("sleep");
                  return (
                    <div
                      key={index}
                      className={`leading-relaxed whitespace-pre-wrap select-text ${isSleeping ? 'text-blue-400 font-semibold' : 'text-green-400'}`}
                    >
                      {log}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
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
            <span className="text-3xl font-extrabold text-gray-900">{todayCount} <span className="text-sm font-normal text-gray-400">/ {dailyEmailLimit} sent today</span></span>
            <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">Limit: {dailyEmailLimit}/day</span>
          </div>
          <div className="w-full bg-gray-100 h-2 rounded-full mt-3 overflow-hidden">
            <div className="bg-blue-600 h-full rounded-full transition-all duration-500" style={{ width: `${Math.min((todayCount / dailyEmailLimit) * 100, 100)}%` }}></div>
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

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="md:col-span-3">
                <Input
                  label="Autopilot Subject Line"
                  placeholder="Helping {{company}} strengthen its online presence"
                  value={subjectTemplate}
                  onChange={(e) => setSubjectTemplate(e.target.value)}
                />
              </div>
              <div>
                <Input
                  label="Daily Limit"
                  type="number"
                  min="1"
                  max="500"
                  placeholder="20"
                  value={dailyEmailLimit}
                  onChange={(e) => setDailyEmailLimit(e.target.value)}
                />
              </div>
              <div>
                <Input
                  label="Batch Target"
                  type="number"
                  min="1"
                  max="50"
                  placeholder="5"
                  value={batchEmailLimit}
                  onChange={(e) => setBatchEmailLimit(e.target.value)}
                />
              </div>
            </div>

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

            <div className="flex items-center justify-between pt-2 border-t border-gray-100">
              {successMsg && (
                <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                  <FiCheckCircle /> {successMsg}
                </span>
              )}
              {error && !successMsg && (
                <span className="text-xs text-red-600 font-medium flex items-center gap-1">
                  <FiAlertCircle /> {error}
                </span>
              )}
              {!successMsg && !error && <span />}
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

          {/* Autopilot Redesign Template (Bad Website Leads) Configurations */}
          <Card className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
                <FiSettings className="text-blue-500" /> Redesign (Bad Website) Template
              </h3>
              <span className="text-xs text-gray-400">Pitches sent exclusively to leads with outdated/slow websites.</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="md:col-span-5">
                <Input
                  label="Redesign Subject Line"
                  placeholder="Quick suggestion for {{company}} about your website"
                  value={redesignSubjectTemplate}
                  onChange={(e) => setRedesignSubjectTemplate(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="md:col-span-3">
                <label className="block text-sm font-semibold text-gray-700 mb-1.5">Email Body Template</label>
                <textarea
                  ref={redesignBodyRef}
                  rows="14"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
                  placeholder="Write your website redesign outreach email here..."
                  value={redesignBodyTemplate}
                  onChange={(e) => setRedesignBodyTemplate(e.target.value)}
                />
              </div>

              {/* Template Variables Helper */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Available Tags:</label>
                <div className="flex flex-col gap-1.5">
                  {redesignVariables.map((variable) => (
                    <button
                      type="button"
                      key={variable.code}
                      onClick={() => insertRedesignVariable(variable.code)}
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

            <div className="flex items-center justify-between pt-2 border-t border-gray-100">
              {successMsg && (
                <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                  <FiCheckCircle /> {successMsg}
                </span>
              )}
              {error && !successMsg && (
                <span className="text-xs text-red-600 font-medium flex items-center gap-1">
                  <FiAlertCircle /> {error}
                </span>
              )}
              {!successMsg && !error && <span />}
              <Button
                variant="primary"
                onClick={handleSaveSettings}
                disabled={savingSettings}
                className="text-xs px-6 py-2"
              >
                {savingSettings ? 'Saving...' : 'Save Redesign Template'}
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
                  <p>Outreach emails are sent automatically. The daily limit is capped at **{dailyEmailLimit} sent emails per day** to preserve domain IP reputation.</p>
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

          {/* Category Input & Chips (Collapsible Dropdown with Scrollbar) */}
          <div className="border-b border-gray-100 pb-2">
            <div 
              className="flex items-center justify-between cursor-pointer py-1.5 select-none hover:bg-gray-50 px-1 rounded transition-colors" 
              onClick={() => setShowCategories(!showCategories)}
            >
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider cursor-pointer">Target Categories ({categories.length})</label>
              <span className="text-xs text-gray-400 font-bold">{showCategories ? '▼' : '▶'}</span>
            </div>
            
            {showCategories && (
              <div className="space-y-3 mt-2">
                <form onSubmit={handleAddCategory} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. Beauty Products, Plumbers, Grocery Stores"
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-850 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                  />
                  <Button type="submit" variant="secondary" className="text-xs px-3 py-1.5 border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 cursor-pointer">Add</Button>
                </form>

                <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 border border-gray-200 rounded-xl max-h-[140px] overflow-y-auto align-content-start">
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
            )}
          </div>

          {/* Location Input & Chips (Collapsible Dropdown with Scrollbar) */}
          <div className="border-b border-gray-100 pb-2">
            <div 
              className="flex items-center justify-between cursor-pointer py-1.5 select-none hover:bg-gray-50 px-1 rounded transition-colors" 
              onClick={() => setShowLocations(!showLocations)}
            >
              <label className="text-xs font-bold text-gray-700 uppercase tracking-wider cursor-pointer">Target Locations ({locations.length})</label>
              <span className="text-xs text-gray-400 font-bold">{showLocations ? '▼' : '▶'}</span>
            </div>
            
            {showLocations && (
              <div className="space-y-3 mt-2">
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

                <div className="flex flex-wrap gap-1.5 p-2 bg-gray-50 border border-gray-200 rounded-xl max-h-[140px] overflow-y-auto align-content-start">
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
            )}
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

          {/* Target New Businesses (Under 5 Reviews) */}
          <div className="flex items-center justify-between p-3 bg-indigo-50/40 border border-indigo-100 rounded-xl">
            <div className="flex flex-col pr-2">
              <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">Target New Businesses Only</span>
              <span className="text-[9px] text-gray-500 mt-0.5 leading-normal">
                {targetNewBusinessesOnly
                  ? "Filters Google Maps results to only target fresh businesses with 0 to 5 reviews."
                  : "Off. Normal targeting without review count restrictions."}
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={targetNewBusinessesOnly}
                onChange={(e) => setTargetNewBusinessesOnly(e.target.checked)}
              />
              <div className="w-8 h-4.5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-indigo-500"></div>
            </label>
          </div>

          {/* Enable Redesign Campaigns Toggle */}
          <div className="flex items-center justify-between p-3 bg-gray-50 border border-gray-200 rounded-xl">
            <div className="flex flex-col pr-2">
              <span className="text-[11px] font-bold text-gray-700 uppercase tracking-wider">Redesign Campaigns</span>
              <span className="text-[9px] text-gray-400 mt-0.5 leading-normal">
                {enableRedesign
                  ? "Pitches website redesigns to companies with existing low-scoring websites."
                  : "Skips redesigns. Targets only businesses with zero digital identity (no website)."}
              </span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={enableRedesign}
                onChange={(e) => setEnableRedesign(e.target.checked)}
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
                      <div className="flex flex-col gap-1">
                        <div className="flex items-center gap-1.5 overflow-hidden">
                          <span className="text-green-600 font-semibold text-xs font-mono truncate block" title={record.email}>
                            {record.email}
                          </span>
                          {record.status === 'Sent' ? (
                            <span className="text-[8px] bg-green-50 text-green-700 px-1 py-0.2 rounded border border-green-200 font-extrabold flex-shrink-0">
                              ✓ Verified
                            </span>
                          ) : record.status === 'Pending_Email' ? (
                            <span className="text-[8px] bg-indigo-50 text-indigo-700 px-1 py-0.2 rounded border border-indigo-200 font-extrabold flex-shrink-0">
                              ⧖ Queued
                            </span>
                          ) : record.status === 'Unverified' ? (
                            <span className="text-[8px] bg-amber-50 text-amber-700 px-1 py-0.2 rounded border border-amber-200 font-extrabold flex-shrink-0">
                              Unverified
                            </span>
                          ) : (
                            <span className="text-[8px] bg-red-50 text-red-700 px-1 py-0.2 rounded border border-red-200 font-extrabold flex-shrink-0">
                              ✕ Failed
                            </span>
                          )}
                        </div>
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
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600 align-middle truncate text-xs" title={`${record.category} in ${record.location}`}>
                      {record.category} / {record.location}
                    </td>
                    <td className="px-6 py-4 text-gray-500 align-middle text-xs">
                      {new Date(record.sent_at).toLocaleDateString()} {new Date(record.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-6 py-4 text-right align-middle">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => {
                            setSelectedRecord(record);
                            setShowPreviewModal(true);
                          }}
                          className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all cursor-pointer ${record.status === 'Sent'
                              ? 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100/50'
                              : record.status === 'Pending_Email'
                                ? 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100/50'
                                : record.status === 'Unverified'
                                  ? 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100/50'
                                  : 'bg-red-50 text-red-700 border-red-200 hover:bg-red-100/50'
                            }`}
                        >
                          {record.status === 'Sent' ? 'View Mail ✓' : record.status === 'Pending_Email' ? 'Queued ⧖' : record.status === 'Unverified' ? 'Unverified ⚠' : 'Failed ⚠'}
                        </button>
                        
                        {record.status === 'Failed' && (
                          <button
                            onClick={async () => {
                              try {
                                await automationService.resendFailedEmail(record.id);
                                // Instantly trigger stats refresh using parent fetches (like fetchRecords)
                                if (typeof fetchHistory === 'function') {
                                  fetchHistory();
                                } else if (typeof fetchStatsConcurrently === 'function') {
                                  fetchStatsConcurrently();
                                } else {
                                  window.location.reload();
                                }
                              } catch (err) {
                                alert("Failed to re-queue email: " + (err.response?.data?.detail || err.message));
                              }
                            }}
                            className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm transition-all cursor-pointer flex items-center gap-1"
                            title="Re-queue and Resend outreach"
                          >
                            Resend ⟳
                          </button>
                        )}
                      </div>
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
                <FiMail className="text-blue-500 text-base" /> {selectedRecord.status === 'Unverified' ? 'Skipped Outreach (Unverified)' : 'Sent Outreach Template'}
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
