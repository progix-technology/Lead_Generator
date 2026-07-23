import React, { useState, useEffect } from 'react';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import Badge from '../components/Badge';
import { FiSearch, FiFilter } from 'react-icons/fi';
import companyService from '../services/companyService';

export default function CompanySearch() {
  // Load initial state from sessionStorage to persist across tab switches
  const [query, setQuery] = useState(() => sessionStorage.getItem('search_query') || '');
  const [location, setLocation] = useState(() => sessionStorage.getItem('search_location') || '');
  const [noWebsiteOnly, setNoWebsiteOnly] = useState(() => sessionStorage.getItem('search_nowebsite') === 'true');
  const [results, setResults] = useState(() => {
    const saved = sessionStorage.getItem('search_results');
    return saved ? JSON.parse(saved) : [];
  });
  const [emails, setEmails] = useState(() => {
    const saved = sessionStorage.getItem('search_emails');
    return saved ? JSON.parse(saved) : {};
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [emailLoading, setEmailLoading] = useState({});
  const [saveLoading, setSaveLoading] = useState({});
  const [savedCompanies, setSavedCompanies] = useState({});
  
  // New States for Pagination & Bulk Scanning
  const [nextPageToken, setNextPageToken] = useState(() => sessionStorage.getItem('search_next_token') || null);
  const [bulkFinding, setBulkFinding] = useState(false);
  const stopBulkRef = React.useRef(false);

  // New States for Filtering
  const [sourceFilter, setSourceFilter] = useState('all');
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [dbSavedCompanies, setDbSavedCompanies] = useState(new Set());

  // Load saved company names from database on component mount
  useEffect(() => {
    const fetchSavedCompaniesFromDB = async () => {
      try {
        const response = await companyService.getCompanies(0, 1000);
        if (response && response.data) {
          const names = response.data.map(c => c.name);
          setDbSavedCompanies(new Set(names));
        }
      } catch (err) {
        console.error("Failed to load saved leads from DB:", err);
      }
    };
    fetchSavedCompaniesFromDB();
  }, []);

  // Sync state to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('search_query', query);
  }, [query]);

  useEffect(() => {
    sessionStorage.setItem('search_location', location);
  }, [location]);

  useEffect(() => {
    sessionStorage.setItem('search_nowebsite', noWebsiteOnly);
  }, [noWebsiteOnly]);

  useEffect(() => {
    sessionStorage.setItem('search_results', JSON.stringify(results));
  }, [results]);

  useEffect(() => {
    sessionStorage.setItem('search_emails', JSON.stringify(emails));
  }, [emails]);

  useEffect(() => {
    if (nextPageToken) {
      sessionStorage.setItem('search_next_token', nextPageToken);
    } else {
      sessionStorage.removeItem('search_next_token');
    }
  }, [nextPageToken]);

  const handleSearch = async () => {
    if (!query) {
      setError('Please enter a business category (e.g., Beauty Products, Grocery Stores)');
      return;
    }
    setError('');
    setLoading(true);
    setNextPageToken(null);
    try {
      const response = await companyService.searchLiveCompanies(query, location);
      setResults(response.data || []);
      setNextPageToken(response.nextPageToken || null);
    } catch (err) {
      setError('Failed to fetch companies. Please check your API key or try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = async () => {
    if (!nextPageToken) return;
    setError('');
    setLoading(true);
    try {
      const response = await companyService.searchLiveCompanies(query, location, nextPageToken);
      setResults(prev => [...prev, ...(response.data || [])]);
      setNextPageToken(response.nextPageToken || null);
    } catch (err) {
      setError('Failed to load more results. Try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBulkFindEmails = async () => {
    stopBulkRef.current = false;
    setBulkFinding(true);
    
    // Find all leads that need email lookups
    const pending = [];
    filteredResults.forEach((company, index) => {
      const key = company.name;
      const hasEmail = emails[key] && emails[key] !== 'Not Found' && emails[key] !== 'Error';
      if (!hasEmail) {
        pending.push({ company, index });
      }
    });

    if (pending.length === 0) {
      setBulkFinding(false);
      return;
    }

    // Run scans concurrently in batches of 3 to optimize speed
    const batchSize = 3;
    for (let i = 0; i < pending.length; i += batchSize) {
      if (stopBulkRef.current) break;
      const batch = pending.slice(i, i + batchSize);
      await Promise.all(
        batch.map(({ company, index }) => 
          handleFindEmail(company, index)
        )
      );
    }
    
    setBulkFinding(false);
  };

  const handleStopBulkFind = () => {
    stopBulkRef.current = true;
    setBulkFinding(false);
  };

  // Filter results dynamically based on Google Places website_url, email discovery source, and saved status.
  const filteredResults = React.useMemo(() => {
    let temp = results;
    if (noWebsiteOnly) {
      temp = temp.filter(c => !c.website_url && !c.discovered_website_url);
    }
    if (sourceFilter !== 'all') {
      temp = temp.filter(c => {
        const emailObj = emails[c.name];
        if (!emailObj || typeof emailObj !== 'object') return false;
        return emailObj.source === sourceFilter;
      });
    }
    // Filter out already saved/emailed companies (both from local state and DB)
    temp = temp.filter(c => !savedCompanies[c.name] && !dbSavedCompanies.has(c.name));
    return temp;
  }, [results, noWebsiteOnly, sourceFilter, emails, savedCompanies, dbSavedCompanies]);

  const handleFindEmail = async (company, index) => {
    const key = company.name;
    setEmailLoading(prev => ({ ...prev, [key]: true }));
    try {
      const response = await companyService.findCompanyEmail(company.name, location);
      if (response.website_url) {
        // A website was found! Update the company details, but keep it in the list
        setResults(prevResults => {
          const updated = [...prevResults];
          updated[index] = {
            ...updated[index],
            discovered_website_url: response.website_url
          };
          return updated;
        });
        if (response.email) {
          setEmails(prev => ({ 
            ...prev, 
            [key]: { email: response.email, source: response.email_source } 
          }));
        }
      } else if (response.email) {
        setEmails(prev => ({ 
          ...prev, 
          [key]: { email: response.email, source: response.email_source } 
        }));
      } else {
        setEmails(prev => ({ ...prev, [key]: 'Not Found' }));
      }
    } catch (err) {
      console.error(err);
      setEmails(prev => ({ ...prev, [key]: 'Error' }));
    } finally {
      setEmailLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const handleSaveLead = async (company, index) => {
    const key = company.name;
    setSaveLoading(prev => ({ ...prev, [key]: true }));
    try {
      const emailVal = emails[key];
      let email = null;
      if (emailVal) {
        email = typeof emailVal === 'string' 
          ? (emailVal !== 'Not Found' && emailVal !== 'Error' ? emailVal : null)
          : (emailVal.email && emailVal.email !== 'Not Found' && emailVal.email !== 'Error' ? emailVal.email : null);
      }
      
      await companyService.createCompany({
        name: company.name,
        industry: company.industry || 'Local Business',
        location: location || company.address || '',
        website: company.website_url || company.discovered_website_url || null,
        phone: company.phone_number || null,
        email: email,
        email_source: (emailVal && typeof emailVal === 'object') ? emailVal.source : null,
        status: 'Pending'
      });
      
      // Update saved state to trigger filteredResults removal
      setSavedCompanies(prev => ({ ...prev, [key]: true }));
      setDbSavedCompanies(prev => {
        const updated = new Set(prev);
        updated.add(key);
        return updated;
      });
    } catch (err) {
      console.error("Save lead error:", err);
      alert("Failed to save lead: " + (err.response?.data?.detail || err.message));
    } finally {
      setSaveLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Dark Banner Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 rounded-2xl text-white shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-blue-500/20 text-blue-400 rounded-xl text-xl">🔍</span>
            <h1 className="text-2xl font-black tracking-tight">Smart Lead Finder & Social Scraper</h1>
          </div>
          <p className="text-sm text-slate-300">
            Search Google Places for local businesses, extract social emails (Facebook, Instagram, LinkedIn), and filter leads.
          </p>
        </div>
        <Button 
          variant={showFilterPanel ? "primary" : "secondary"} 
          className="flex items-center gap-2 text-xs py-2.5 px-4 font-bold rounded-xl shadow-md border border-slate-700 bg-slate-800 text-white hover:bg-slate-700 cursor-pointer self-start lg:self-auto"
          onClick={() => setShowFilterPanel(prev => !prev)}
        >
          <FiFilter /> {showFilterPanel ? 'Hide Advanced Filters' : 'Advanced Filters'}
        </Button>
      </div>

      <Card>
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
          <Input 
            label="Business Category / Query" 
            placeholder="e.g. Bakeries" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <Input 
            label="Location" 
            placeholder="e.g. California" 
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
          <div className="flex items-end">
            <Button 
              className="w-full flex items-center justify-center gap-2"
              onClick={handleSearch}
              disabled={loading}
            >
              <FiSearch /> {loading ? 'Searching...' : 'Search Google Maps'}
            </Button>
          </div>
        </div>
        
        <div className="flex items-center mt-2">
          <label className="flex items-center cursor-pointer">
            <input 
              type="checkbox" 
              className="form-checkbox h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              checked={noWebsiteOnly}
              onChange={(e) => setNoWebsiteOnly(e.target.checked)}
            />
            <span className="ml-2 text-sm text-gray-700 font-medium">
              🎯 Show ONLY businesses WITHOUT a website (Best Leads for Web Dev)
            </span>
          </label>
        </div>

        {showFilterPanel && (
          <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
            <div>
              <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Filter by Email Source:</label>
              <div className="flex gap-2 flex-wrap">
                {[
                  { id: 'all', label: 'All Sources' },
                  { id: 'Website', label: 'via Website' },
                  { id: 'Facebook', label: 'via Facebook' },
                  { id: 'Instagram', label: 'via Instagram' },
                  { id: 'WHOIS Registry', label: 'via WHOIS' }
                ].map(source => {
                  const isActive = sourceFilter === source.id;
                  return (
                    <button
                      key={source.id}
                      onClick={() => setSourceFilter(source.id)}
                      className={`px-3 py-1 text-xs rounded-full border transition-all duration-200 cursor-pointer ${
                        isActive 
                          ? 'bg-blue-600 text-white border-blue-700 shadow-sm font-semibold' 
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      {source.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">
            Search Results {filteredResults.length > 0 && `(${filteredResults.length})`}
          </h2>
          {filteredResults.length > 0 && (
            <Button
              variant={bulkFinding ? "secondary" : "primary"}
              className={`text-xs py-1.5 px-3 flex items-center gap-1.5 shadow-sm font-semibold transition-all ${
                bulkFinding ? 'border border-red-200 text-red-600 hover:bg-red-50' : ''
              }`}
              onClick={bulkFinding ? handleStopBulkFind : handleBulkFindEmails}
              disabled={loading}
            >
              {bulkFinding ? (
                <>
                  <span className="w-2.5 h-2.5 bg-red-600 rounded-full animate-ping"></span>
                  Stop Scanning Emails
                </>
              ) : (
                '🕵️ Scan Emails for All Leads'
              )}
            </Button>
          )}
        </div>
        <div className="max-h-[550px] overflow-y-auto overflow-x-hidden">
          <table className="w-full text-left text-sm table-fixed">
            <thead className="text-gray-600 font-semibold border-b border-gray-100 sticky top-0 z-10 bg-gray-50 shadow-[0_1px_2px_rgba(0,0,0,0.05)]">
              <tr>
                <th className="px-6 py-3 w-[22%] text-xs uppercase tracking-wider font-semibold">Company Name</th>
                <th className="px-6 py-3 w-[24%] text-xs uppercase tracking-wider font-semibold">Website / Email</th>
                <th className="px-6 py-3 w-[15%] text-xs uppercase tracking-wider font-semibold">Phone</th>
                <th className="px-6 py-3 w-[24%] text-xs uppercase tracking-wider font-semibold">Address</th>
                <th className="px-6 py-3 w-[15%] text-xs uppercase tracking-wider font-semibold">Rating</th>
                <th className="px-6 py-3 w-[10%] text-xs uppercase tracking-wider font-semibold text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {filteredResults.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                    {loading ? 'Searching Google Maps...' : 'No results found. Try a different search query or toggle the filter.'}
                  </td>
                </tr>
              ) : (
                filteredResults.map((company, index) => {
                  const hasWebsite = company.website_url || company.discovered_website_url;
                  return (
                    <tr key={index} className={`hover:bg-gray-50/70 transition-colors ${!hasWebsite ? 'bg-blue-50/20' : ''}`}>
                      <td className="px-6 py-4 font-medium text-gray-800 align-middle">
                        <div className="font-semibold text-gray-900 truncate" title={company.name}>{company.name}</div>
                        {!hasWebsite && (
                          <div className="text-red-500 text-[10px] font-bold mt-1 flex items-center gap-0.5 select-none">
                            🔥 Hot Lead
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 align-middle">
                        <div className="flex flex-col gap-1 overflow-hidden">
                          {/* Website Link (if exists) */}
                          {hasWebsite ? (
                            <a 
                              href={company.website_url || company.discovered_website_url} 
                              target="_blank" 
                              rel="noopener noreferrer" 
                              className="text-blue-600 hover:underline font-semibold text-xs truncate block"
                              title={company.website_url || company.discovered_website_url}
                            >
                              {(company.website_url || company.discovered_website_url).replace(/^https?:\/\//, '').split('/')[0]}
                            </a>
                          ) : (
                            <span className="text-gray-400 italic text-xs">No Website</span>
                          )}

                          {/* Email Address & Source (if exists) */}
                          {emails[company.name] ? (
                            <div className="flex flex-col mt-0.5">
                              {emails[company.name] === 'Not Found' ? (
                                <span className="text-gray-400 text-[10px] italic">Email Not Found</span>
                              ) : emails[company.name] === 'Error' ? (
                                <span className="text-red-400 text-[10px] italic">Error scanning email</span>
                              ) : (
                                <>
                                  <div className="flex items-center gap-1">
                                    <span className="text-green-600 font-semibold text-xs font-mono break-all truncate block" title={typeof emails[company.name] === 'string' ? emails[company.name] : emails[company.name].email}>
                                      {typeof emails[company.name] === 'string' ? emails[company.name] : emails[company.name].email}
                                    </span>
                                    <span className="text-[9px] bg-green-50 text-green-700 px-1 py-0.2 rounded border border-green-200 font-extrabold flex-shrink-0" title="SMTP Verified Inbox">
                                      ✓ Verified
                                    </span>
                                  </div>
                                  {emails[company.name].source && (
                                    <span className="text-[9px] text-gray-400 font-normal italic -mt-0.5">
                                      via {emails[company.name].source}
                                    </span>
                                  )}
                                </>
                              )}
                            </div>
                          ) : (
                            <Button 
                              variant="secondary" 
                              className="text-[10px] py-0.5 px-2 flex items-center gap-1 w-fit mt-1 border border-gray-200 hover:bg-gray-50 text-gray-600"
                              onClick={() => handleFindEmail(company, index)}
                              disabled={emailLoading[company.name]}
                            >
                              <FiSearch className="text-[9px]" /> {emailLoading[company.name] ? 'Searching...' : 'Find Email 🕵️'}
                            </Button>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-gray-600 align-middle truncate text-xs font-mono" title={company.phone_number || '-'}>
                        {company.phone_number || '-'}
                      </td>
                      <td className="px-6 py-4 text-gray-600 align-middle">
                        <div className="truncate text-xs" title={company.address}>
                          {company.address || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 align-middle">
                        {company.rating ? (
                          <div className="flex items-center gap-1.5 text-xs text-gray-800 font-semibold select-none">
                            <span className="text-amber-400 text-base">★</span>
                            <span>{company.rating}</span>
                            <span className="text-gray-400 font-normal text-[10px]">({company.rating_count})</span>
                          </div>
                        ) : (
                          <span className="text-gray-300 text-xs">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right align-middle">
                        <Button 
                          variant={savedCompanies[company.name] ? "secondary" : "primary"} 
                          className="text-[10px] py-1 px-2.5 font-semibold"
                          onClick={() => handleSaveLead(company, index)}
                          disabled={saveLoading[company.name] || savedCompanies[company.name]}
                        >
                          {saveLoading[company.name] ? 'Saving...' : savedCompanies[company.name] ? 'Saved ✓' : 'Save Lead'}
                        </Button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        {nextPageToken && (
          <div className="p-4 border-t border-gray-100 flex justify-center bg-gray-50/50">
            <Button
              variant="secondary"
              className="text-xs py-2 px-6 shadow-sm font-semibold border border-gray-200"
              onClick={handleLoadMore}
              disabled={loading}
            >
              {loading ? 'Loading More Leads...' : 'Load More Leads ⬇️'}
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
