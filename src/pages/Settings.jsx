import React, { useState, useEffect } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import automationService from '../services/automationService';
import authService from '../services/authService';
import { useAuth } from '../context/AuthContext';
import { FiSave, FiAlertCircle, FiCheckCircle, FiMail, FiKey } from 'react-icons/fi';

export default function Settings() {
  const { user, setUser } = useAuth();
  
  // API credentials states
  const [openRouterKey, setOpenRouterKey] = useState('');
  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState('587');
  const [smtpEmail, setSmtpEmail] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  
  // API provider options
  const [emailServiceProvider, setEmailServiceProvider] = useState('SMTP');
  const [resendApiKey, setResendApiKey] = useState('');
  const [sendgridApiKey, setSendgridApiKey] = useState('');
  const [sendgridSender, setSendgridSender] = useState('');

  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Profile Edit states
  const [profileFirstName, setProfileFirstName] = useState('');
  const [profileLastName, setProfileLastName] = useState('');
  const [profileEmail, setProfileEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (user) {
      setProfileFirstName(user.first_name || '');
      setProfileLastName(user.last_name || '');
      setProfileEmail(user.email || '');
    }
  }, [user]);

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
      setEmailServiceProvider(settings.email_service_provider || 'SMTP');
      setResendApiKey(settings.resend_api_key || '');
      setSendgridApiKey(settings.sendgrid_api_key || '');
      setSendgridSender(settings.sendgrid_sender || '');
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
        smtp_password: smtpPassword,
        email_service_provider: emailServiceProvider,
        resend_api_key: resendApiKey,
        sendgrid_api_key: sendgridApiKey,
        sendgrid_sender: sendgridSender
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

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileError('');
    setProfileSuccess('');

    if (newPassword) {
      if (!currentPassword) {
        setProfileError('Current password is required to change password.');
        setProfileSaving(false);
        return;
      }
      if (newPassword.length < 8) {
        setProfileError('New password must be at least 8 characters long.');
        setProfileSaving(false);
        return;
      }
      if (newPassword !== confirmPassword) {
        setProfileError('New passwords do not match.');
        setProfileSaving(false);
        return;
      }
    }

    try {
      const updated = await authService.updateProfile({
        first_name: profileFirstName,
        last_name: profileLastName,
        email: profileEmail,
        current_password: currentPassword || null,
        new_password: newPassword || null
      });

      setUser(updated);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      
      setProfileSuccess('Profile updated successfully!');
      setTimeout(() => setProfileSuccess(''), 4000);
    } catch (err) {
      console.error(err);
      const errMsg = err.response?.data?.detail || 'Failed to update user profile.';
      setProfileError(errMsg);
    } finally {
      setProfileSaving(false);
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
            <FiMail className="text-blue-500" /> Outbound Emailing Configuration
          </h3>

          <div className="space-y-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-gray-600">Email Service Provider</label>
              <select
                className="w-full text-xs rounded-lg border border-gray-200 p-2.5 bg-white text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 shadow-sm"
                value={emailServiceProvider}
                onChange={(e) => setEmailServiceProvider(e.target.value)}
              >
                <option value="SMTP">SMTP Server (Gmail, Outlook, custom domains - blocked on Render Free tier)</option>
                <option value="Resend">Resend API (HTTP-based - Recommended for Render Free tier)</option>
                <option value="SendGrid">SendGrid API (HTTP-based - Alternative for Render Free tier)</option>
              </select>
            </div>
          </div>

          {emailServiceProvider === 'SMTP' && (
            <>
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
            </>
          )}

          {emailServiceProvider === 'Resend' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Input 
                  label="Resend API Key" 
                  type="password" 
                  placeholder="re_........................" 
                  value={resendApiKey}
                  onChange={(e) => setResendApiKey(e.target.value)}
                />
                <Input 
                  label="Sender Email Address (Must be verified in Resend)" 
                  placeholder="e.g. info@yourdomain.com (or onboarding@resend.dev for test account)" 
                  value={smtpEmail}
                  onChange={(e) => setSmtpEmail(e.target.value)}
                />
              </div>
              <p className="text-[10px] text-gray-400 leading-normal">
                Create a free account at <a href="https://resend.com" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">resend.com</a> to get an API Key. Resend allows 3,000 free emails/month. If using a custom domain, configure it under Domains in your Resend Dashboard.
              </p>
            </div>
          )}

          {emailServiceProvider === 'SendGrid' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Input 
                  label="SendGrid API Key" 
                  type="password" 
                  placeholder="SG........................." 
                  value={sendgridApiKey}
                  onChange={(e) => setSendgridApiKey(e.target.value)}
                />
                <Input 
                  label="SendGrid Verified Sender Email" 
                  placeholder="e.g. outreach@yourcompany.com" 
                  value={sendgridSender}
                  onChange={(e) => setSendgridSender(e.target.value)}
                />
              </div>
              <p className="text-[10px] text-gray-400 leading-normal">
                To send emails via SendGrid, configure Single Sender Verification or Domain Authentication in your SendGrid settings, and enter the verified sender email address here.
              </p>
            </div>
          )}


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

      {/* Profile Card */}
      <form onSubmit={handleUpdateProfile}>
        <Card className="space-y-6">
          <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider border-b border-gray-100 pb-3 flex items-center gap-1.5">
            👤 User Profile Info
          </h3>
          
          {profileError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
              <FiAlertCircle className="text-base" /> {profileError}
            </div>
          )}

          {profileSuccess && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
              <FiCheckCircle className="text-base" /> {profileSuccess}
            </div>
          )}

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
            <Input 
              label="First Name" 
              value={profileFirstName} 
              onChange={(e) => setProfileFirstName(e.target.value)} 
            />
            <Input 
              label="Last Name" 
              value={profileLastName} 
              onChange={(e) => setProfileLastName(e.target.value)} 
            />
            <Input 
              label="Email Address" 
              type="email"
              value={profileEmail} 
              onChange={(e) => setProfileEmail(e.target.value)} 
            />
            <Input 
              label="Role" 
              value={user?.role === 'admin' ? 'Administrator' : user?.role || 'User'} 
              disabled 
              className="bg-gray-50 text-gray-500 cursor-not-allowed" 
            />
          </div>

          <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider border-b border-gray-50 pb-2 pt-4">
            🔐 Change Password (Optional)
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Input 
              label="Current Password" 
              type="password" 
              placeholder="Required for password change"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <Input 
              label="New Password" 
              type="password" 
              placeholder="Min 8 characters"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <Input 
              label="Confirm New Password" 
              type="password" 
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          <div className="pt-4 flex justify-end border-t border-gray-100">
            <Button 
              type="submit" 
              disabled={profileSaving}
              className="flex items-center gap-2 text-xs py-2.5 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white cursor-pointer shadow-sm font-semibold"
            >
              <FiSave /> {profileSaving ? 'Updating Profile...' : 'Update Profile'}
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
}
