import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import ChangePlanModal from '../components/ChangePlanModal';
import SimulatePaymentModal from '../components/SimulatePaymentModal';
import { 
  CreditCard, 
  Download, 
  Calendar, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  RefreshCw, 
  Server, 
  Cpu, 
  Layers, 
  Lock, 
  Unlock, 
  Trash2, 
  Plus, 
  ChevronRight,
  ShieldCheck,
  Zap,
  Globe,
  Radio
} from 'lucide-react';

export default function CustomerDashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('billing'); // 'billing' | 'cloud'
  
  // Billing State
  const [subscription, setSubscription] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [simulatingInvoice, setSimulatingInvoice] = useState(null);
  const [actionMessage, setActionMessage] = useState('');

  // Cloud Infrastructure State
  const [cloudData, setCloudData] = useState(null);
  const [isDeployModalOpen, setIsDeployModalOpen] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [serverForm, setServerForm] = useState({
    name: 'web-prod-01',
    region: 'ap-south-1 (Mumbai)',
    vcpus: 2,
    ram_gb: 4,
    has_load_balancer: false,
  });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subRes, invRes, cloudRes] = await Promise.all([
        api.get('/subscriptions/me'),
        api.get('/invoices/me'),
        api.get('/cloud/resources').catch(() => ({ data: null })),
      ]);
      setSubscription(subRes.data);
      setInvoices(invRes.data);
      if (cloudRes && cloudRes.data) {
        setCloudData(cloudRes.data);
      }
    } catch (err) {
      console.error('Failed to load customer dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDownloadPdf = async (invoiceId, invoiceNumber) => {
    try {
      const res = await api.get(`/invoices/${invoiceId}/pdf`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${invoiceNumber}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download invoice PDF.');
    }
  };

  const handleDeployServer = async (e) => {
    e.preventDefault();
    try {
      setDeploying(true);
      const res = await api.post('/cloud/servers', serverForm);
      setActionMessage(res.data.message || 'Server deployed successfully!');
      setIsDeployModalOpen(false);
      setServerForm({
        name: `web-node-${Math.floor(Math.random() * 900 + 100)}`,
        region: 'ap-south-1 (Mumbai)',
        vcpus: 2,
        ram_gb: 4,
        has_load_balancer: false,
      });
      setTimeout(() => setActionMessage(''), 4000);
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Deployment failed');
    } finally {
      setDeploying(false);
    }
  };

  const handleTerminateServer = async (serverId, serverName) => {
    if (!window.confirm(`Are you sure you want to terminate ${serverName}?`)) return;
    try {
      await api.delete(`/cloud/servers/${serverId}`);
      setActionMessage(`Server ${serverName} terminated.`);
      setTimeout(() => setActionMessage(''), 3000);
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to terminate server');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Active</span>
          </span>
        );
      case 'past_due':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Past Due (Dunning Active)</span>
          </span>
        );
      case 'suspended':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">
            <span>Suspended</span>
          </span>
        );
      case 'trialing':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
            <span>Trialing</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  if (loading && !cloudData && !subscription) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header & Tab Navigation */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Customer Portal</h1>
          <p className="text-sm text-slate-500 mt-1">
            Subscription billing management and decoupled cloud infrastructure feature gating console.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center space-x-2 bg-slate-100 p-1.5 rounded-2xl w-fit">
          <button
            onClick={() => setActiveTab('billing')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${
              activeTab === 'billing'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <CreditCard className="w-4 h-4" />
            <span>Billing & Invoices</span>
          </button>

          <button
            onClick={() => setActiveTab('cloud')}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold transition cursor-pointer ${
              activeTab === 'cloud'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Cloud Infrastructure (Decoupled SaaS)</span>
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-2xl text-sm flex items-center space-x-2 animate-fade-in shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 1: BILLING & INVOICES                                            */}
      {/* ==================================================================== */}
      {activeTab === 'billing' && (
        <div className="space-y-8 animate-fade-in">
          {/* Subscription Status Card */}
          {subscription ? (
            <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Current Plan</span>
                    {getStatusBadge(subscription.status)}
                  </div>
                  <div className="flex items-baseline space-x-3">
                    <h2 className="text-3xl font-black text-slate-900 tracking-tight">
                      {subscription.plan?.name || 'Starter'} Plan
                    </h2>
                    <span className="text-xl font-bold text-blue-600">
                      ₹{((subscription.plan?.price_minor || 0) / 100).toLocaleString('en-IN')}/mo
                    </span>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-slate-500">
                    <div className="flex items-center space-x-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        Cycle Period: {new Date(subscription.current_period_start).toLocaleDateString()} –{' '}
                        {new Date(subscription.current_period_end).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={() => setIsPlanModalOpen(true)}
                    className="inline-flex items-center justify-center space-x-2 px-5 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold transition shadow-md shadow-blue-500/20 cursor-pointer"
                  >
                    <span>Change / Upgrade Plan</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Status Notice if Past Due */}
              {subscription.status === 'past_due' && (
                <div className="mt-6 p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start space-x-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div className="text-xs text-amber-900 space-y-1">
                    <p className="font-bold">Dunning Grace Period Active</p>
                    <p>
                      Your latest invoice renewal failed. BillWise is actively executing smart retries (Days 1, 3, 5). 
                      Cloud compute resources are throttled until payment is resolved.
                    </p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-3xl p-8 border border-slate-200 text-center shadow-sm">
              <CreditCard className="w-12 h-12 text-slate-400 mx-auto mb-3" />
              <h3 className="text-lg font-bold text-slate-900">No Active Subscription</h3>
              <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
                Select a subscription tier to activate automatic billing and cloud compute features.
              </p>
            </div>
          )}

          {/* Invoices Table */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-slate-100 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Invoices & Statements</h3>
                <p className="text-xs text-slate-500 mt-0.5">Itemized tax invoices with GST and PDF download</p>
              </div>
              <span className="text-xs font-bold px-3 py-1 bg-slate-100 text-slate-700 rounded-full">
                {invoices.length} Invoices
              </span>
            </div>

            {invoices.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                No invoices generated yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3.5">Invoice #</th>
                      <th className="px-6 py-3.5">Date</th>
                      <th className="px-6 py-3.5">Amount</th>
                      <th className="px-6 py-3.5">Status</th>
                      <th className="px-6 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {invoices.map((inv) => (
                      <tr key={inv.id} className="hover:bg-slate-50/60 transition">
                        <td className="px-6 py-4 font-semibold text-slate-900">
                          {inv.number}
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-500">
                          {new Date(inv.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 font-bold text-slate-900">
                          ₹{(inv.total_minor / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-6 py-4">
                          {inv.status === 'paid' ? (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                              <span>Paid</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                              <Clock className="w-3 h-3 text-amber-600" />
                              <span>Due</span>
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right space-x-2">
                          <button
                            onClick={() => setSimulatingInvoice(inv)}
                            className="inline-flex items-center space-x-1 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-xs font-bold transition border border-blue-200 cursor-pointer"
                            title="Test payment gateway simulator"
                          >
                            <Zap className="w-3.5 h-3.5 text-blue-600" />
                            <span>Simulate Pay</span>
                          </button>

                          <button
                            onClick={() => handleDownloadPdf(inv.id, inv.number)}
                            className="inline-flex items-center space-x-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition border border-slate-300 cursor-pointer"
                            title="Download ReportLab Tax Invoice"
                          >
                            <Download className="w-3.5 h-3.5 text-slate-600" />
                            <span>PDF</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* TAB 2: CLOUD INFRASTRUCTURE CONSOLE (DECOUPLED SAAS FEATURE GATING) */}
      {/* ==================================================================== */}
      {activeTab === 'cloud' && (
        <div className="space-y-8 animate-fade-in">
          {/* Feature Gating Explainer Banner */}
          <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white rounded-3xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
            <div className="relative z-10 space-y-3">
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/20 text-cyan-300 border border-cyan-400/30 text-xs font-bold">
                <Radio className="w-3 h-3 text-cyan-400 animate-pulse" />
                <span>Decoupled Microservice Demonstration</span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
                Simulated Cloud Infrastructure Provider
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                This simulated cloud console acts as a separate application consuming the <strong>BillWise Billing Engine</strong>. 
                Maximum servers, CPU/RAM quotas, and premium features (like <strong>Cloud Load Balancers</strong>) are automatically locked or unlocked based on the user's active billing tier.
              </p>
            </div>
          </div>

          {/* Locked Alert if PAST_DUE or SUSPENDED */}
          {cloudData?.subscription?.is_locked && (
            <div className="p-5 rounded-2xl bg-amber-50 border border-amber-300 flex items-start space-x-3.5 shadow-sm">
              <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-xs text-amber-900 space-y-1">
                <h4 className="font-bold text-sm">Feature Gating Suspension Alert</h4>
                <p>{cloudData.subscription.lock_reason}</p>
                <button
                  onClick={() => setActiveTab('billing')}
                  className="font-bold underline text-amber-800 hover:text-amber-950 mt-1 cursor-pointer block"
                >
                  Go to Billing & Invoices to settle balance →
                </button>
              </div>
            </div>
          )}

          {/* Quota & Feature Gating Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Servers Quota */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex justify-between items-center text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Server Capacity</span>
                <Server className="w-4 h-4 text-blue-600" />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {cloudData?.usage?.server_count || 0} / {cloudData?.limits?.max_servers || 1}
              </div>
              <p className="text-xs text-slate-500">
                Current tier: <strong className="text-blue-600">{cloudData?.limits?.tier_name || 'Free'}</strong>
              </p>
            </div>

            {/* Card 2: Compute Power */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex justify-between items-center text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Allocated Compute</span>
                <Cpu className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {cloudData?.usage?.total_vcpus || 0} <span className="text-xs font-normal text-slate-500">vCPUs</span>
              </div>
              <p className="text-xs text-slate-500">
                RAM: <strong>{cloudData?.usage?.total_ram_gb || 0} GB</strong> total
              </p>
            </div>

            {/* Card 3: Feature Gated Load Balancers */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-2">
              <div className="flex justify-between items-center text-slate-500">
                <span className="text-xs font-bold uppercase tracking-wider">Load Balancers</span>
                {cloudData?.limits?.load_balancer_allowed ? (
                  <Unlock className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Lock className="w-4 h-4 text-amber-600" />
                )}
              </div>
              <div className="text-2xl font-black text-slate-900">
                {cloudData?.limits?.load_balancer_allowed ? (
                  <span className="text-emerald-600 text-lg">UNLOCKED</span>
                ) : (
                  <span className="text-amber-600 text-lg">LOCKED</span>
                )}
              </div>
              <p className="text-xs text-slate-500">
                {cloudData?.limits?.load_balancer_allowed
                  ? 'Active in Pro/Enterprise'
                  : 'Requires Pro Tier or higher'}
              </p>
            </div>

            {/* Card 4: Action Deploy Button */}
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-5 rounded-2xl border border-blue-200 shadow-sm flex flex-col justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-blue-900">Deploy Instance</span>
                <p className="text-xs text-blue-700 mt-1">Spin up cloud compute node</p>
              </div>
              <button
                onClick={() => setIsDeployModalOpen(true)}
                disabled={cloudData?.subscription?.is_locked}
                className="mt-3 inline-flex items-center justify-center space-x-1.5 w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition shadow-sm disabled:opacity-50 cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                <span>Deploy Server</span>
              </button>
            </div>
          </div>

          {/* Deployed Cloud Servers Grid */}
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Active Cloud Instances</h3>
                <p className="text-xs text-slate-500">Simulated virtual machines running in customer VPC</p>
              </div>
              <span className="text-xs font-bold px-3 py-1 bg-slate-100 text-slate-700 rounded-full">
                {cloudData?.servers?.length || 0} Instances
              </span>
            </div>

            {(!cloudData?.servers || cloudData.servers.length === 0) ? (
              <div className="bg-white rounded-3xl p-12 text-center border border-slate-200 shadow-sm space-y-3">
                <Server className="w-12 h-12 text-slate-400 mx-auto" />
                <h4 className="font-bold text-slate-900 text-base">No Servers Deployed</h4>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">
                  Click the <strong>Deploy Server</strong> button to simulate spinning up a cloud compute instance within your subscription quotas.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {cloudData.servers.map((srv) => (
                  <div
                    key={srv.id}
                    className="bg-white rounded-3xl p-6 border border-slate-200 shadow-sm hover:shadow-md transition space-y-4 relative"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <Server className="w-4 h-4 text-blue-600" />
                          <h4 className="font-bold text-slate-900 text-base">{srv.name}</h4>
                        </div>
                        <p className="text-xs text-slate-400 flex items-center space-x-1">
                          <Globe className="w-3 h-3" />
                          <span>{srv.region}</span>
                        </p>
                      </div>

                      {srv.status === 'RUNNING' ? (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                          <span>Running</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                          <AlertTriangle className="w-3 h-3 text-amber-600" />
                          <span>Throttled</span>
                        </span>
                      )}
                    </div>

                    <div className="p-3.5 rounded-2xl bg-slate-50 text-xs font-mono space-y-1.5 border border-slate-100">
                      <div className="flex justify-between text-slate-600">
                        <span>CPU Cores:</span>
                        <span className="font-bold text-slate-900">{srv.vcpus} vCPUs</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>RAM Memory:</span>
                        <span className="font-bold text-slate-900">{srv.ram_gb} GB</span>
                      </div>
                      <div className="flex justify-between text-slate-600 pt-1 border-t border-slate-200">
                        <span>Load Balancer:</span>
                        <span className={srv.has_load_balancer ? 'text-emerald-600 font-bold' : 'text-slate-400'}>
                          {srv.has_load_balancer ? 'ATTACHED' : 'NONE'}
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleTerminateServer(srv.id, srv.name)}
                      className="w-full py-2 px-3 rounded-xl border border-red-200 text-red-600 hover:bg-red-50 text-xs font-bold transition flex items-center justify-center space-x-1.5 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Terminate Instance</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Deploy Server Modal */}
      {isDeployModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 relative space-y-5">
            <div className="flex justify-between items-center pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center">
                  <Server className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base">Provision Cloud Server</h3>
                  <p className="text-xs text-slate-500">Feature gated according to your {cloudData?.limits?.tier_name}</p>
                </div>
              </div>
              <button
                onClick={() => setIsDeployModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-full"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleDeployServer} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Server Name
                </label>
                <input
                  type="text"
                  required
                  value={serverForm.name}
                  onChange={(e) => setServerForm({ ...serverForm, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Cloud Region
                </label>
                <select
                  value={serverForm.region}
                  onChange={(e) => setServerForm({ ...serverForm, region: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ap-south-1 (Mumbai)">ap-south-1 (Mumbai)</option>
                  <option value="ap-southeast-1 (Singapore)">ap-southeast-1 (Singapore)</option>
                  <option value="eu-central-1 (Frankfurt)">eu-central-1 (Frankfurt)</option>
                  <option value="us-east-1 (N. Virginia)">us-east-1 (N. Virginia)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    vCPUs (Max {cloudData?.limits?.max_vcpus_per_server || 2})
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={cloudData?.limits?.max_vcpus_per_server || 2}
                    value={serverForm.vcpus}
                    onChange={(e) => setServerForm({ ...serverForm, vcpus: parseInt(e.target.value) || 1 })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    RAM GB (Max {cloudData?.limits?.max_ram_per_server || 4})
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={cloudData?.limits?.max_ram_per_server || 4}
                    value={serverForm.ram_gb}
                    onChange={(e) => setServerForm({ ...serverForm, ram_gb: parseInt(e.target.value) || 1 })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Feature Gating: Load Balancer Option */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-900">Attach Cloud Load Balancer</span>
                    {cloudData?.limits?.load_balancer_allowed ? (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">PRO FEATURE</span>
                    ) : (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">LOCKED</span>
                    )}
                  </div>
                  <input
                    type="checkbox"
                    disabled={!cloudData?.limits?.load_balancer_allowed}
                    checked={serverForm.has_load_balancer}
                    onChange={(e) => setServerForm({ ...serverForm, has_load_balancer: e.target.checked })}
                    className="w-4 h-4 text-blue-600 rounded disabled:opacity-40 cursor-pointer"
                  />
                </div>
                {!cloudData?.limits?.load_balancer_allowed && (
                  <p className="text-[11px] text-amber-700">
                    🔒 Load Balancers are locked on Starter. Upgrade to <strong>Pro</strong> to enable traffic distribution.
                  </p>
                )}
              </div>

              <div className="pt-2 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsDeployModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={deploying}
                  className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md shadow-blue-500/20 disabled:opacity-50"
                >
                  {deploying ? 'Deploying...' : 'Provision Server'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Plan Change Modal */}
      <ChangePlanModal
        subscription={subscription}
        isOpen={isPlanModalOpen}
        onClose={() => setIsPlanModalOpen(false)}
        onPlanChanged={fetchData}
      />

      {/* Payment Gateway Simulator Modal */}
      <SimulatePaymentModal
        invoice={simulatingInvoice}
        isOpen={!!simulatingInvoice}
        onClose={() => setSimulatingInvoice(null)}
        onPaymentSimulated={fetchData}
      />
    </div>
  );
}
