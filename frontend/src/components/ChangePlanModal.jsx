import React, { useState } from 'react';
import api from '../api/client';
import { X, Check, ArrowUpRight, AlertCircle, RefreshCw } from 'lucide-react';

const PLANS = [
  { code: 'free', name: 'Free', price: '₹0', priceMinor: 0, description: 'Basic trial access' },
  { code: 'starter', name: 'Starter', price: '₹499/mo', priceMinor: 49900, description: 'For freelancers & hobbyists' },
  { code: 'pro', name: 'Pro', price: '₹1,499/mo', priceMinor: 149900, description: 'For growing SaaS teams' },
  { code: 'business', name: 'Business', price: '₹4,999/mo', priceMinor: 499900, description: 'For scaling companies' },
  { code: 'enterprise', name: 'Enterprise', price: '₹14,999/mo', priceMinor: 1499900, description: 'Dedicated scale & SLA' },
];

export default function ChangePlanModal({ subscription, isOpen, onClose, onPlanChanged }) {
  const [selectedPlan, setSelectedPlan] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  if (!isOpen || !subscription) return null;

  const currentPlanCode = subscription.plan?.code || 'starter';

  const handleUpgrade = async () => {
    if (!selectedPlan || selectedPlan === currentPlanCode) return;
    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      const res = await api.post(`/subscriptions/${subscription.id}/change-plan`, {
        new_plan_code: selectedPlan,
      });
      const inv = res.data.invoice;
      const invText = inv ? `Generated prorated invoice ${inv.number} for ₹${(inv.total_minor / 100).toFixed(2)}` : 'Plan updated successfully.';
      setSuccessMsg(`Switched to ${selectedPlan.toUpperCase()}! ${invText}`);
      setTimeout(() => {
        onPlanChanged();
        onClose();
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to switch plans.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-200">
        <div className="flex justify-between items-center pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-xl font-bold text-slate-900">Change Subscription Plan</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Mid-cycle changes calculate fair second-level prorated credit/charge
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="my-4 bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-sm flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="my-4 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-2.5 rounded-lg text-sm flex items-center space-x-2">
            <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Plan Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-5">
          {PLANS.map((plan) => {
            const isCurrent = plan.code === currentPlanCode;
            const isSelected = plan.code === selectedPlan;

            return (
              <div
                key={plan.code}
                onClick={() => !isCurrent && setSelectedPlan(plan.code)}
                className={`p-4 rounded-xl border-2 transition cursor-pointer ${
                  isCurrent
                    ? 'border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed'
                    : isSelected
                    ? 'border-blue-600 bg-blue-50/40 shadow-sm'
                    : 'border-slate-200 hover:border-slate-300 bg-white'
                }`}
              >
                <div className="flex justify-between items-start">
                  <h4 className="font-bold text-slate-900 text-base">{plan.name}</h4>
                  {isCurrent && (
                    <span className="text-[10px] uppercase font-bold bg-slate-200 text-slate-700 px-2 py-0.5 rounded">
                      Current
                    </span>
                  )}
                </div>
                <div className="mt-2 text-xl font-extrabold text-blue-600">{plan.price}</div>
                <p className="mt-1 text-xs text-slate-500">{plan.description}</p>
              </div>
            );
          })}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 pt-3 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleUpgrade}
            disabled={!selectedPlan || selectedPlan === currentPlanCode || loading}
            className="flex items-center space-x-2 px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition disabled:opacity-50 shadow-sm"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Prorating...</span>
              </>
            ) : (
              <>
                <span>Confirm & Switch Tier</span>
                <ArrowUpRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
