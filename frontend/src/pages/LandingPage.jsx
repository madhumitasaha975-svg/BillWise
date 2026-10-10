import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Sparkles, 
  ArrowRight, 
  CreditCard, 
  ShieldCheck, 
  RefreshCw, 
  FileText, 
  Zap, 
  CheckCircle2, 
  AlertTriangle, 
  Cpu, 
  TrendingUp, 
  Lock, 
  Calendar, 
  Download, 
  Check, 
  ChevronRight,
  Terminal,
  Activity,
  Layers,
  Globe
} from 'lucide-react';

const PLANS = [
  { code: 'starter', name: 'Starter', price: '₹499', period: '/month', desc: 'For early-stage SaaS startups', featured: false, features: ['Up to 500 subscriptions', 'Automated proration engine', 'Standard email webhooks', 'PDF invoice generation'] },
  { code: 'pro', name: 'Pro', price: '₹1,499', period: '/month', desc: 'For fast-growing SaaS products', featured: true, features: ['Up to 5,000 subscriptions', 'Smart Dunning retry engine', 'HMAC-SHA256 Webhooks', '18% GST Compliant PDFs', 'Customer Billing Portal'] },
  { code: 'business', name: 'Business', price: '₹4,999', period: '/month', desc: 'For established software companies', featured: false, features: ['Up to 50,000 subscriptions', 'Custom retry backoff intervals', 'Dedicated audit log retention', 'Role-based access control (RBAC)', 'Priority 24/7 SLA support'] },
];

export default function LandingPage() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  // Subtle interactive 3D pointer tilt
  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: x * 12, y: -y * 12 });
  };

  const handleMouseLeave = () => {
    setTilt({ x: 0, y: 0 });
  };

  return (
    <div className="min-h-screen bg-[#FAFBFC] text-slate-900 font-sans selection:bg-blue-600 selection:text-white relative overflow-x-hidden">
      
      {/* ========================================================= */}
      {/* 1. FLOATING TRANSLUCENT NAVIGATION                        */}
      {/* ========================================================= */}
      <header className="fixed top-5 inset-x-0 z-50 flex justify-center px-4 sm:px-6 pointer-events-none">
        <nav className="pointer-events-auto max-w-5xl w-full bg-white/80 backdrop-blur-xl border border-white/80 shadow-[0_10px_35px_rgba(0,0,0,0.06)] rounded-full px-5 sm:px-7 py-3 flex items-center justify-between transition-all duration-300">
          
          {/* Brand Wordmark */}
          <div className="flex items-center space-x-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-md shadow-blue-500/25">
              <CreditCard className="w-5 h-5" />
            </div>
            <div className="flex items-baseline space-x-1">
              <span className="text-lg font-black tracking-tight text-slate-900">BILLWISE</span>
              <span className="text-[10px] font-extrabold uppercase bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">SaaS</span>
            </div>
          </div>

          {/* Nav Links */}
          <div className="hidden md:flex items-center space-x-7 text-xs font-semibold text-slate-600">
            <a href="#features" className="hover:text-blue-600 transition-colors">Features</a>
            <a href="#proration" className="hover:text-blue-600 transition-colors">Proration</a>
            <a href="#dunning" className="hover:text-blue-600 transition-colors">Dunning Engine</a>
            <a href="#pricing" className="hover:text-blue-600 transition-colors">Pricing</a>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <Link
              to="/login"
              className="text-xs font-semibold text-slate-700 hover:text-blue-600 px-3 py-1.5 transition-colors"
            >
              Sign In
            </Link>
            <Link
              to="/login"
              className="relative group overflow-hidden rounded-full px-4 sm:px-5 py-2 text-xs font-bold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 shadow-md shadow-blue-500/25 hover:shadow-lg hover:shadow-blue-500/40 transition-all active:scale-95"
            >
              <span className="relative z-10 flex items-center space-x-1.5">
                <span>Launch Demo</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </span>
            </Link>
          </div>
        </nav>
      </header>

      {/* ========================================================= */}
      {/* 2. HIGH-IMPACT HERO SECTION WITH 3D INTERFACE MOCKUP      */}
      {/* ========================================================= */}
      <section className="relative pt-36 sm:pt-44 pb-20 sm:pb-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto bg-tech-grid">
        
        {/* Ambient Radial Lighting */}
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-blue-500/15 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />
        <div className="absolute top-40 right-1/4 w-[30rem] h-[30rem] bg-indigo-500/15 rounded-full blur-3xl pointer-events-none animate-pulse-glow" />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          
          {/* LEFT COLUMN: Value Proposition */}
          <div className="lg:col-span-6 space-y-7 text-left z-10">
            
            {/* Announcement Pill */}
            <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-blue-50/90 border border-blue-200/60 shadow-sm">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600"></span>
              </span>
              <span className="text-xs font-semibold text-blue-900 tracking-wide">
                Precision SaaS Recurring Billing & Proration Engine
              </span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-slate-900 leading-[1.08]">
              Automate Billing.{' '}
              <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 bg-clip-text text-transparent">
                Recover Churn.
              </span>{' '}
              Scale Revenue.
            </h1>

            {/* Description */}
            <p className="text-base sm:text-lg text-slate-600 max-w-xl leading-relaxed">
              The production-grade subscription billing platform with second-level proration math, automated dunning recovery, and compliant GST PDF invoicing. Zero floating-point drift.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                to="/login"
                className="inline-flex items-center space-x-2 px-7 py-3.5 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 shadow-xl shadow-blue-600/30 hover:shadow-blue-600/40 hover:-translate-y-0.5 transition-all"
              >
                <span>Launch Live Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <a
                href="#pricing"
                className="inline-flex items-center space-x-2 px-6 py-3.5 rounded-xl font-bold text-sm text-slate-700 bg-white border border-slate-200 shadow-sm hover:border-slate-300 hover:bg-slate-50 transition-all"
              >
                <span>Explore Plans</span>
              </a>
            </div>

            {/* Proof Badges */}
            <div className="flex items-center space-x-4 pt-4 text-xs text-slate-600">
              <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Zero Float Rounding (Integer Paise)</span>
              </div>
              <div className="flex items-center space-x-1.5 font-semibold text-slate-800">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                <span>HMAC-SHA256 Webhooks</span>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: 3D Product Interface Mockup + Floating Depth Cards */}
          <div 
            className="lg:col-span-6 relative perspective-1200 flex justify-center items-center"
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            
            {/* Ambient Background Glow Orb */}
            <div className="absolute w-[28rem] h-[28rem] bg-gradient-to-tr from-blue-500/20 via-indigo-500/20 to-purple-500/20 rounded-full blur-3xl pointer-events-none" />

            {/* 3D TILTED MAIN MOCKUP (BillWise Billing Control Plane) */}
            <div 
              style={{
                transform: `rotateY(${tilt.x - 8}deg) rotateX(${tilt.y + 6}deg) rotateZ(-1deg)`,
                transition: 'transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1)',
              }}
              className="relative w-full max-w-lg bg-white/95 backdrop-blur-2xl border border-white/90 rounded-3xl p-6 shadow-[0_25px_60px_-15px_rgba(37,99,235,0.25),0_15px_30px_rgba(0,0,0,0.06)] transition-all preserve-3d"
            >
              
              {/* Header inside Mockup */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-[11px] font-extrabold uppercase tracking-widest text-blue-600">
                    Live Subscription Control Plane
                  </span>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Status: ACTIVE
                </span>
              </div>

              {/* Plan Card Inside Mockup */}
              <div className="pt-4 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-xl font-black text-slate-900 tracking-tight">
                      Pro Plan Subscription
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">Customer: developer@billwise.com</p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200/70 rounded-xl p-2.5 text-right shadow-sm">
                    <span className="text-[10px] font-bold uppercase text-blue-800 block">Monthly Rate</span>
                    <span className="text-base font-black text-blue-600">₹1,499.00</span>
                  </div>
                </div>

                {/* Mid-Cycle Proration Calculation Preview */}
                <div className="p-3.5 rounded-2xl bg-slate-900 text-white shadow-inner space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300">Mid-Cycle Plan Upgrade Preview</span>
                    <span className="font-mono text-cyan-400 text-[10px] bg-cyan-950 px-2 py-0.5 rounded">PRORATED</span>
                  </div>
                  <div className="space-y-1 text-[11px] font-mono border-t border-slate-800 pt-2">
                    <div className="flex justify-between text-emerald-400">
                      <span>+ Remaining Pro Plan Charge:</span>
                      <span>+₹1,000.00</span>
                    </div>
                    <div className="flex justify-between text-amber-400">
                      <span>- Unused Starter Plan Credit:</span>
                      <span>-₹333.33</span>
                    </div>
                    <div className="flex justify-between text-white font-bold pt-1 border-t border-slate-700">
                      <span>Net Immediate Due:</span>
                      <span className="text-cyan-300">₹666.67</span>
                    </div>
                  </div>
                </div>

                {/* Progress bar of current cycle */}
                <div className="space-y-1 pt-1">
                  <div className="flex justify-between text-xs font-semibold text-slate-600">
                    <span>Billing Cycle: Day 10 of 30</span>
                    <span className="text-blue-600 font-bold">66% Cycle Left</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 w-[33%] rounded-full" />
                  </div>
                </div>

                {/* Invoices List preview */}
                <div className="pt-2 space-y-1.5">
                  <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>Recent Invoices</span>
                    <span className="text-blue-600 cursor-pointer">All Invoices →</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                    <div className="flex items-center space-x-2">
                      <FileText className="w-4 h-4 text-blue-600" />
                      <span className="font-bold text-slate-900">INV-2026-000022</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-emerald-600">₹1,499.00 PAID</span>
                      <span className="text-[10px] bg-slate-200 px-1.5 py-0.5 rounded font-mono">PDF</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ======================================================= */}
            {/* FLOATING UI CARDS AT DIFFERENT DEPTHS                   */}
            {/* ======================================================= */}
            
            {/* Floating Card 1: Top-Left "Invoice Generated PDF" */}
            <div className="absolute -top-6 -left-6 sm:-left-10 bg-white/95 backdrop-blur-xl border border-white p-3.5 rounded-2xl shadow-xl shadow-blue-500/10 flex items-center space-x-3 animate-float-slow z-20">
              <div className="w-8 h-8 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600">
                <Download className="w-4 h-4" />
              </div>
              <div className="text-left">
                <span className="text-xs font-bold text-slate-900 block leading-tight">GST Tax Invoice</span>
                <span className="text-[10px] text-blue-600 font-semibold">ReportLab Compiled (RAM)</span>
              </div>
            </div>

            {/* Floating Card 2: Top-Right "Dunning Recovered" */}
            <div className="absolute top-10 -right-6 sm:-right-8 bg-white/95 backdrop-blur-xl border border-white p-3 rounded-2xl shadow-xl shadow-blue-500/10 flex items-center space-x-2.5 animate-float-delayed z-20">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 flex items-center justify-center text-emerald-600">
                <RefreshCw className="w-4 h-4" />
              </div>
              <div className="text-left">
                <span className="text-xs font-bold text-slate-900 block leading-tight">Dunning Recovered!</span>
                <span className="text-[10px] text-emerald-600 font-semibold">PAST_DUE → ACTIVE</span>
              </div>
            </div>

            {/* Floating Card 3: Bottom-Left "Webhook HMAC-SHA256" */}
            <div className="absolute -bottom-6 -left-4 sm:-left-8 bg-white/95 backdrop-blur-xl border border-white p-3 rounded-2xl shadow-xl shadow-blue-500/10 flex items-center space-x-3 animate-float-reverse z-20">
              <div className="w-8 h-8 rounded-xl bg-violet-100 flex items-center justify-center text-violet-600">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="text-left">
                <span className="text-xs font-bold text-slate-900 block leading-tight">HMAC-SHA256 Verified</span>
                <span className="text-[10px] text-violet-600 font-semibold">Zero Timing Attacks</span>
              </div>
            </div>

            {/* Floating Card 4: Bottom-Right "Revenue Telemetry" */}
            <div className="absolute bottom-12 -right-4 sm:-right-8 bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-3 rounded-2xl shadow-xl shadow-blue-500/25 flex items-center space-x-2.5 animate-float-slow z-20">
              <TrendingUp className="w-5 h-5 text-cyan-200" />
              <div className="text-left">
                <span className="text-xs font-black block leading-tight">₹12.4L Collected</span>
                <span className="text-[9px] uppercase tracking-wider text-blue-100 font-semibold">+18.4% This Month</span>
              </div>
            </div>

            {/* 3D Isometric Tech Props */}
            <div className="absolute -top-12 right-20 w-14 h-14 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 border-2 border-cyan-400/80 shadow-[0_0_20px_rgba(34,211,238,0.4)] flex items-center justify-center animate-float-delayed pointer-events-none">
              <Cpu className="w-7 h-7 text-cyan-400" />
            </div>

            <div className="absolute -bottom-10 right-28 w-12 h-12 rounded-xl bg-white/40 backdrop-blur-md border border-white/80 shadow-lg flex items-center justify-center animate-float-reverse pointer-events-none">
              <Activity className="w-6 h-6 text-indigo-600" />
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* 3. CORE CAPABILITIES (Features Grid)                      */}
      {/* ========================================================= */}
      <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-t border-slate-100">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-bold border border-blue-200">
            <Zap className="w-3.5 h-3.5" />
            <span>Architecture Pillars</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
            Engineered for Financial Integrity
          </h2>
          <p className="text-sm sm:text-base text-slate-600">
            Every layer of BillWise guarantees mathematical accuracy, cryptographic security, and automated revenue recovery.
          </p>
        </div>

        {/* 3 Flagship Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          
          {/* Card 1: Pure Proration Math */}
          <div className="group bg-white rounded-3xl border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-2xl hover:border-blue-300 hover:-translate-y-1.5 transition-all duration-300 p-8 space-y-5">
            <div className="w-12 h-12 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center shadow-sm">
              <RefreshCw className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors">
              Pure Proration Math
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Second-level precision proration credit and charge formulas with integer paise storage. Completely eliminates floating-point rounding errors during mid-cycle tier changes.
            </p>
            <div className="pt-2 text-xs font-mono font-semibold text-blue-700 flex items-center space-x-1">
              <span>calculate_proration()</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Card 2: Automated Dunning Engine */}
          <div id="dunning" className="group bg-white rounded-3xl border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-2xl hover:border-indigo-300 hover:-translate-y-1.5 transition-all duration-300 p-8 space-y-5">
            <div className="w-12 h-12 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center shadow-sm">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
              Automated Dunning Engine
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Fights involuntary churn through a smart retry schedule (Days 1, 3, 5). Grants a customer grace period in <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">PAST_DUE</code> and recovers to <code className="text-xs bg-slate-100 px-1 py-0.5 rounded">ACTIVE</code> upon payment.
            </p>
            <div className="pt-2 text-xs font-mono font-semibold text-indigo-700 flex items-center space-x-1">
              <span>process_dunning_retries()</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>

          {/* Card 3: In-Memory PDF Generation */}
          <div className="group bg-white rounded-3xl border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-2xl hover:border-violet-300 hover:-translate-y-1.5 transition-all duration-300 p-8 space-y-5">
            <div className="w-12 h-12 rounded-2xl bg-violet-100 text-violet-600 flex items-center justify-center shadow-sm">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 group-hover:text-violet-600 transition-colors">
              Stateless PDF Invoicing
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Server-side compiled ReportLab tax invoices rendered strictly in RAM (<code className="text-xs bg-slate-100 px-1 py-0.5 rounded">io.BytesIO</code>). Zero server disk exhaustion, 18% GST itemization, and authenticated IDOR protection.
            </p>
            <div className="pt-2 text-xs font-mono font-semibold text-violet-700 flex items-center space-x-1">
              <span>GET /api/invoices/{'{id}'}/pdf</span>
              <ChevronRight className="w-4 h-4" />
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* 4. PRICING PLANS SECTION                                  */}
      {/* ========================================================= */}
      <section id="pricing" className="py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-t border-slate-200/80">
        <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
          <span className="text-xs font-extrabold uppercase tracking-widest text-blue-600">Transparent Pricing</span>
          <h2 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
            Plans Designed to Scale With You
          </h2>
          <p className="text-sm sm:text-base text-slate-600">
            Switch plans at any moment. BillWise automatically prorates the exact second-level difference.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {PLANS.map((plan) => (
            <div
              key={plan.code}
              className={`rounded-3xl p-8 flex flex-col justify-between transition-all duration-300 ${
                plan.featured
                  ? 'bg-slate-900 text-white shadow-2xl scale-105 border-2 border-blue-500 relative'
                  : 'bg-white text-slate-900 border border-slate-200 shadow-sm hover:shadow-lg'
              }`}
            >
              {plan.featured && (
                <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-sm">
                  Most Popular
                </span>
              )}

              <div className="space-y-4">
                <div>
                  <h3 className="text-xl font-bold">{plan.name}</h3>
                  <p className={`text-xs mt-1 ${plan.featured ? 'text-slate-400' : 'text-slate-500'}`}>{plan.desc}</p>
                </div>

                <div className="flex items-baseline space-x-1">
                  <span className="text-4xl font-black tracking-tight">{plan.price}</span>
                  <span className={`text-xs ${plan.featured ? 'text-slate-400' : 'text-slate-500'}`}>{plan.period}</span>
                </div>

                <div className={`pt-4 border-t ${plan.featured ? 'border-slate-800' : 'border-slate-100'} space-y-3 text-xs`}>
                  {plan.features.map((feat, i) => (
                    <div key={i} className="flex items-center space-x-2.5">
                      <Check className={`w-4 h-4 flex-shrink-0 ${plan.featured ? 'text-cyan-400' : 'text-blue-600'}`} />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-8">
                <Link
                  to="/login"
                  className={`w-full py-3 rounded-xl text-xs font-bold transition-all block text-center ${
                    plan.featured
                      ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/30'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
                  }`}
                >
                  Select {plan.name}
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ========================================================= */}
      {/* 5. CINEMATIC DARK FINAL CTA SECTION                       */}
      {/* ========================================================= */}
      <section className="relative py-28 px-4 sm:px-6 lg:px-8 bg-[#070913] text-white overflow-hidden">
        
        {/* Background Radial Glow Lights & Grid */}
        <div className="absolute inset-0 bg-tech-grid-dark opacity-20 pointer-events-none" />
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[40rem] h-[25rem] bg-blue-600/25 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute -bottom-20 right-1/4 w-[25rem] h-[25rem] bg-indigo-500/20 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/15 text-cyan-300 text-xs font-bold">
            <Terminal className="w-3.5 h-3.5" />
            <span>Ready for Production Deployment</span>
          </div>

          <h2 className="text-4xl sm:text-6xl font-black tracking-tight text-white leading-tight">
            Take control of your subscription revenue{' '}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-violet-400 bg-clip-text text-transparent">
              today.
            </span>
          </h2>

          <p className="text-base sm:text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
            Test the live customer portal, trigger automated dunning retries, and experience transparent proration math firsthand.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <Link
              to="/login"
              className="inline-flex items-center space-x-2 px-8 py-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 shadow-xl shadow-blue-600/30 hover:shadow-blue-600/50 hover:scale-105 transition-all"
            >
              <span>Launch Demo Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="#pricing"
              className="inline-flex items-center space-x-2 px-8 py-4 rounded-xl font-bold text-sm text-slate-300 bg-white/5 border border-white/10 backdrop-blur-md hover:bg-white/10 hover:text-white transition-all"
            >
              <span>View Pricing Plans</span>
            </a>
          </div>
        </div>
      </section>

      {/* ========================================================= */}
      {/* 6. MINIMAL FOOTER                                         */}
      {/* ========================================================= */}
      <footer className="bg-[#05060D] text-slate-500 py-12 px-4 sm:px-6 lg:px-8 border-t border-white/5">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-6">
          
          {/* Logo & Copyright */}
          <div className="flex items-center space-x-3">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <CreditCard className="w-4 h-4" />
            </div>
            <span className="text-sm font-bold text-slate-300">BILLWISE</span>
            <span className="text-xs text-slate-600">© 2026 BillWise SaaS Billing Platform. All rights reserved.</span>
          </div>

          {/* Links */}
          <div className="flex items-center space-x-6 text-xs font-semibold text-slate-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#proration" className="hover:text-white transition-colors">Proration</a>
            <a href="#dunning" className="hover:text-white transition-colors">Dunning</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </div>

          {/* Social Icons */}
          <div className="flex items-center space-x-4 text-slate-400">
            <a href="https://github.com" target="_blank" rel="noreferrer" aria-label="GitHub" className="hover:text-white transition-colors">
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
            </a>
            <a href="https://twitter.com" target="_blank" rel="noreferrer" aria-label="Twitter" className="hover:text-white transition-colors">
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
            </a>
            <a href="https://linkedin.com" target="_blank" rel="noreferrer" aria-label="LinkedIn" className="hover:text-white transition-colors">
              <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.761-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
