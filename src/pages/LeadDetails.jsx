import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import Card from '../components/Card';
import Button from '../components/Button';
import Badge from '../components/Badge';
import { FiMail, FiPhone, FiGlobe, FiMapPin, FiStar, FiActivity, FiArrowLeft, FiPlusCircle } from 'react-icons/fi';
import companyService from '../services/companyService';

export default function LeadDetails() {
  const [searchParams] = useSearchParams();
  const id = searchParams.get('id');

  const [company, setCompany] = useState(null);
  const [audit, setAudit] = useState(null);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadDetails = async () => {
      try {
        setLoading(true);
        const coData = await companyService.getCompanyById(id);
        setCompany(coData);

        try {
          const audits = await companyService.getAuditsForCompany(id);
          if (audits && audits.length > 0) {
            setAudit(audits[audits.length - 1]); // Load latest audit
          }
        } catch (e) {
          console.warn("No audits found for company", e);
        }

        try {
          const scData = await companyService.getLeadScoreForCompany(id);
          setScore(scData);
        } catch (e) {
          console.warn("No lead score found for company", e);
        }
      } catch (err) {
        console.error(err);
        setError('Failed to fetch lead details. Verify the company exists.');
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      loadDetails();
    }
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !company) {
    return (
      <div className="space-y-4">
        <Link to="/companies" className="text-blue-600 flex items-center gap-1 hover:underline">
          <FiArrowLeft /> Back to Companies
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm font-medium">
          {error || 'Company not found.'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-inter">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <Link to="/companies" className="text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1 mb-2">
            <FiArrowLeft /> Back to Companies
          </Link>
          <h2 className="text-2xl font-bold text-gray-800 tracking-tight">{company.name}</h2>
          <p className="text-gray-500 text-sm">{company.industry || 'Local Business'} • Lead Status: <span className="font-semibold text-blue-600">{company.status}</span></p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" className="flex items-center gap-2"><FiStar /> Add to Priority</Button>
          <Link to="/campaign">
            <Button variant="primary" className="flex items-center gap-2"><FiMail /> Send Email</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Website Audit Results</h3>
            {audit ? (
              <>
                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="p-4 bg-gray-50 rounded-xl text-center border border-gray-100">
                    <div className="text-2xl font-bold text-blue-600">{audit.seo_score}/100</div>
                    <div className="text-xs text-gray-500 mt-1 uppercase font-semibold">SEO Score</div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-xl text-center border border-gray-100">
                    <div className="text-2xl font-bold text-blue-600">{audit.ui_score}/100</div>
                    <div className="text-xs text-gray-500 mt-1 uppercase font-semibold">UI Score</div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-xl text-center border border-gray-100">
                    <div className="text-2xl font-bold text-blue-600">{audit.performance_score}/100</div>
                    <div className="text-xs text-gray-500 mt-1 uppercase font-semibold">Performance</div>
                  </div>
                </div>
                <div>
                  <h4 className="font-semibold text-gray-700 mb-2">Suggested Services to Pitch:</h4>
                  <ul className="list-disc list-inside text-gray-600 space-y-1 text-sm">
                    {audit.suggestions && audit.suggestions.length > 0 ? (
                      audit.suggestions.map((suggestion, idx) => (
                        <li key={idx}>{suggestion}</li>
                      ))
                    ) : (
                      <li>No issues detected. Ready to pitch standard SEO retainers.</li>
                    )}
                  </ul>
                </div>
              </>
            ) : (
              <div className="text-center py-8 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                <p className="text-gray-500 text-sm mb-4">No audit data available for this business.</p>
                {company.website ? (
                  <Link to={`/audit?url=${encodeURIComponent(company.website)}`}>
                    <Button variant="secondary" className="text-xs flex items-center gap-1 mx-auto">
                      <FiPlusCircle /> Run Website Audit
                    </Button>
                  </Link>
                ) : (
                  <p className="text-xs text-gray-400">Add a website URL to this company to run an audit.</p>
                )}
              </div>
            )}
          </Card>

          <Card>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Email History</h3>
            <div className="space-y-4">
              {company.status === 'Emailed' ? (
                <div className="border-l-2 border-primary pl-4 pb-4">
                  <p className="text-xs text-gray-500 mb-1">Recently sent</p>
                  <p className="font-semibold text-gray-800">Initial Cold Pitch Email</p>
                  <p className="text-xs text-gray-600 mt-0.5">Status: <Badge variant="success">Sent</Badge></p>
                </div>
              ) : (
                <p className="text-sm text-gray-500 italic">No emails sent yet to this lead.</p>
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Lead Score</h3>
            <div className="flex items-center justify-center py-6">
              <div className="relative w-32 h-32 flex items-center justify-center rounded-full border-8 border-primary/20">
                <div className="text-3xl font-extrabold text-primary">{score ? score.score : 'N/A'}</div>
              </div>
            </div>
            <p className="text-center text-xs text-gray-500 font-semibold uppercase tracking-wider mt-4">
              {score ? (score.score >= 80 ? 'High Quality Lead' : score.score >= 50 ? 'Medium Quality Lead' : 'Low Quality Lead') : 'No Score Computed'}
            </p>
          </Card>

          <Card>
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Contact Info</h3>
            <div className="space-y-4 text-sm text-gray-600">
              <div className="flex items-start gap-3">
                <FiGlobe className="mt-1 flex-shrink-0 text-gray-400" />
                {company.website ? (
                  <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-medium break-all">
                    {company.website.replace(/^https?:\/\//, '')}
                  </a>
                ) : (
                  <span className="italic text-gray-400">No Website</span>
                )}
              </div>
              <div className="flex items-start gap-3">
                <FiMail className="mt-1 flex-shrink-0 text-gray-400" />
                {company.email ? (
                  <span className="font-medium text-gray-800 break-all">{company.email}</span>
                ) : (
                  <span className="italic text-gray-400">No Email Address</span>
                )}
              </div>
              <div className="flex items-start gap-3">
                <FiPhone className="mt-1 flex-shrink-0 text-gray-400" />
                <span>{company.phone || <span className="italic text-gray-400">No Phone Number</span>}</span>
              </div>
              <div className="flex items-start gap-3">
                <FiMapPin className="mt-1 flex-shrink-0 text-gray-400" />
                <span className="text-gray-700">{company.location || 'No Location Available'}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
