import React, { useState } from 'react';
import { X, Check, Sparkles, Shield, Zap, Terminal } from 'lucide-react';
import { createOrder, verifyPayment } from '../services/api';

export default function PricingModal({
  isOpen,
  onClose,
  currentUser,
  onOpenAuth,
  onPaymentSuccess,
}) {
  const [billingCycle, setBillingCycle] = useState('monthly'); // 'monthly' | 'yearly'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const planId = billingCycle === 'yearly' ? 'cyber_pro_yearly' : 'cyber_pro_monthly';
  const priceDisplay = billingCycle === 'yearly' ? '₹35,000' : '₹3,500';
  const pricePeriod = billingCycle === 'yearly' ? '/year' : '/month';

  const handleCheckout = async () => {
    setError('');
    if (!currentUser) {
      onClose();
      onOpenAuth();
      return;
    }

    if (typeof window.Razorpay === 'undefined') {
      setError('Razorpay SDK failed to load. Please check network connection.');
      return;
    }

    setLoading(true);
    try {
      const order = await createOrder(planId);

      const options = {
        key: order.razorpay_key_id,
        amount: order.amount,
        currency: order.currency || 'INR',
        name: 'FRIDAY AI',
        description: order.plan_label || 'friday Cyber Pro Subscription',
        order_id: order.order_id,
        prefill: {
          email: currentUser.email || '',
          name: currentUser.displayName || '',
        },
        theme: { color: '#FF3038' },
        handler: async function (response) {
          try {
            await verifyPayment({
              plan_id: planId,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            });
            onPaymentSuccess();
            onClose();
          } catch (err) {
            setError(err.message || 'Payment verification failed');
          }
        },
        modal: {
          ondismiss: function () {
            setLoading(false);
          },
        },
      };

      const rzp = new window.Razorpay(options);
      rzp.on('payment.failed', function (resp) {
        setError(resp.error?.description || 'Transaction declined');
        setLoading(false);
      });
      rzp.open();
    } catch (err) {
      setError(err.message || 'Failed to initiate checkout');
      setLoading(false);
    }
  };

  const PRO_FEATURES = [
    'Ultra-fast GPU Inference (<0.8s TTFT)',
    '100% Uncensored Offensive Intelligence',
    'Unlimited Daily Exploitation Conversations',
    'Exploit Payloads, Evasion & Memory Logic',
    'Senior Red Team Adversarial Persona',
    'Zero Telemetry & Private Conversation Storage',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md">
      <div className="relative w-full max-w-md rounded-2xl bg-[#0b0b0f] border border-[#262633] p-5 sm:p-6 shadow-2xl text-left max-h-[90dvh] overflow-y-auto">
        {/* Subtle Crimson Glow */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-[#FF3038]/10 blur-3xl pointer-events-none"></div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-[#16161f] transition-colors cursor-pointer"
          aria-label="Close Pricing Modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#160b0c] border border-[#FF3038]/40 w-fit text-[#FF555D] text-[11px] font-mono mb-3">
          <Sparkles className="w-3.5 h-3.5" />
          <span>FRIDAY CYBER PRO</span>
        </div>

        <h3 className="font-heading font-extrabold text-2xl text-white tracking-tight mb-1">
          Unleash Unconstrained Red Team Compute
        </h3>
        <p className="text-xs text-zinc-400 mb-6 leading-relaxed">
          Upgrade to enterprise Nvidia GPU infrastructure for unconstrained offensive research.
        </p>

        {/* Billing Cycle Switcher */}
        <div className="flex items-center p-1 rounded-xl bg-[#121218] border border-[#1e1e28] mb-6">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`flex-1 py-1.5 text-xs font-heading font-semibold rounded-lg transition-all ${
              billingCycle === 'monthly'
                ? 'bg-[#1e1e28] text-white shadow'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingCycle('yearly')}
            className={`flex-1 py-1.5 text-xs font-heading font-semibold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              billingCycle === 'yearly'
                ? 'bg-[#1e1e28] text-white shadow'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <span>Yearly</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              Save 20%
            </span>
          </button>
        </div>

        {/* Price Card */}
        <div className="p-4 rounded-xl bg-[#0f0f14] border border-[#FF3038]/30 mb-6 flex items-baseline justify-between">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="font-heading text-3xl font-extrabold text-white">{priceDisplay}</span>
              <span className="font-mono text-xs text-zinc-500">{pricePeriod}</span>
            </div>
            <span className="text-[11px] text-zinc-400 font-mono">Instant activation via Razorpay</span>
          </div>
          <div className="w-8 h-8 rounded-lg bg-[#181822] border border-[#2a2a38] flex items-center justify-center">
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
        </div>

        {/* Feature List */}
        <div className="space-y-2.5 mb-6">
          {PRO_FEATURES.map((feat, i) => (
            <div key={i} className="flex items-center gap-2.5 text-xs text-zinc-300">
              <div className="w-4 h-4 rounded-full bg-emerald-950/60 border border-emerald-800/50 flex items-center justify-center shrink-0">
                <Check className="w-2.5 h-2.5 text-emerald-400" />
              </div>
              <span>{feat}</span>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-4 p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {/* Checkout CTA */}
        <button
          onClick={handleCheckout}
          disabled={loading}
          className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[#FF3038] to-[#b30008] hover:from-[#ff4d54] hover:to-[#cc000a] text-white text-xs font-heading font-bold shadow-[0_0_20px_rgba(255,48,56,0.35)] transition-all flex items-center justify-center gap-2 active:scale-98"
        >
          <Sparkles className="w-4 h-4" />
          <span>{loading ? 'Preparing Secure Gateway…' : 'Upgrade to Friday Cyber Pro'}</span>
        </button>

        <p className="text-[10px] font-mono text-zinc-500 text-center mt-3">
          Secured by 256-bit SSL &bull; Cancel anytime with one click
        </p>
      </div>
    </div>
  );
}

