import React, { useState } from 'react';
import api from '../api/client';
import { CreditCard, CheckCircle2, AlertTriangle, X, ShieldAlert, Zap } from 'lucide-react';

export default function SimulatePaymentModal({ invoice, isOpen, onClose, onPaymentSimulated }) {
  const [loading, setLoading] = useState(false);
  const [resultMsg, setResultMsg] = useState(null);

  if (!isOpen || !invoice) return null;

  const handleSimulate = async (outcome) => {
    try {
      setLoading(true);
      setResultMsg(null);
      const res = await api.post(`/invoices/${invoice.id}/simulate-payment`, {
        outcome: outcome,
      });
      setResultMsg({
        type: outcome === 'succeeded' ? 'success' : 'error',
        text: res.data.message,
      });
      setTimeout(() => {
        onPaymentSimulated();
        onClose();
        setResultMsg(null);
      }, 1600);
    } catch (err) {
      setResultMsg({
        type: 'error',
        text: err.response?.data?.detail || 'Simulation error',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 relative space-y-5">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1.5 rounded-full hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center">
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Payment Gateway Simulator</h3>
            <p className="text-xs text-slate-500">Test real-time webhook transitions & state reaction</p>
          </div>
        </div>

        {/* Invoice Summary Box */}
        <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
          <div className="flex justify-between text-xs text-slate-500">
            <span>Invoice Number</span>
            <span className="font-mono font-bold text-slate-800">{invoice.number}</span>
          </div>
          <div className="flex justify-between items-baseline pt-1 border-t border-slate-200">
            <span className="text-xs font-semibold text-slate-600">Total Due (incl. 18% GST)</span>
            <span className="text-xl font-extrabold text-blue-600">
              ₹{(invoice.total_minor / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>

        {resultMsg && (
          <div
            className={`p-3 rounded-xl text-xs font-medium flex items-center space-x-2 ${
              resultMsg.type === 'success'
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-amber-50 text-amber-800 border border-amber-200'
            }`}
          >
            {resultMsg.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            )}
            <span>{resultMsg.text}</span>
          </div>
        )}

        {/* Simulation Action Buttons */}
        <div className="space-y-3 pt-2">
          <button
            onClick={() => handleSimulate('succeeded')}
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 shadow-md shadow-emerald-600/20 flex items-center justify-center space-x-2 transition disabled:opacity-50 cursor-pointer"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{loading ? 'Processing...' : 'Simulate Payment Success (200 OK)'}</span>
          </button>

          <button
            onClick={() => handleSimulate('failed')}
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl text-xs font-bold text-amber-900 bg-amber-50 hover:bg-amber-100 border border-amber-300 shadow-sm flex items-center justify-center space-x-2 transition disabled:opacity-50 cursor-pointer"
          >
            <ShieldAlert className="w-4 h-4 text-amber-600" />
            <span>{loading ? 'Processing...' : 'Simulate Payment Failure (Trigger Dunning)'}</span>
          </button>
        </div>

        <p className="text-[11px] text-center text-slate-400">
          Success marks invoice <span className="font-semibold text-emerald-600">PAID</span>. Failure shifts subscription to <span className="font-semibold text-amber-600">PAST_DUE</span> and throttles cloud compute quota.
        </p>
      </div>
    </div>
  );
}
