import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, User, LogOut, CreditCard } from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="bg-blue-600 text-white p-2 rounded-lg shadow-sm">
              <CreditCard className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xl font-bold text-slate-900 tracking-tight">BillWise</span>
              <span className="ml-2 px-2 py-0.5 text-xs font-semibold bg-blue-50 text-blue-700 rounded-full border border-blue-200">
                SaaS Billing
              </span>
            </div>
          </div>

          {/* User profile & actions */}
          <div className="flex items-center space-x-4">
            {user && (
              <>
                <div className="flex items-center space-x-2 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200">
                  {user.role === 'admin' ? (
                    <Shield className="w-4 h-4 text-purple-600" />
                  ) : (
                    <User className="w-4 h-4 text-slate-600" />
                  )}
                  <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">
                    {user.role}
                  </span>
                </div>

                <button
                  onClick={logout}
                  className="flex items-center space-x-1.5 text-slate-600 hover:text-red-600 px-3 py-1.5 rounded-md text-sm font-medium transition-colors hover:bg-red-50"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Logout</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
