import React, { useState, useEffect } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import automationService from '../services/automationService';
import { useAuth } from '../context/AuthContext';
import { FiSave, FiAlertCircle, FiCheckCircle, FiMail, FiKey } from 'react-icons/fi';

export default function Settings() {
  const { user } = useAuth();
  
  // API credentials states
  const [openRouterKey, setOpenRouterKey] = useState('');
  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState('587');
  const [smtpEmail, setSmtpEmail] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError('');
      const settings = await automationService.getSettings();
      setOpenRouterKey(settings.openrouter_api_key || '');
      setSmtpHost(settings.smtp_host || 'smtp.gmail.com');
      setSmtpPort(String(settings.smtp_port || '587'));
      setSmtpEmail(settings.smtp_email || '');
      setSmtpPassword(settings.smtp_password || '');
    } catch (err) {
      console.error(err);
      setError('Failed to fetch settings from server.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await automationService.updateSettings({
        openrouter_api_key: openRouterKey,
        smtp_host: smtpHost,
        smtp_port: parseInt(smtpPort) || 587,
        smtp_email: smtpEmail,
        smtp_password: smtpPassword
      });
      setSuccess('Settings saved successfully! Autopilot will now use these credentials.');
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      console.error(err);
      setError('Failed to save settings. Please verify inputs.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[450px]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-8 font-inter">
      <div>
        <h2 className="text-xl font-bold text-gray-800 tracking-tight">Credentials & Settings</h2>
        <p className="text-gray-500 text-xs mt-1">Configure your custom OpenRouter API Key and SMTP credentials to send outreach emails directly from your own domain.</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <FiAlertCircle className="text-base" /> {error}
        </div>
      )}

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <FiCheckCircle className="text-base" /> {success}
        </div>
      )}

      <form onSubmit={handleSaveSettings}>
        <Card className="space-y-6">
          <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider border-b border-gray-100 pb-3 flex items-center gap-1.5">
            <FiKey className="text-blue-500" /> OpenRouter API Key
          </h3>
          
          <div className="space-y-4">
            <Input 
              label="OpenRouter API Key" 
              type="password" 
              placeholder="sk-or-v1-................................"
              value={openRouterKey}
              onChange={(e) => setOpenRouterKey(e.target.value)}
            />
            <p className="text-[10px] text-gray-400 leading-normal">
              Used to extract prospect greeting names dynamically and personalizing outreach drafts via OpenRouter models. If empty, the system falls back to default environment keys or rule-based greetings.
            </p>
          </div>

          <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider border-b border-gray-100 pb-3 pt-4 flex items-center gap-1.5">
            <FiMail className="text-blue-500" /> SMTP Configuration
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input 
              label="SMTP Host" 
              placeholder="e.g. smtp.gmail.com" 
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.target.value)}
            />
            <Input 
              label="SMTP Port" 
              placeholder="e.g. 587" 
              value={smtpPort}
              onChange={(e) => setSmtpPort(e.target.value)}
            />
            <Input 
              label="SMTP Username (Email Address)" 
              placeholder="e.g. your-email@gmail.com" 
              value={smtpEmail}
              onChange={(e) => setSmtpEmail(e.target.value)}
            />
            <Input 
              label="SMTP Password / App Password" 
              type="password" 
              placeholder="Enter password or Gmail App Password" 
              value={smtpPassword}
              onChange={(e) => setSmtpPassword(e.target.value)}
            />
          </div>
          <p className="text-[10px] text-gray-400 leading-normal">
            For Gmail: Make sure 2-Step Verification is active and generate a 16-character <strong>App Password</strong> instead of your normal password to prevent security blocks.
          </p>

          <div className="pt-4 flex justify-end border-t border-gray-100">
            <Button 
              type="submit" 
              disabled={saving}
              className="flex items-center gap-2 text-xs py-2.5 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white cursor-pointer shadow-sm font-semibold"
            >
              <FiSave /> {saving ? 'Saving Settings...' : 'Save API Settings'}
            </Button>
          </div>
        </Card>
      </form>

      {/* Profile Card (Static / visual presentation of logged in user) */}
      <Card>
        <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider border-b border-gray-100 pb-3 flex items-center gap-1.5">
          👤 User Profile Info
        </h3>
        <div className="space-y-6 pt-2">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-full bg-blue-100 flex items-center justify-center text-blue-750 text-xl font-bold border border-blue-200 shadow-sm uppercase select-none">
              {user?.first_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
            </div>
            <div>
              <p className="text-sm font-bold text-gray-800">{user?.first_name || 'Admin'} {user?.last_name || 'User'}</p>
              <p className="text-xs text-gray-400">{user?.email}</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input label="First Name" value={user?.first_name || 'Vivang'} disabled className="bg-gray-50" />
            <Input label="Last Name" value={user?.last_name || 'Mishra'} disabled className="bg-gray-50" />
            <Input label="Email Address" value={user?.email || 'user@company.com'} disabled className="bg-gray-50" />
            <Input label="Role" value="Administrator" disabled className="bg-gray-50" />
          </div>
        </div>
      </Card>
    </div>
  );
}
