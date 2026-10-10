import React, { useState, useEffect } from 'react';
import api from '../api/client';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
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
  Calendar,
  PieChart,
  BarChart3,
  Clock,
  ArrowUpRight
} from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [triggeringJob, setTriggeringJob] = useState('');
  const [jobResult, setJobResult] = useState('');

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [metricRes, analyticsRes, subRes, logRes] = await Promise.all([
        api.get('/admin/metrics'),
        api.get('/admin/analytics').catch(() => ({ data: null })),
        api.get('/admin/subscriptions'),
        api.get('/admin/audit-logs'),
      ]);
      setMetrics(metricRes.data);
      if (analyticsRes && analyticsRes.data) {
        setAnalytics(analyticsRes.data);
      }
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
      setJobResult(`${jobName} completed: ${res.data.message}`);
      setTimeout(() => setJobResult(''), 4000);
      await fetchAdminData();
    } catch (err) {
      alert(`Job execution failed: ${err.message}`);
    } finally {
      setTriggeringJob('');
    }
  };

  // Prepare Line Chart Data for MRR Growth
  const lineChartData = {
    labels: analytics?.revenue_trend?.map((t) => t.month) || ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
    datasets: [
      {
        label: 'MRR (₹)',
        data: analytics?.revenue_trend?.map((t) => t.mrr_minor / 100) || [674, 869, 1079, 1274, 1409, 1499],
        borderColor: '#4F46E5',
        backgroundColor: 'rgba(79, 70, 229, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      {
        label: 'Invoiced with Tax (₹)',
        data: analytics?.revenue_trend?.map((t) => t.invoiced_minor / 100) || [795, 1025, 1273, 1503, 1662, 1768],
        borderColor: '#06B6D4',
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        tension: 0.4,
        pointRadius: 3,
      },
    ],
  };

  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { font: { size: 11, weight: '600' } },
      },
      tooltip: {
        callbacks: {
          label: (context) => ` ₹${context.parsed.y.toLocaleString('en-IN')}`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value) => `₹${value}`,
          font: { size: 10 },
        },
        grid: { color: 'rgba(0,0,0,0.04)' },
      },
      x: {
        grid: { display: false },
        ticks: { font: { size: 11 } },
      },
    },
  };

  // Prepare Doughnut Chart Data for Plan Distribution
  const doughnutData = {
    labels: analytics?.plan_distribution?.map((p) => p.plan_name) || ['Starter', 'Pro', 'Business'],
    datasets: [
      {
        data: analytics?.plan_distribution?.map((p) => p.count) || [4, 8, 2],
        backgroundColor: [
          '#3B82F6', // Blue (Starter)
          '#6366F1', // Indigo (Pro)
          '#8B5CF6', // Violet (Business)
          '#EC4899', // Pink (Enterprise)
          '#94A3B8', // Slate (Free)
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: { font: { size: 11, weight: '600' } },
      },
    },
    cutout: '65%',
  };

  if (loading && !metrics) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-purple-600 flex items-center justify-center text-white shadow-md shadow-purple-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight">Admin Billing Control Plane</h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Global MRR analytics, automated job triggers, subscriber ledgers, and interactive billing calendar.
          </p>
        </div>
        <button
          onClick={fetchAdminData}
          className="inline-flex items-center space-x-1.5 px-3.5 py-2 bg-white border border-slate-300 rounded-xl text-xs font-bold text-slate-700 hover:bg-slate-50 transition shadow-sm w-fit cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {jobResult && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-2xl text-sm flex items-center space-x-2 shadow-sm animate-fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{jobResult}</span>
        </div>
      )}

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Collected Revenue</span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">
            ₹{((metrics?.total_revenue_minor || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-400">Total settled across paid invoices</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Current MRR</span>
            <BarChart3 className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-2xl font-black text-indigo-600">
            ₹{((analytics?.mrr_minor || 0) / 100).toLocaleString('en-IN')}
          </div>
          <p className="text-xs text-slate-400">
            ARR Run-rate: ₹{((analytics?.arr_minor || 0) / 100).toLocaleString('en-IN')}
          </p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Active Tenants</span>
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-slate-900">{metrics?.active_subscriptions || 0}</div>
          <p className="text-xs text-slate-400">Paying customers in ACTIVE status</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex justify-between items-center text-slate-500">
            <span className="text-xs font-bold uppercase tracking-wider">Dunning (Past Due)</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-black text-amber-600">{metrics?.past_due_subscriptions || 0}</div>
          <p className="text-xs text-slate-400">In automated retry recovery flow</p>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* CHART.JS FINANCIAL ANALYTICS SECTION                                 */}
      {/* ==================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* MRR Trend Line Chart */}
        <div className="lg:col-span-8 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="font-bold text-slate-900 text-base">Monthly Recurring Revenue (MRR) Growth</h3>
              <p className="text-xs text-slate-500 mt-0.5">Chart.js real-time financial telemetry</p>
            </div>
            <span className="inline-flex items-center space-x-1 text-xs font-bold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              <ArrowUpRight className="w-3.5 h-3.5" />
              <span>+18.4% MoM</span>
            </span>
          </div>
          <div className="h-64">
            <Line data={lineChartData} options={lineChartOptions} />
          </div>
        </div>

        {/* Plan Distribution Doughnut Chart */}
        <div className="lg:col-span-4 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-4">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Plan Tier Distribution</h3>
            <p className="text-xs text-slate-500 mt-0.5">Active subscriptions by product tier</p>
          </div>
          <div className="h-64 flex items-center justify-center">
            <Doughnut data={doughnutData} options={doughnutOptions} />
          </div>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* GLOBAL BILLING SCHEDULE & RENEWAL CALENDAR                          */}
      {/* ==================================================================== */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center">
          <div className="flex items-center space-x-2.5">
            <Calendar className="w-5 h-5 text-indigo-600" />
            <div>
              <h3 className="font-bold text-slate-900 text-base">Global Billing Calendar & Upcoming Renewals</h3>
              <p className="text-xs text-slate-500 mt-0.5">Next 30 days renewal timeline across all tenants</p>
            </div>
          </div>
          <span className="text-xs font-bold px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full">
            {analytics?.billing_calendar?.length || 0} Scheduled Renewals
          </span>
        </div>

        {(!analytics?.billing_calendar || analytics.billing_calendar.length === 0) ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No upcoming renewals scheduled in the next 30 days.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-3.5">Renewal Date</th>
                  <th className="px-6 py-3.5">Tenant Account</th>
                  <th className="px-6 py-3.5">Plan Tier</th>
                  <th className="px-6 py-3.5">Renewal Fee</th>
                  <th className="px-6 py-3.5">Current Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {analytics.billing_calendar.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/60 transition">
                    <td className="px-6 py-3.5 font-bold text-slate-900 flex items-center space-x-2">
                      <Clock className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{new Date(item.renewal_date).toLocaleDateString()}</span>
                    </td>
                    <td className="px-6 py-3.5">
                      <span className="font-semibold text-slate-900 block">{item.customer_name}</span>
                      <span className="text-slate-400">{item.customer_email}</span>
                    </td>
                    <td className="px-6 py-3.5 font-bold text-indigo-600">{item.plan_name}</td>
                    <td className="px-6 py-3.5 font-bold text-slate-900">
                      ₹{(item.renewal_amount_minor / 100).toLocaleString('en-IN')}
                    </td>
                    <td className="px-6 py-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                          item.status === 'active'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {item.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Manual Job Triggers Section */}
      <div className="bg-gradient-to-r from-purple-50 via-indigo-50 to-blue-50 border border-purple-200/60 rounded-3xl p-6 sm:p-7 shadow-sm">
        <h3 className="font-bold text-slate-900 text-base mb-1">Automated Background Worker Triggers</h3>
        <p className="text-xs text-slate-600 mb-4">
          Test or simulate Celery background workers and dunning recovery pipelines directly from the UI.
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => triggerJob('trigger-renewals', 'Renewal Scanner')}
            disabled={!!triggeringJob}
            className="inline-flex items-center space-x-2 px-4 py-2.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-800 rounded-xl text-xs font-bold transition shadow-sm disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 text-blue-600 fill-blue-600" />
            <span>{triggeringJob === 'Renewal Scanner' ? 'Scanning...' : 'Trigger Due Renewals Scanner'}</span>
          </button>

          <button
            onClick={() => triggerJob('trigger-dunning', 'Dunning Engine')}
            disabled={!!triggeringJob}
            className="inline-flex items-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-md shadow-purple-500/20 disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5 text-white fill-white" />
            <span>{triggeringJob === 'Dunning Engine' ? 'Retrying...' : 'Trigger Dunning Retry Engine'}</span>
          </button>
        </div>
      </div>

      {/* Subscriptions Table */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Subscriber Ledgers</h3>
            <p className="text-xs text-slate-500 mt-0.5">Live contracts across all tenants</p>
          </div>
          <span className="text-xs font-bold px-3 py-1 bg-slate-100 text-slate-700 rounded-full">
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
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-purple-600" />
            <h3 className="font-bold text-slate-900 text-base">Immutable Audit Log Feed</h3>
          </div>
          <span className="text-xs font-bold px-3 py-1 bg-purple-50 text-purple-700 rounded-full">
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
