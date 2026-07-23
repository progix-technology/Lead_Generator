import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import { FiEdit3, FiEye, FiSend, FiCpu, FiX } from 'react-icons/fi';
import companyService from '../services/companyService';

export default function EmailCampaign() {
  const [searchParams] = useSearchParams();
  const targetCompanyId = searchParams.get('companyId');

  const [highlightedVar, setHighlightedVar] = useState(null);
  
  const escapeHTML = (str) => {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  };

  const [subject, setSubject] = useState(() => sessionStorage.getItem('campaign_subject_v3') || 'Helping {{company}} Strengthen Its Online Presence');
  const [template, setTemplate] = useState(() => sessionStorage.getItem('campaign_template_v3') || `Hello {{first_name}},

I hope you're doing well.

While researching businesses in the {{industry}} sector across {{location}}, I came across {{company}}. I was impressed by your local presence and the reputation you've built within your community.

I noticed that customers currently rely primarily on {{current_platform}}, as there doesn't appear to be a dedicated business website. While social media and business listings are great for visibility, many customers prefer visiting a professional website before making a purchase, booking a service, or getting in touch.

A dedicated website could help you:

• Showcase your {{service_type}} with a clean, modern design
• Display your contact information, business hours, and location in one place
• Improve your visibility on Google through local SEO
• Promote offers, announcements, and new services more effectively
• Build greater trust with new customers and strengthen your brand online

At Progix Technologies LLP, we help businesses create modern, mobile-friendly websites designed to improve customer experience, increase online visibility, and generate more direct enquiries.

If you're interested, we'd be happy to prepare a complimentary homepage concept tailored specifically for {{company}}, along with a few ideas on how your online presence could be further enhanced.

Thank you for your time, and I look forward to hearing from you.

Best Regards,

Abhinandan Dubey
Progix Technologies LLP
📞 +1 (916) 702-8905
✉️ info@progixtechnology.com
🌐 https://www.progixtechnology.com/`);
  
  const [targetCompany, setTargetCompany] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  // AI Modal States
  const [showAIModal, setShowAIModal] = useState(false);
  const [agencyName, setAgencyName] = useState(() => localStorage.getItem('agency_name') || 'Progix Technologies LLP');
  const [services, setServices] = useState(() => localStorage.getItem('agency_services') || 'Web Development, SEO optimization, and UI Redesign');
  const [portfolio, setPortfolio] = useState(() => localStorage.getItem('agency_portfolio') || 'Free website audit report and a 1-page design mockup');
  const [cta, setCta] = useState(() => localStorage.getItem('agency_cta') || 'a quick 5-minute feedback call next Tuesday');
  const [aiGenerating, setAiGenerating] = useState(false);

  // Helper function to render variable replacement on the fly in the preview/editor
  const renderTemplatePreview = (text, company = targetCompany) => {
    if (!text) return '';
    const compName = company ? company.name : 'Bella Bakery';
    
    // Resolve smart greeting name
    let firstName = 'Bella';
    if (company) {
      firstName = 'Team';
      if (company.name) {
        let personalEmail = true;
        if (company.email) {
          const prefix = company.email.split('@')[0].toLowerCase();
          const generics = ['info', 'contact', 'support', 'hello', 'sales', 'admin', 'jobs', 'office', 'team'];
          for (const generic of generics) {
            if (prefix.startsWith(generic)) {
              personalEmail = false;
              break;
            }
          }
          if (personalEmail) {
            const namePart = prefix.replace(/\./g, '_').replace(/-/g, '_').split('_')[0];
            if (namePart.length > 2) {
              firstName = namePart.charAt(0).toUpperCase() + namePart.slice(1);
            } else {
              personalEmail = false;
            }
          }
        }
        if (!personalEmail) {
          const businessKeywords = ['bakery', 'restaurant', 'llp', 'plumbing', 'inc', 'co', 'corp', 'tech', 'services', 'clinic', 'dent', 'shop', 'salon', 'group', 'ltd', 'limited', 'firm', 'agency', 'bar', 'cafe', 'pizzeria'];
          const lowerName = company.name.toLowerCase();
          const isBusiness = businessKeywords.some(k => lowerName.includes(k));
          if (isBusiness) {
            const words = company.name.split(' ');
            if (words.length > 3) {
              firstName = words.slice(0, 2).join(' ') + ' Team';
            } else {
              firstName = company.name + ' Team';
            }
          } else {
            firstName = company.name.split(' ')[0];
          }
        }
      }
    }

    const websiteUrl = company ? (company.website || 'your website') : 'bellabakery.com';
    const ind = company ? (company.industry || 'Local Business') : 'Bakery';
    const loc = company ? (company.location || 'Kingsburg, CA') : 'Kingsburg, CA';
    
    // Dynamically resolve current_platform
    let platform = 'social media profiles';
    if (company) {
      if (company.email_source === 'Facebook') platform = 'Facebook';
      else if (company.email_source === 'Instagram') platform = 'Instagram';
      else if (company.email_source === 'LinkedIn') platform = 'LinkedIn';
      else if (company.website) platform = 'directories and online listings';
    } else {
      platform = 'Facebook';
    }

    // Dynamically resolve service_type based on industry
    let service = 'services and offerings';
    const indLower = ind.toLowerCase();
    if (indLower.includes('bakery') || indLower.includes('bake')) {
      service = 'bakery products and custom cakes';
    } else if (indLower.includes('restaurant') || indLower.includes('food') || indLower.includes('cafe')) {
      service = 'menu offerings and dining experience';
    } else if (indLower.includes('plumb')) {
      service = 'plumbing services and rapid repairs';
    } else if (indLower.includes('dent') || indLower.includes('clinic')) {
      service = 'dental treatments and patient care';
    } else if (indLower.includes('salon') || indLower.includes('hair') || indLower.includes('beauty')) {
      service = 'beauty treatments and styling services';
    }

    return text
      .replace(/{{first_name}}/g, firstName)
      .replace(/{{company}}/g, compName)
      .replace(/{{website}}/g, websiteUrl)
      .replace(/{{industry}}/g, ind)
      .replace(/{{location}}/g, loc)
      .replace(/{{current_platform}}/g, platform)
      .replace(/{{service_type}}/g, service);
  };

  const renderTemplatePreviewHTML = (text, company = targetCompany) => {
    if (!text) return '';
    let escaped = escapeHTML(text);
    
    const compName = company ? company.name : 'Bella Bakery';
    
    // Resolve smart greeting name
    let firstName = 'Bella';
    if (company) {
      firstName = 'Team';
      if (company.name) {
        let personalEmail = true;
        if (company.email) {
          const prefix = company.email.split('@')[0].toLowerCase();
          const generics = ['info', 'contact', 'support', 'hello', 'sales', 'admin', 'jobs', 'office', 'team'];
          for (const generic of generics) {
            if (prefix.startsWith(generic)) {
              personalEmail = false;
              break;
            }
          }
          if (personalEmail) {
            const namePart = prefix.replace(/\./g, '_').replace(/-/g, '_').split('_')[0];
            if (namePart.length > 2) {
              firstName = namePart.charAt(0).toUpperCase() + namePart.slice(1);
            } else {
              personalEmail = false;
            }
          }
        }
        if (!personalEmail) {
          const businessKeywords = ['bakery', 'restaurant', 'llp', 'plumbing', 'inc', 'co', 'corp', 'tech', 'services', 'clinic', 'dent', 'shop', 'salon', 'group', 'ltd', 'limited', 'firm', 'agency', 'bar', 'cafe', 'pizzeria'];
          const lowerName = company.name.toLowerCase();
          const isBusiness = businessKeywords.some(k => lowerName.includes(k));
          if (isBusiness) {
            const words = company.name.split(' ');
            if (words.length > 3) {
              firstName = words.slice(0, 2).join(' ') + ' Team';
            } else {
              firstName = company.name + ' Team';
            }
          } else {
            firstName = company.name.split(' ')[0];
          }
        }
      }
    }

    const websiteUrl = company ? (company.website || 'your website') : 'bellabakery.com';
    const ind = company ? (company.industry || 'Local Business') : 'Bakery';
    const loc = company ? (company.location || 'Kingsburg, CA') : 'Kingsburg, CA';
    
    // Dynamically resolve current_platform
    let platform = 'social media profiles';
    if (company) {
      if (company.email_source === 'Facebook') platform = 'Facebook';
      else if (company.email_source === 'Instagram') platform = 'Instagram';
      else if (company.email_source === 'LinkedIn') platform = 'LinkedIn';
      else if (company.website) platform = 'directories and online listings';
    } else {
      platform = 'Facebook';
    }

    // Dynamically resolve service_type based on industry
    let service = 'services and offerings';
    const indLower = ind.toLowerCase();
    if (indLower.includes('bakery') || indLower.includes('bake')) {
      service = 'bakery products and custom cakes';
    } else if (indLower.includes('restaurant') || indLower.includes('food') || indLower.includes('cafe')) {
      service = 'menu offerings and dining experience';
    } else if (indLower.includes('plumb')) {
      service = 'plumbing services and rapid repairs';
    } else if (indLower.includes('dent') || indLower.includes('clinic')) {
      service = 'dental treatments and patient care';
    } else if (indLower.includes('salon') || indLower.includes('hair') || indLower.includes('beauty')) {
      service = 'beauty treatments and styling services';
    }

    const variablesMap = {
      '{{first_name}}': firstName,
      '{{company}}': compName,
      '{{website}}': websiteUrl,
      '{{industry}}': ind,
      '{{location}}': loc,
      '{{current_platform}}': platform,
      '{{service_type}}': service
    };

    Object.entries(variablesMap).forEach(([key, val]) => {
      const isHighlighted = highlightedVar === key;
      const replacement = isHighlighted
        ? `<span class="bg-yellow-200 border border-yellow-300 text-yellow-900 font-bold px-1.5 py-0.5 rounded transition-all duration-300 animate-pulse">${val}</span>`
        : val;
        
      if (escaped.includes(key)) {
        // Raw brackets (Campaign Mode)
        const regex = new RegExp(key.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'), 'g');
        escaped = escaped.replace(regex, replacement);
      } else if (isHighlighted && val) {
        // Resolved text (Single Lead Mode) - highlight the resolved value in preview
        const escapedVal = val.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&');
        const regex = new RegExp(escapedVal, 'g');
        escaped = escaped.replace(regex, replacement);
      }
    });

    return escaped.replace(/\n/g, '<br>');
  };

  // Load target company details if companyId exists
  useEffect(() => {
    const fetchTargetCompany = async () => {
      try {
        const data = await companyService.getCompanyById(targetCompanyId);
        setTargetCompany(data);
        
        // Auto-resolve template values directly in the Editor boxes!
        setSubject(prev => renderTemplatePreview(prev, data));
        setTemplate(prev => renderTemplatePreview(prev, data));
      } catch (err) {
        console.error("Failed to load target company", err);
      }
    };
    if (targetCompanyId) {
      fetchTargetCompany();
    } else {
      setTargetCompany(null);
    }
  }, [targetCompanyId]);

  // Sync campaign template and subject to sessionStorage (only if not targeting a single lead)
  useEffect(() => {
    if (!targetCompanyId) {
      sessionStorage.setItem('campaign_subject_v3', subject);
    }
  }, [subject, targetCompanyId]);

  useEffect(() => {
    if (!targetCompanyId) {
      sessionStorage.setItem('campaign_template_v3', template);
    }
  }, [template, targetCompanyId]);

  // Save agency profile variables
  useEffect(() => {
    localStorage.setItem('agency_name', agencyName);
  }, [agencyName]);

  useEffect(() => {
    localStorage.setItem('agency_services', services);
  }, [services]);

  useEffect(() => {
    localStorage.setItem('agency_portfolio', portfolio);
  }, [portfolio]);

  useEffect(() => {
    localStorage.setItem('agency_cta', cta);
  }, [cta]);

  const handleSendCampaign = async () => {
    setLoading(true);
    setStatusMessage(targetCompanyId ? `Sending outreach email to ${targetCompany?.name || 'lead'}...` : 'Initiating email campaign...');
    try {
      const response = await companyService.sendCampaign(subject, template, targetCompanyId);
      setStatusMessage(targetCompanyId 
        ? `Success! Outreach email successfully delivered to ${targetCompany?.name || 'lead'}.`
        : `Success! Sent ${response.sent_count} emails. Failed: ${response.failed_count}`);
    } catch (err) {
      console.error(err);
      setStatusMessage('Failed to trigger campaign. Please verify your SMTP configurations.');
    } finally {
      setLoading(false);
    }
  };

  const handleExitDirectMode = () => {
    // Restore raw templates from session storage
    setSubject(sessionStorage.getItem('campaign_subject_v3') || 'Helping {{company}} Strengthen Its Online Presence');
    setTemplate(sessionStorage.getItem('campaign_template_v3') || `Hello {{first_name}},

I hope you're doing well.

While researching businesses in the {{industry}} sector across {{location}}, I came across {{company}}. I was impressed by your local presence and the reputation you've built within your community.

I noticed that customers currently rely primarily on {{current_platform}}, as there doesn't appear to be a dedicated business website. While social media and business listings are great for visibility, many customers prefer visiting a professional website before making a purchase, booking a service, or getting in touch.

A dedicated website could help you:

• Showcase your {{service_type}} with a clean, modern design
• Display your contact information, business hours, and location in one place
• Improve your visibility on Google through local SEO
• Promote offers, announcements, and new services more effectively
• Build greater trust with new customers and strengthen your brand online

At Progix Technologies LLP, we help businesses create modern, mobile-friendly websites designed to improve customer experience, increase online visibility, and generate more direct enquiries.

If you're interested, we'd be happy to prepare a complimentary homepage concept tailored specifically for {{company}}, along with a few ideas on how your online presence could be further enhanced.

Thank you for your time, and I look forward to hearing from you.

Best Regards,

Abhinandan Dubey
Progix Technologies LLP
📞 +1 (916) 702-8905
✉️ progixtechnology@gmail.com
🌐 https://www.progixtechnology.com/`);
    setTargetCompany(null);
    window.history.replaceState({}, '', '/campaign');
  };

  const handleGenerateAITemplate = async () => {
    setAiGenerating(true);
    setStatusMessage('Generating professional template via OpenRouter...');
    try {
      const response = await companyService.generateAITemplate(agencyName, services, portfolio, cta);
      if (response.subject && response.body) {
        setSubject(response.subject);
        setTemplate(response.body);
        setStatusMessage('Success! Professional email template generated by AI.');
        setShowAIModal(false);
      } else {
        setStatusMessage('AI returned empty templates. Check your API settings.');
      }
    } catch (err) {
      console.error(err);
      setStatusMessage('Failed to connect to AI server. Verify the OPENROUTER_API_KEY in your backend .env file.');
    } finally {
      setAiGenerating(false);
    }
  };

  return (
    <div className="space-y-6 relative font-inter">
      {/* Top Dark Banner Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 rounded-2xl text-white shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-blue-500/20 text-blue-400 rounded-xl text-xl">✉️</span>
            <h1 className="text-2xl font-black tracking-tight">Manual & Bulk Email Outreach</h1>
          </div>
          <p className="text-sm text-slate-300">
            Craft custom email pitches with dynamic tags or trigger single-lead direct outreach.
          </p>
        </div>
        <Button 
          variant="primary" 
          className="flex items-center gap-2 shadow-md bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl border border-blue-500/50 cursor-pointer self-start lg:self-auto"
          onClick={handleSendCampaign}
          disabled={loading || (targetCompanyId && !targetCompany)}
        >
          <FiSend /> {loading ? 'Sending...' : targetCompany ? `Send Email to ${targetCompany.name}` : 'Send Campaign'}
        </Button>
      </div>

      {targetCompany && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-xl flex justify-between items-center text-sm font-semibold shadow-sm animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-blue-600 rounded-full animate-pulse"></span>
            <span>Single Lead Outreach Mode: Sending email only to <span className="underline">{targetCompany.name}</span> ({targetCompany.email || 'No email saved'})</span>
          </div>
          <button 
            onClick={handleExitDirectMode}
            className="text-blue-600 hover:text-blue-800 font-bold flex items-center gap-1 cursor-pointer"
          >
            Exit Direct Mode <FiX />
          </button>
        </div>
      )}

      {statusMessage && (
        <div className={`p-4 rounded-xl text-sm font-semibold border ${
          statusMessage.startsWith('Success') 
            ? 'bg-green-50 border-green-200 text-green-800' 
            : statusMessage.startsWith('Failed')
            ? 'bg-red-50 border-red-200 text-red-800'
            : 'bg-blue-50 border-blue-200 text-blue-800'
        }`}>
          {statusMessage}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2"><FiEdit3 /> Template Editor</h3>
            <Button 
              variant="secondary" 
              className="text-sm py-1 px-3 flex items-center gap-2 border border-blue-200 text-blue-600 hover:bg-blue-50/50"
              onClick={() => setShowAIModal(true)}
            >
              <FiCpu /> AI Generate
            </Button>
          </div>
          
          <div className="space-y-4">
            <Input 
              label="Subject Line" 
              value={subject} 
              onChange={(e) => setSubject(e.target.value)} 
            />
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email Body</label>
              <textarea 
                className="w-full px-4 py-2 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all duration-200 h-64 resize-none font-sans"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
              />
            </div>
            
            <div>
              <span className="text-sm font-medium text-gray-700 block mb-1">Available Variables (Click to highlight in Preview, click + to insert):</span>
              <div className="flex gap-2 mt-2 flex-wrap">
                {['{{first_name}}', '{{company}}', '{{website}}', '{{industry}}', '{{location}}', '{{current_platform}}', '{{service_type}}'].map(v => {
                  const isHighlighted = highlightedVar === v;
                  return (
                    <span 
                      key={v} 
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-full border bg-gray-100 text-gray-600 border-gray-200 hover:bg-gray-200 select-none"
                    >
                      <span 
                        className="cursor-pointer hover:underline font-mono"
                        onClick={() => setHighlightedVar(prev => prev === v ? null : v)}
                      >
                        {v}
                      </span>
                      <button
                        className="pl-1.5 ml-1 border-l hover:text-blue-500 font-extrabold text-xs transition-colors border-gray-300 text-gray-400"
                        onClick={() => {
                          setTemplate(prev => prev + ' ' + v);
                        }}
                        title={`Insert ${v} into template`}
                      >
                        +
                      </button>
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2"><FiEye /> Preview ({targetCompany ? targetCompany.name : 'Example Lead'})</h3>
          
          <div className="border border-gray-200 rounded-xl overflow-hidden shadow-sm">
            <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 text-sm">
              <div className="mb-1"><span className="text-gray-500 font-medium">To:</span> {targetCompany ? (targetCompany.email || 'No email saved for this company') : 'contact@bellabakery.com'}</div>
              <div className="flex gap-1"><span className="text-gray-500 font-medium">Subject:</span> <span dangerouslySetInnerHTML={{ __html: renderTemplatePreviewHTML(subject) }} /></div>
            </div>
            <div 
              className="p-4 bg-white min-h-[16rem] text-sm text-gray-700 font-sans leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderTemplatePreviewHTML(template) }}
            />
          </div>
        </Card>
      </div>

      {/* AI Modal Overlay */}
      {showAIModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-2xl max-w-lg w-full overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                  <FiCpu className="text-primary" /> AI Template Generator
                </h3>
                <p className="text-xs text-gray-500 mt-1">Provide details about your business to generate custom cold pitch email templates.</p>
              </div>
              <button 
                className="text-gray-400 hover:text-gray-600 transition-colors"
                onClick={() => setShowAIModal(false)}
              >
                <FiX size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <Input 
                label="Your Business / Agency Name" 
                value={agencyName} 
                onChange={(e) => setAgencyName(e.target.value)} 
                placeholder="e.g. Progix Technology"
              />
              <Input 
                label="Core Services Offered" 
                value={services} 
                onChange={(e) => setServices(e.target.value)} 
                placeholder="e.g. Web Development, SEO optimization, and UI Redesign"
              />
              <Input 
                label="Your Offer / Case Study details" 
                value={portfolio} 
                onChange={(e) => setPortfolio(e.target.value)} 
                placeholder="e.g. Free website audit report and a 1-page design mockup"
              />
              <Input 
                label="Call to Action (CTA)" 
                value={cta} 
                onChange={(e) => setCta(e.target.value)} 
                placeholder="e.g. a quick 5-minute feedback call next Tuesday"
              />
            </div>
            
            <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100">
              <Button 
                variant="secondary" 
                onClick={() => setShowAIModal(false)}
                disabled={aiGenerating}
              >
                Cancel
              </Button>
              <Button 
                variant="primary" 
                onClick={handleGenerateAITemplate}
                disabled={aiGenerating}
                className="flex items-center gap-2"
              >
                {aiGenerating ? 'Generating...' : 'Generate Template ✨'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
