import React, { useState, useEffect, useRef } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import automationService from '../services/automationService';
import { FiGlobe, FiSettings, FiCheckCircle, FiAlertCircle, FiTag, FiClock } from 'react-icons/fi';

export default function CountryTemplates() {
  const [selectedCountryTab, setSelectedCountryTab] = useState('USA');
  const [countryTemplates, setCountryTemplates] = useState({});
  const [subjectTemplate, setSubjectTemplate] = useState('');
  const [bodyTemplate, setBodyTemplate] = useState('');
  const [redesignSubjectTemplate, setRedesignSubjectTemplate] = useState('');
  const [redesignBodyTemplate, setRedesignBodyTemplate] = useState('');

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
      setCountryTemplates(cTmpls);

      const activeTmpl = cTmpls[selectedCountryTab] || cTmpls['USA'] || {};
      setSubjectTemplate(activeTmpl.subject_template || settings.subject_template || '');
      setBodyTemplate(activeTmpl.body_template || settings.body_template || '');
      setRedesignSubjectTemplate(activeTmpl.redesign_subject_template || settings.redesign_subject_template || '');
      setRedesignBodyTemplate(activeTmpl.redesign_body_template || settings.redesign_body_template || '');
    } catch (err) {
      console.error(err);
      setError('Failed to load country email templates.');
    } finally {
      setLoading(false);
    }
  };

  const handleCountryTabChange = (newTab) => {
    // Save current active tab state
    const updated = {
      ...countryTemplates,
      [selectedCountryTab]: {
        subject_template: subjectTemplate,
        body_template: bodyTemplate,
        redesign_subject_template: redesignSubjectTemplate,
        redesign_body_template: redesignBodyTemplate
      }
    };
    setCountryTemplates(updated);
    setSelectedCountryTab(newTab);

    // Load target tab values
    const nextTmpl = updated[newTab] || {};
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

  const handleSaveTemplates = async () => {
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
        country_templates: finalCountryTemplates
      });
      setCountryTemplates(finalCountryTemplates);
      setSuccessMsg('Country email templates saved successfully!');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error(err);
      setError('Failed to save email templates.');
    } finally {
      setSavingSettings(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500 font-medium">Loading country email templates...</div>;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-blue-950 to-slate-900 p-6 rounded-2xl text-white shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-2 bg-blue-500/20 text-blue-400 rounded-xl text-xl">🌐</span>
            <h1 className="text-2xl font-black tracking-tight">Multi-Country Email Templates</h1>
          </div>
          <p className="text-sm text-slate-300">
            Configure localized, high-converting outreach pitches & redesign templates tailored for each country.
          </p>
        </div>

        {/* Country Tabs */}
        <div className="flex items-center gap-2 bg-slate-800/80 p-1.5 rounded-xl border border-slate-700">
          <button
            type="button"
            onClick={() => handleCountryTabChange('USA')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              selectedCountryTab === 'USA' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <span className="text-base">🇺🇸</span> United States (USA)
          </button>
          <button
            type="button"
            onClick={() => handleCountryTabChange('UK')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              selectedCountryTab === 'UK' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <span className="text-base">🇬🇧</span> United Kingdom (UK)
          </button>
          <button
            type="button"
            onClick={() => handleCountryTabChange('UAE')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
              selectedCountryTab === 'UAE' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            <span className="text-base">🇦🇪</span> Dubai (UAE)
          </button>
        </div>
      </div>

      {/* Target Schedule Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-3xl">
            {selectedCountryTab === 'USA' ? '🇺🇸' : selectedCountryTab === 'UK' ? '🇬🇧' : '🇦🇪'}
          </span>
          <div>
            <span className="font-bold text-gray-900 text-sm">
              {selectedCountryTab === 'USA' ? 'United States Outreach Profile' : selectedCountryTab === 'UK' ? 'United Kingdom Outreach Profile' : 'Dubai (UAE) Outreach Profile'}
            </span>
            <span className="text-xs text-gray-500 block flex items-center gap-1 mt-0.5">
              <FiClock className="text-blue-500" />
              Target Operating Window: <strong className="text-gray-700">
                {selectedCountryTab === 'USA' ? '01:00 AM – 04:00 AM IST' : selectedCountryTab === 'UK' ? '03:00 PM – 09:00 PM IST' : '10:00 AM – 02:00 PM IST'}
              </strong>
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-blue-700 bg-blue-100 px-3 py-1.5 rounded-lg border border-blue-200">
            Time-Slot Scheduler Active
          </span>
        </div>
      </div>

      {/* Standard Pitch Template Card */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiSettings className="text-blue-500" /> Standard Cold Email Pitch ({selectedCountryTab})
            </h3>
            <span className="text-xs text-gray-400">Pitches sent to businesses without a custom website.</span>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-gray-100 text-gray-600 rounded-lg">
            {selectedCountryTab} Standard Template
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
                rows="14"
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
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
        </div>
      </Card>

      {/* Redesign Pitch Template Card */}
      <Card className="space-y-4">
        <div className="flex items-center justify-between border-b border-gray-100 pb-3">
          <div>
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-1.5">
              <FiSettings className="text-blue-500" /> Redesign (Bad Website) Pitch ({selectedCountryTab})
            </h3>
            <span className="text-xs text-gray-400">Pitches sent exclusively to leads with outdated/slow/broken websites.</span>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-lg">
            {selectedCountryTab} Redesign Template
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
                rows="14"
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm text-gray-800 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
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
            onClick={handleSaveTemplates}
            disabled={savingSettings}
            className="text-sm px-8 py-2.5 font-bold shadow-lg shadow-blue-500/20"
          >
            {savingSettings ? 'Saving All Templates...' : `Save All ${selectedCountryTab} Templates`}
          </Button>
        </div>
      </Card>
    </div>
  );
}
