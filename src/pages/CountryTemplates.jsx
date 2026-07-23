import React, { useState, useEffect, useRef } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import automationService from '../services/automationService';
import { FiGlobe, FiSettings, FiCheckCircle, FiAlertCircle, FiTag, FiClock, FiPlus, FiTrash2, FiMapPin, FiX } from 'react-icons/fi';

const DEFAULT_SCHEDULES = {
  USA: {
    country_name: "United States",
    flag: "🇺🇸",
    start_time_ist: "01:00 AM",
    end_time_ist: "04:00 AM",
    locations: [
      "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
      "Dallas, TX", "Miami, FL", "Atlanta, GA", "San Diego, CA", "Austin, TX",
      "Seattle, WA", "Denver, CO", "San Jose, CA", "Orlando, FL", "Tampa, FL",
      "Las Vegas, NV", "Charlotte, NC", "Nashville, TN", "Boston, MA", "Philadelphia, PA",
      "Fort Worth, TX", "Jacksonville, FL", "Columbus, OH", "Indianapolis, IN", "San Antonio, TX",
      "Portland, OR", "Sacramento, CA", "Raleigh, NC", "Kansas City, MO", "Cincinnati, OH",
      "Cleveland, OH", "Pittsburgh, PA", "Milwaukee, WI", "Minneapolis, MN", "Salt Lake City, UT",
      "Virginia Beach, VA", "Richmond, VA", "Oklahoma City, OK", "Louisville, KY", "Memphis, TN",
      "Birmingham, AL", "New Orleans, LA", "Buffalo, NY", "Hartford, CT", "Providence, RI",
      "Boise, ID", "Tulsa, OK", "Reno, NV", "Des Moines, IA", "Spokane, WA"
    ]
  },
  UK: {
    country_name: "United Kingdom",
    flag: "🇬🇧",
    start_time_ist: "03:00 PM",
    end_time_ist: "09:00 PM",
    locations: ["London, UK", "Manchester, UK", "Birmingham, UK", "Leeds, UK", "Glasgow, UK", "Liverpool, UK", "Edinburgh, UK", "Bristol, UK"]
  },
  UAE: {
    country_name: "Dubai (UAE)",
    flag: "🇦🇪",
    start_time_ist: "10:00 AM",
    end_time_ist: "02:00 PM",
    locations: ["Dubai, UAE", "Abu Dhabi, UAE", "Sharjah, UAE", "Ajman, UAE", "Ras Al Khaimah, UAE"]
  }
};

export default function CountryTemplates() {
  const [selectedCountryTab, setSelectedCountryTab] = useState('USA');
  const [countryTemplates, setCountryTemplates] = useState({});
  const [countrySchedules, setCountrySchedules] = useState(DEFAULT_SCHEDULES);
  
  const [subjectTemplate, setSubjectTemplate] = useState('');
  const [bodyTemplate, setBodyTemplate] = useState('');
  const [redesignSubjectTemplate, setRedesignSubjectTemplate] = useState('');
  const [redesignBodyTemplate, setRedesignBodyTemplate] = useState('');

  // Add Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newCountryName, setNewCountryName] = useState('');
  const [newCountryCode, setNewCountryCode] = useState('');
  const [newCountryFlag, setNewCountryFlag] = useState('🌐');
  const [newStartTime, setNewStartTime] = useState('10:00 AM');
  const [newEndTime, setNewEndTime] = useState('06:00 PM');
  const [newCityInput, setNewCityInput] = useState('');
  const [newCitiesList, setNewCitiesList] = useState([]);

  // Active City Tag Input State
  const [activeCityInput, setActiveCityInput] = useState('');

  const [loading, setLoading] = useState(true);
  const [savingSettings, setSavingSettings] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const bodyRef = useRef(null);
  const redesignBodyRef = useRef(null);

  const variables = [
    { label: 'Company Name', code: '{{company}}' },
    { label: 'First Name', code: '{{first_name}}' },
    { label: 'Website URL', code: '{{website}}' },
    { label: 'Industry/Category', code: '{{industry}}' },
    { label: 'Location', code: '{{location}}' },
    { label: 'Current Platform', code: '{{current_platform}}' },
    { label: 'Service Type', code: '{{service_type}}' },
  ];

  const redesignVariables = [
    { label: 'Company Name', code: '{{company}}' },
    { label: 'First Name', code: '{{first_name}}' },
    { label: 'Website URL', code: '{{website}}' },
    { label: 'Industry/Category', code: '{{industry}}' },
    { label: 'Location', code: '{{location}}' },
    { label: 'Performance Score', code: '{{performance_score}}' },
    { label: 'UI/Mobile Score', code: '{{ui_score}}' },
    { label: 'SEO Score', code: '{{seo_score}}' },
    { label: 'Audit Suggestions', code: '{{suggestions}}' },
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError('');
      const settings = await automationService.getSettings();
      
      const cTmpls = settings.country_templates || {};
      const cScheds = settings.country_schedules || DEFAULT_SCHEDULES;
      
      setCountryTemplates(cTmpls);
      setCountrySchedules(cScheds);

      const tabKeys = Object.keys(cScheds);
      const activeKey = tabKeys.includes(selectedCountryTab) ? selectedCountryTab : (tabKeys[0] || 'USA');
      setSelectedCountryTab(activeKey);

      const activeTmpl = cTmpls[activeKey] || cTmpls['USA'] || {};
      setSubjectTemplate(activeTmpl.subject_template || settings.subject_template || '');
      setBodyTemplate(activeTmpl.body_template || settings.body_template || '');
      setRedesignSubjectTemplate(activeTmpl.redesign_subject_template || settings.redesign_subject_template || '');
      setRedesignBodyTemplate(activeTmpl.redesign_body_template || settings.redesign_body_template || '');
    } catch (err) {
      console.error(err);
      setError('Failed to load country email templates & schedules.');
    } finally {
      setLoading(false);
    }
  };

  const handleCountryTabChange = (newTab) => {
    const updatedTemplates = {
      ...countryTemplates,
      [selectedCountryTab]: {
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        redesign_subject_template: redesignSubjectTemplate,
        redesign_body_template: redesignBodyTemplate
      }
    };
    setCountryTemplates(updatedTemplates);
    setSelectedCountryTab(newTab);

    const nextTmpl = updatedTemplates[newTab] || {};
    setSubjectTemplate(nextTmpl.subject_template || '');
    setBodyTemplate(nextTmpl.body_template || '');
    setRedesignSubjectTemplate(nextTmpl.redesign_subject_template || '');
    setRedesignBodyTemplate(nextTmpl.redesign_body_template || '');
  };

  const insertVariable = (varCode) => {
    if (!bodyRef.current) return;
    const textarea = bodyRef.current;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const currentVal = bodyTemplate;
    const newVal = currentVal.substring(0, start) + varCode + currentVal.substring(end);
    setBodyTemplate(newVal);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + varCode.length, start + varCode.length);
    }, 0);
  };

  const insertRedesignVariable = (varCode) => {
    if (!redesignBodyRef.current) return;
    const textarea = redesignBodyRef.current;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const currentVal = redesignBodyTemplate;
    const newVal = currentVal.substring(0, start) + varCode + currentVal.substring(end);
    setRedesignBodyTemplate(newVal);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + varCode.length, start + varCode.length);
    }, 0);
  };

  const handleAddCityToActiveCountry = (e) => {
    e.preventDefault();
    if (!activeCityInput.trim()) return;
    const cityStr = activeCityInput.trim();
    
    setCountrySchedules(prev => {
      const activeSched = prev[selectedCountryTab] || {};
      const currentLocs = activeSched.locations || [];
      if (currentLocs.includes(cityStr)) return prev;
      return {
        ...prev,
        [selectedCountryTab]: {
          ...activeSched,
          locations: [...currentLocs, cityStr]
        }
      };
    });
    setActiveCityInput('');
  };

  const handleRemoveCityFromActiveCountry = (cityToRemove) => {
    setCountrySchedules(prev => {
      const activeSched = prev[selectedCountryTab] || {};
      const currentLocs = activeSched.locations || [];
      return {
        ...prev,
        [selectedCountryTab]: {
          ...activeSched,
          locations: currentLocs.filter(c => c !== cityToRemove)
        }
      };
    });
  };

  const handleScheduleTimeChange = (field, val) => {
    setCountrySchedules(prev => ({
      ...prev,
      [selectedCountryTab]: {
        ...prev[selectedCountryTab],
        [field]: val
      }
    }));
  };

  const handleAddNewCityToModalList = (e) => {
    e.preventDefault();
    if (!newCityInput.trim()) return;
    const cityStr = newCityInput.trim();
    if (!newCitiesList.includes(cityStr)) {
      setNewCitiesList([...newCitiesList, cityStr]);
    }
    setNewCityInput('');
  };

  const handleRemoveCityFromModalList = (cityToRemove) => {
    setNewCitiesList(newCitiesList.filter(c => c !== cityToRemove));
  };

  const handleCreateNewCountryProfile = (e) => {
    e.preventDefault();
    if (!newCountryName.trim()) {
      alert("Please enter a Country Name.");
      return;
    }
    const codeKey = (newCountryCode.trim() || newCountryName.trim().substring(0, 3)).toUpperCase();

    const newSched = {
      country_name: newCountryName.trim(),
      flag: newCountryFlag.trim() || '🌐',
      start_time_ist: newStartTime,
      end_time_ist: newEndTime,
      locations: newCitiesList.length > 0 ? newCitiesList : [`${newCountryName.trim()}, Main City`]
    };

    const newTmpl = {
      subject_template: `Helping {{company}} strengthen its online presence in ${newCountryName.trim()}`,
      body_template: `Hello {{first_name}},\n\nI hope you're doing well.\n\nWhile researching businesses in the {{industry}} sector across {{location}}, I came across {{company}}...\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP`,
      redesign_subject_template: `Website performance report & suggestions for {{company}} (${newCountryName.trim()})`,
      redesign_body_template: `Hello {{first_name}},\n\nI hope you are having a pleasant week.\n\nWhile conducting digital audits for {{industry}} firms in {{location}}, I analyzed your website ({{website}})...\n\nBest Regards,\n\nAbhinandan Dubey\nProgix Technologies LLP`
    };

    const updatedSchedules = { ...countrySchedules, [codeKey]: newSched };
    const updatedTemplates = { ...countryTemplates, [codeKey]: newTmpl };

    setCountrySchedules(updatedSchedules);
    setCountryTemplates(updatedTemplates);

    setSelectedCountryTab(codeKey);
    setSubjectTemplate(newTmpl.subject_template);
    setBodyTemplate(newTmpl.body_template);
    setRedesignSubjectTemplate(newTmpl.redesign_subject_template);
    setRedesignBodyTemplate(newTmpl.redesign_body_template);

    // Reset Modal
    setShowAddModal(false);
    setNewCountryName('');
    setNewCountryCode('');
    setNewCountryFlag('🌐');
    setNewCitiesList([]);
    setNewCityInput('');
  };

  const handleDeleteCountryProfile = (codeToDelete) => {
    if (Object.keys(countrySchedules).length <= 1) {
      alert("You must keep at least one country profile in the system.");
      return;
    }
    if (!window.confirm(`Are you sure you want to delete the country profile '${codeToDelete}'?`)) {
      return;
    }

    const updatedSchedules = { ...countrySchedules };
    delete updatedSchedules[codeToDelete];

    const updatedTemplates = { ...countryTemplates };
    delete updatedTemplates[codeToDelete];

    setCountrySchedules(updatedSchedules);
    setCountryTemplates(updatedTemplates);

    const remainingKeys = Object.keys(updatedSchedules);
    const nextActive = remainingKeys[0] || 'USA';
    setSelectedCountryTab(nextActive);

    const nextTmpl = updatedTemplates[nextActive] || {};
    setSubjectTemplate(nextTmpl.subject_template || '');
    setBodyTemplate(nextTmpl.body_template || '');
    setRedesignSubjectTemplate(nextTmpl.redesign_subject_template || '');
    setRedesignBodyTemplate(nextTmpl.redesign_body_template || '');
  };

  const handleSaveAllSettings = async () => {
    setSavingSettings(true);
    setError('');
    setSuccessMsg('');

    const finalCountryTemplates = {
      ...countryTemplates,
      [selectedCountryTab]: {
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        redesign_subject_template: redesignSubjectTemplate,
        redesign_body_template: redesignBodyTemplate
      }
    };

    try {
      await automationService.updateSettings({
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        redesign_subject_template: redesignSubjectTemplate,
        redesign_body_template: redesignBodyTemplate,
        country_templates: finalCountryTemplates,
        country_schedules: countrySchedules
      });
      setCountryTemplates(finalCountryTemplates);
      setSuccessMsg('All Country Email Templates & Time Schedules saved successfully!');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error(err);
      setError('Failed to save country profiles & settings.');
    } finally {
      setSavingSettings(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500 font-medium">Loading country email templates & schedules...</div>;
  }

  const activeSchedule = countrySchedules[selectedCountryTab] || {
    country_name: selectedCountryTab,
    flag: '🌐',
    start_time_ist: '10:00 AM',
    end_time_ist: '06:00 PM',
    locations: []
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 p-6 rounded-2xl text-white shadow-xl border border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-2 bg-blue-500/20 text-blue-400 rounded-xl text-xl">🌐</span>
            <h1 className="text-2xl font-black tracking-tight">Multi-Country Email Templates & Scheduler</h1>
          </div>
          <p className="text-sm text-slate-300">
            Configure target country operating schedules (AM/PM), target city pools, and custom email pitches.
          </p>
        </div>

        {/* Dynamic Country Tabs Bar + Add Country Button */}
        <div className="flex flex-wrap items-center gap-2 bg-slate-800/80 p-1.5 rounded-2xl border border-slate-700">
          {Object.keys(countrySchedules).map((code) => {
            const sched = countrySchedules[code] || {};
            const isSelected = selectedCountryTab === code;
            return (
              <button
                key={code}
                type="button"
                onClick={() => handleCountryTabChange(code)}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                  isSelected
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                    : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
                }`}
              >
                <span className="text-base">{sched.flag || '🌐'}</span>
                <span>{sched.country_name || code}</span>
              </button>
            );
          })}

          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="px-3.5 py-2 rounded-xl text-xs font-bold bg-green-600 hover:bg-green-500 text-white transition-all flex items-center gap-1.5 cursor-pointer shadow-md shadow-green-600/20"
          >
            <FiPlus className="text-sm" /> Add Country
          </button>
        </div>
      </div>

      {/* Target Operating Schedule & Cities Card for Active Country */}
      <Card className="space-y-4 border-2 border-blue-100 bg-blue-50/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-blue-100 pb-3 gap-2">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{activeSchedule.flag || '🌐'}</span>
            <div>
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                {activeSchedule.country_name || selectedCountryTab} Operating Profile
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-blue-100 text-blue-800 rounded-full">
                  {selectedCountryTab}
                </span>
              </h2>
              <span className="text-xs text-gray-500 block">
                Define the specific IST time slot (AM/PM) and cities to target for this country.
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => handleDeleteCountryProfile(selectedCountryTab)}
              className="text-xs font-semibold text-red-600 hover:text-red-800 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-red-200 transition-all flex items-center gap-1 cursor-pointer"
            >
              <FiTrash2 /> Delete Country Profile
            </button>
          </div>
        </div>

        {/* Schedule Time Slot Inputs with AM/PM support */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-white p-4 rounded-xl border border-blue-100">
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1"><FiClock className="text-blue-500" /> Start Time (IST)</span>
              <span className="text-[10px] font-normal text-gray-400">Specify AM/PM e.g. 10:00 AM</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-800 focus:border-blue-500 focus:outline-none"
                placeholder="e.g. 10:00 AM"
                value={activeSchedule.start_time_ist || ''}
                onChange={(e) => handleScheduleTimeChange('start_time_ist', e.target.value)}
              />
            </div>
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              <span className="text-[10px] text-gray-400 font-medium">Quick Presets:</span>
              {['10:00 AM', '03:00 PM', '06:00 PM', '01:00 AM'].map(preset => (
                <button
                  type="button"
                  key={preset}
                  onClick={() => handleScheduleTimeChange('start_time_ist', preset)}
                  className="px-2 py-0.5 text-[10px] font-semibold bg-gray-100 hover:bg-blue-50 text-gray-600 hover:text-blue-600 rounded border border-gray-200 cursor-pointer transition-colors"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1"><FiClock className="text-blue-500" /> End Time (IST)</span>
              <span className="text-[10px] font-normal text-gray-400">Specify AM/PM e.g. 02:00 PM</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-800 focus:border-blue-500 focus:outline-none"
                placeholder="e.g. 02:00 PM"
                value={activeSchedule.end_time_ist || ''}
                onChange={(e) => handleScheduleTimeChange('end_time_ist', e.target.value)}
              />
            </div>
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              <span className="text-[10px] text-gray-400 font-medium">Quick Presets:</span>
              {['02:00 PM', '09:00 PM', '11:00 PM', '04:00 AM'].map(preset => (
                <button
                  type="button"
                  key={preset}
                  onClick={() => handleScheduleTimeChange('end_time_ist', preset)}
                  className="px-2 py-0.5 text-[10px] font-semibold bg-gray-100 hover:bg-blue-50 text-gray-600 hover:text-blue-600 rounded border border-gray-200 cursor-pointer transition-colors"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Active Country Target Cities Management */}
        <div className="bg-white p-4 rounded-xl border border-blue-100 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-gray-700 uppercase tracking-wider flex items-center gap-1">
              <FiMapPin className="text-blue-500" /> Target Cities in {activeSchedule.country_name || selectedCountryTab} ({activeSchedule.locations?.length || 0})
            </label>
            <span className="text-[11px] text-gray-400">Autopilot rotates through these cities during operating hours</span>
          </div>

          {/* Add City Input Form */}
          <form onSubmit={handleAddCityToActiveCountry} className="flex gap-2">
            <input
              type="text"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none"
              placeholder={`Add city in ${activeSchedule.country_name} (e.g., Toronto, ${selectedCountryTab})...`}
              value={activeCityInput}
              onChange={(e) => setActiveCityInput(e.target.value)}
            />
            <button
              type="submit"
              className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg transition-all cursor-pointer flex items-center gap-1"
            >
              <FiPlus /> Add City
            </button>
          </form>

          {/* Cities Tags */}
          <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto p-1">
            {(activeSchedule.locations || []).map((city) => (
              <span
                key={city}
                className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-50 border border-blue-200 text-blue-800 rounded-lg text-xs font-medium"
              >
                <span>{city}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveCityFromActiveCountry(city)}
                  className="text-blue-400 hover:text-red-600 transition-colors cursor-pointer"
                >
                  <FiX />
                </button>
              </span>
            ))}

            {(activeSchedule.locations || []).length === 0 && (
              <span className="text-xs text-gray-400 italic">No cities added yet for this country. Type above to add.</span>
            )}
          </div>
        </div>
      </Card>

      {/* Standard Pitch Template Card */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiSettings className="text-blue-500" /> Standard Cold Email Pitch ({activeSchedule.country_name || selectedCountryTab})
            </h3>
            <span className="text-xs text-gray-400">Pitches sent to businesses without a custom website.</span>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-gray-100 text-gray-600 rounded-lg">
            {selectedCountryTab} Standard Pitch
          </span>
        </div>

        <div className="space-y-4">
          <Input
            label="Subject Line"
            placeholder="Helping {{company}} strengthen its online presence"
            value={subjectTemplate}
            onChange={(e) => setSubjectTemplate(e.target.value)}
          />

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-3">
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">Email Body Template</label>
              <textarea
                ref={bodyRef}
                rows="13"
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none font-sans"
                placeholder="Write standard cold outreach email here..."
                value={bodyTemplate}
                onChange={(e) => setBodyTemplate(e.target.value)}
              />
            </div>

            {/* Template Variables Helper */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <FiTag className="text-blue-500" /> Available Tags:
              </label>
              <div className="flex flex-col gap-1.5">
                {variables.map((variable) => (
                  <button
                    key={variable.code}
                    type="button"
                    onClick={() => insertVariable(variable.code)}
                    className="text-left px-2.5 py-1.5 text-[11px] font-semibold text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-all cursor-pointer flex items-center justify-between"
                  >
                    <span>{variable.label}</span>
                    <span className="text-blue-600 font-mono">+{variable.code}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Redesign Pitch Template Card */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiSettings className="text-blue-500" /> Redesign (Bad Website) Pitch ({activeSchedule.country_name || selectedCountryTab})
            </h3>
            <span className="text-xs text-gray-400">Pitches sent exclusively to leads with outdated/slow/broken websites.</span>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg">
            {selectedCountryTab} Redesign Pitch
          </span>
        </div>

        <div className="space-y-4">
          <Input
            label="Redesign Subject Line"
            placeholder="Quick suggestion for {{company}} about your website"
            value={redesignSubjectTemplate}
            onChange={(e) => setRedesignSubjectTemplate(e.target.value)}
          />

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-3">
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">Redesign Email Body Template</label>
              <textarea
                ref={redesignBodyRef}
                rows="13"
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none font-sans"
                placeholder="Write website redesign outreach email here..."
                value={redesignBodyTemplate}
                onChange={(e) => setRedesignBodyTemplate(e.target.value)}
              />
            </div>

            {/* Redesign Template Variables Helper */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <FiTag className="text-amber-500" /> Audit Tags:
              </label>
              <div className="flex flex-col gap-1.5">
                {redesignVariables.map((variable) => (
                  <button
                    key={variable.code}
                    type="button"
                    onClick={() => insertRedesignVariable(variable.code)}
                    className="text-left px-2.5 py-1.5 text-[11px] font-semibold text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-all cursor-pointer flex items-center justify-between"
                  >
                    <span>{variable.label}</span>
                    <span className="text-blue-600 font-mono">+{variable.code}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Global Save Actions Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          {successMsg && (
            <span className="text-sm text-green-600 font-medium flex items-center gap-1.5">
              <FiCheckCircle className="text-lg" /> {successMsg}
            </span>
          )}
          {error && !successMsg && (
            <span className="text-sm text-red-600 font-medium flex items-center gap-1.5">
              <FiAlertCircle className="text-lg" /> {error}
            </span>
          )}
          {!successMsg && !error && <span />}
          <Button
            variant="primary"
            onClick={handleSaveAllSettings}
            disabled={savingSettings}
            className="text-sm px-8 py-2.5 font-bold shadow-lg shadow-blue-500/20"
          >
            {savingSettings ? 'Saving All Profiles & Templates...' : 'Save All Country Profiles & Templates'}
          </Button>
        </div>
      </Card>

      {/* Add New Country Modal Dialog */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 space-y-5 shadow-2xl border border-gray-100 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{newCountryFlag || '🌐'}</span>
                <h3 className="text-lg font-bold text-gray-900">Add New Target Country Profile</h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <FiX className="text-xl" />
              </button>
            </div>

            <form onSubmit={handleCreateNewCountryProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="md:col-span-2">
                  <Input
                    label="Country Name"
                    placeholder="e.g. Canada"
                    value={newCountryName}
                    onChange={(e) => setNewCountryName(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <Input
                    label="Country Flag Emoji"
                    placeholder="e.g. 🇨🇦"
                    value={newCountryFlag}
                    onChange={(e) => setNewCountryFlag(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Start Time (IST)</label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-800 focus:border-blue-500 focus:outline-none"
                    placeholder="e.g. 06:00 PM"
                    value={newStartTime}
                    onChange={(e) => setNewStartTime(e.target.value)}
                    required
                  />
                  <span className="text-[10px] text-gray-400">Specify with AM/PM (e.g., 06:00 PM)</span>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">End Time (IST)</label>
                  <input
                    type="text"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-800 focus:border-blue-500 focus:outline-none"
                    placeholder="e.g. 11:00 PM"
                    value={newEndTime}
                    onChange={(e) => setNewEndTime(e.target.value)}
                    required
                  />
                  <span className="text-[10px] text-gray-400">Specify with AM/PM (e.g., 11:00 PM)</span>
                </div>
              </div>

              {/* Add Cities */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-gray-700">Target Cities / Locations</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none"
                    placeholder="Add city (e.g. Toronto, Canada)..."
                    value={newCityInput}
                    onChange={(e) => setNewCityInput(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={handleAddNewCityToModalList}
                    className="px-3 py-1.5 bg-blue-600 text-white font-bold text-xs rounded-lg hover:bg-blue-700 transition-all cursor-pointer"
                  >
                    Add City
                  </button>
                </div>

                <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto p-1 bg-gray-50 rounded-lg border border-gray-200">
                  {newCitiesList.map((city) => (
                    <span key={city} className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-white border border-gray-200 text-gray-800 rounded-md text-xs font-medium">
                      {city}
                      <button type="button" onClick={() => handleRemoveCityFromModalList(city)} className="text-gray-400 hover:text-red-500">
                        <FiX />
                      </button>
                    </span>
                  ))}
                  {newCitiesList.length === 0 && (
                    <span className="text-xs text-gray-400 italic p-1">No cities added yet.</span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-bold text-gray-600 hover:bg-gray-100 rounded-lg transition-all"
                >
                  Cancel
                </button>
                <Button variant="primary" type="submit" className="text-xs px-6 py-2">
                  Create Country Profile
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
