import React from 'react';
import Card from '../components/Card';
import Badge from '../components/Badge';
import { FiClock, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';

const mockLogs = [
  { id: 1, type: 'Audit', status: 'Success', message: 'Completed website audit for massivedynamic.com', time: '10 mins ago', user: 'System' },
  { id: 2, type: 'Email', status: 'Error', message: 'SMTP connection timeout while sending to oscorp.com', time: '1 hour ago', user: 'System' },
  { id: 3, type: 'User', status: 'Success', message: 'User vivang@company.com logged in', time: '2 hours ago', user: 'Vivang Mishra' },
  { id: 4, type: 'Audit', status: 'Success', message: 'Completed website audit for stark.com', time: '3 hours ago', user: 'System' },
];

export default function Logs() {
  return (
    <div className="space-y-6">
      {/* Top Dark Banner Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 rounded-2xl text-white shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="p-2 bg-blue-500/20 text-blue-400 rounded-xl text-xl">📋</span>
            <h1 className="text-2xl font-black tracking-tight">System Audit Logs</h1>
          </div>
          <p className="text-sm text-slate-300">
            View system activity, authentication events, and audit logs.
          </p>
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-600 font-medium border-b border-gray-100">
              <tr>
                <th className="px-6 py-4">Timestamp</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4">Message</th>
                <th className="px-6 py-4">User</th>
                <th className="px-6 py-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {mockLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-gray-500 flex items-center gap-2">
                    <FiClock className="text-gray-400" /> {log.time}
                  </td>
                  <td className="px-6 py-4 text-gray-600 font-medium">{log.type}</td>
                  <td className="px-6 py-4 text-gray-800">{log.message}</td>
                  <td className="px-6 py-4 text-gray-600">{log.user}</td>
                  <td className="px-6 py-4 text-right">
                    <Badge variant={log.status === 'Success' ? 'success' : 'danger'} className="gap-1">
                      {log.status === 'Success' ? <FiCheckCircle /> : <FiAlertCircle />} {log.status}
                    </Badge>
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
