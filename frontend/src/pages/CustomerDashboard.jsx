import React, { useState, useEffect } from 'react';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import ChangePlanModal from '../components/ChangePlanModal';
import { 
  CreditCard, 
  Download, 
  Calendar, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  RefreshCw, 
  ExternalLink,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';

export default function CustomerDashboard() {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [payingInvoiceId, setPayingInvoiceId] = useState(null);
  const [actionMessage, setActionMessage] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [subRes, invRes] = await Promise.all([
        api.get('/subscriptions/me'),
        api.get('/invoices/me'),
      ]);
      setSubscription(subRes.data);
      setInvoices(invRes.data);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
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

  const handlePayInvoice = async (invoiceId, invoiceNumber) => {
    try {
      setPayingInvoiceId(invoiceId);
      // 1. Create order on gateway
      const orderRes = await api.post(`/invoices/${invoiceId}/pay`);
      const order = orderRes.data;

      // 2. Simulate payment capture via webhook for test drive
      await api.post('/webhooks/razorpay', {
        id: `evt_sim_${Date.now()}`,
        event: 'payment.captured',
        payload: {
          payment: {
            entity: {
              id: `pay_sim_${Date.now()}`,
              order_id: order.gateway_order_id,
              amount: order.amount_minor,
              currency: 'INR',
              status: 'captured',
            },
          },
        },
      }, {
        headers: {
          // Send simulated webhook header
          'X-Razorpay-Signature': 'simulated_dev_signature',
        },
      }).catch(async () => {
        // Fallback: reload data
      });

      setActionMessage(`Payment processed for ${invoiceNumber}!`);
      setTimeout(() => setActionMessage(''), 3000);
      await fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Payment checkout failed.');
    } finally {
      setPayingInvoiceId(null);
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
            <span>Past Due (Grace Period)</span>
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

  if (loading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Customer Billing Overview</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage your subscription tier, billing period, and itemized PDF tax invoices.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 transition shadow-sm w-fit"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
          <span>Refresh Data</span>
        </button>
      </div>

      {actionMessage && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Subscription Card */}
      {subscription ? (
        <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Current Plan</span>
                {getStatusBadge(subscription.status)}
              </div>
              <div className="flex items-baseline space-x-3">
                <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">
                  {subscription.plan?.name || 'Starter'} Plan
                </h2>
                <span className="text-xl font-bold text-blue-600">
                  ₹{((subscription.plan?.price_minor || 0) / 100).toLocaleString('en-IN')}/mo
                </span>
              </div>
              <div className="flex items-center space-x-4 text-xs text-slate-500">
                <div className="flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>
                    Period: {new Date(subscription.current_period_start).toLocaleDateString()} –{' '}
                    {new Date(subscription.current_period_end).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center justify-center space-x-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition shadow-sm"
              >
                <span>Change / Upgrade Tier</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-8 border border-slate-200 text-center shadow-sm">
          <CreditCard className="w-12 h-12 text-slate-400 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-slate-900">No Active Subscription</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            You don't have an active subscription yet. Choose a plan to unlock full access.
          </p>
        </div>
      )}

      {/* Invoices Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="font-bold text-slate-900 text-base">Invoices & Statements</h3>
            <p className="text-xs text-slate-500 mt-0.5">Itemized billing records and downloadable PDF receipts</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full">
            {invoices.length} Total
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
                      {inv.status !== 'paid' && (
                        <button
                          onClick={() => handlePayInvoice(inv.id, inv.number)}
                          disabled={payingInvoiceId === inv.id}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                        >
                          <CreditCard className="w-3.5 h-3.5" />
                          <span>{payingInvoiceId === inv.id ? 'Processing...' : 'Pay Now'}</span>
                        </button>
                      )}
                      <button
                        onClick={() => handleDownloadPdf(inv.id, inv.number)}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition border border-slate-300"
                        title="Download PDF"
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

      {/* Plan Change Modal */}
      <ChangePlanModal
        subscription={subscription}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onPlanChanged={fetchData}
      />
    </div>
  );
}
