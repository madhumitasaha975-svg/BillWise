import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { 
  Shield, 
  TrendingUp, 
  Users, 
  AlertTriangle, 
  FileText, 
  RefreshCw, 
  Play, 
  CheckCircle2, 
  Activity,
  Calendar
} from 'lucide-react';

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggeringJob, setTriggeringJob] = useState('');
  const [jobResult, setJobResult] = useState('');

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [metricRes, subRes, logRes] = await Promise.all([
        api.get('/admin/metrics'),
        api.get('/admin/subscriptions'),
        api.get('/admin/audit-logs'),
      ]);
      setMetrics(metricRes.data);
      setSubscriptions(subRes.data);
      setAuditLogs(logRes.data);
    } catch (err) {
      console.error('Failed to load admin metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const triggerJob = async (jobEndpoint, jobName) => {
    try {
      setTriggeringJob(jobName);
      const res = await api.post(`/admin/${jobEndpoint}`);
      setJobResult(`${jobName} succeeded: ${res.data.message}`);
      setTimeout(() => setJobResult(''), 4000);
      await fetchAdminData();
    } catch (err) {
      alert(`Job execution failed: ${err.message}`);
    } finally {
      setTriggeringJob('');
    }
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-purple-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Shield className="w-6 h-6 text-purple-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Admin Billing Control Plane</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Global metrics, subscription telemetry, background job triggers, and immutable audit logs.
          </p>
        </div>
        <button
          onClick={fetchAdminData}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition shadow-sm w-fit"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {jobResult && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{jobResult}</span>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Revenue</span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900">
            ₹{((metrics?.total_revenue_minor || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-400">Total collected across all paid invoices</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Subscriptions</span>
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900">{metrics?.active_subscriptions || 0}</div>
          <p className="text-xs text-slate-400">Active paying tenant accounts</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Past Due (Dunning)</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-extrabold text-amber-600">{metrics?.past_due_subscriptions || 0}</div>
          <p className="text-xs text-slate-400">Accounts in active retry grace period</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Invoices</span>
            <FileText className="w-4 h-4 text-slate-600" />
          </div>
          <div className="text-2xl font-extrabold text-slate-900">{metrics?.total_invoices || 0}</div>
          <p className="text-xs text-slate-400">Lifetime system invoices</p>
        </div>
      </div>

      {/* Manual Job Triggers Section */}
      <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200/60 rounded-2xl p-6 shadow-sm">
        <h3 className="font-bold text-slate-900 text-base mb-1">Background Scheduled Job Triggers</h3>
        <p className="text-xs text-slate-600 mb-4">
          Test or simulate automated worker jobs directly from the administrative UI.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => triggerJob('trigger-renewals', 'Renewal Scanner')}
            disabled={!!triggeringJob}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-white border border-slate-300 hover:border-slate-400 text-slate-800 rounded-xl text-xs font-bold transition shadow-sm disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 text-blue-600 fill-blue-600" />
            <span>{triggeringJob === 'Renewal Scanner' ? 'Scanning...' : 'Trigger Due Renewals Scanner'}</span>
          </button>

          <button
            onClick={() => triggerJob('trigger-dunning', 'Dunning Engine')}
            disabled={!!triggeringJob}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold transition shadow-sm disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 text-white fill-white" />
            <span>{triggeringJob === 'Dunning Engine' ? 'Retrying...' : 'Trigger Dunning Retry Engine'}</span>
          </button>
        </div>
      </div>

      {/* Subscriptions Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Active Subscriptions</h3>
            <p className="text-xs text-slate-500 mt-0.5">Live subscription contracts across all tenants</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full">
            {subscriptions.length} Subscriptions
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3.5">Subscription ID</th>
                <th className="px-6 py-3.5">Plan</th>
                <th className="px-6 py-3.5">Price</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5">Period End</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {subscriptions.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50/60 transition">
                  <td className="px-6 py-4 font-mono text-xs text-slate-700">
                    {s.id.substring(0, 13)}...
                  </td>
                  <td className="px-6 py-4 font-semibold text-slate-900">{s.plan_name}</td>
                  <td className="px-6 py-4 text-xs font-bold text-slate-700">
                    ₹{(s.plan_price_minor / 100).toLocaleString('en-IN')}/mo
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      s.status === 'active'
                        ? 'bg-emerald-100 text-emerald-800'
                        : s.status === 'past_due'
                        ? 'bg-amber-100 text-amber-800'
                        : s.status === 'suspended'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500">
                    {new Date(s.current_period_end).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-purple-600" />
            <h3 className="font-bold text-slate-900 text-base">Immutable Audit Log Feed</h3>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-purple-50 text-purple-700 rounded-full">
            Real-time Telemetry
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
              <tr>
                <th className="px-6 py-3.5">Timestamp</th>
                <th className="px-6 py-3.5">Action</th>
                <th className="px-6 py-3.5">Entity</th>
                <th className="px-6 py-3.5">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-xs">
              {auditLogs.slice(0, 10).map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/60 transition">
                  <td className="px-6 py-3 text-slate-400">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-3 font-semibold text-purple-700">
                    {log.action}
                  </td>
                  <td className="px-6 py-3 text-slate-600">
                    {log.entity_type}:{log.entity_id.substring(0, 8)}
                  </td>
                  <td className="px-6 py-3 text-slate-500 max-w-xs truncate">
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
