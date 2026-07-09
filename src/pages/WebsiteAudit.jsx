import React from 'react';
import Card from '../components/Card';
import Badge from '../components/Badge';
import Button from '../components/Button';
import { FiDownload } from 'react-icons/fi';

const mockAudits = [
  { id: 1, url: 'stark.com', seo: 92, ui: 88, perf: 75, issues: 4, priority: 'Medium' },
  { id: 2, url: 'wayne.com', seo: 65, ui: 70, perf: 60, issues: 12, priority: 'High' },
  { id: 3, url: 'massivedynamic.com', seo: 95, ui: 90, perf: 98, issues: 1, priority: 'Low' },
  { id: 4, url: 'oscorp.com', seo: 45, ui: 50, perf: 30, issues: 28, priority: 'Critical' },
];

const getScoreColor = (score) => {
  if (score >= 90) return 'text-green-600';
  if (score >= 70) return 'text-yellow-600';
  return 'text-red-600';
};

export default function WebsiteAudit() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-800">Website Audits</h2>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-gray-50 text-gray-600 font-medium border-b border-gray-100">
              <tr>
                <th className="px-6 py-4">Website</th>
                <th className="px-6 py-4">SEO Score</th>
                <th className="px-6 py-4">UI Score</th>
                <th className="px-6 py-4">Performance</th>
                <th className="px-6 py-4">Issues Found</th>
                <th className="px-6 py-4">Priority</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {mockAudits.map((audit) => (
                <tr key={audit.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 font-medium text-blue-600 cursor-pointer hover:underline">{audit.url}</td>
                  <td className={`px-6 py-4 font-bold ${getScoreColor(audit.seo)}`}>{audit.seo}/100</td>
                  <td className={`px-6 py-4 font-bold ${getScoreColor(audit.ui)}`}>{audit.ui}/100</td>
                  <td className={`px-6 py-4 font-bold ${getScoreColor(audit.perf)}`}>{audit.perf}/100</td>
                  <td className="px-6 py-4 text-gray-600">{audit.issues}</td>
                  <td className="px-6 py-4">
                    <Badge variant={audit.priority === 'Critical' || audit.priority === 'High' ? 'danger' : audit.priority === 'Medium' ? 'warning' : 'success'}>
                      {audit.priority}
                    </Badge>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Button variant="secondary" className="text-xs py-1 px-3 flex items-center justify-center gap-2 ml-auto">
                      <FiDownload /> Report
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
