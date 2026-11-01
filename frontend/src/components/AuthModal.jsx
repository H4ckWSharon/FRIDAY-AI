import React, { useState } from 'react';
import { X, Lock, Mail, AlertCircle, ArrowRight } from 'lucide-react';
import { loginWithGoogle, loginWithEmail, registerWithEmail } from '../services/firebase';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleGoogle = async () => {
    setError('');
    setLoading(true);
    try {
      await loginWithGoogle();
      onAuthSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Google sign-in failed');
    } finally {
      setLoading(false);
    }
  };

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please provide email and password.');
      return;
    }
    setLoading(true);
    try {
      if (isRegister) {
        await registerWithEmail(email, password);
      } else {
        await loginWithEmail(email, password);
      }
      onAuthSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md">
      <div className="relative w-full max-w-sm rounded-2xl bg-[#0b0b0f] border border-[#22222d] p-5 sm:p-6 shadow-2xl text-left max-h-[90dvh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-[#16161f] transition-colors cursor-pointer"
          aria-label="Close Authentication Modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-full overflow-hidden border border-[#FF3038]/50 bg-[#0d0e11] p-0.5 flex items-center justify-center shadow-[0_0_12px_rgba(255,48,56,0.25)] shrink-0">
            <img 
              src="/logo.png" 
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = 'https://lh3.googleusercontent.com/aida-public/AB6AXuAcN1eRjJArxV6rgrKmESKWs6pNIIgghz2t08lwPHUbguzKUi6_QBkU6zT2Alm2IBhnUq5gJooHVbDYG5riYM9mTAd0ESKoFB_W7ofJEOdvKes4PoKqQ6WVDiu1mvJFhvhPDnO_TLp6O9JInIaI90cgk4l-ucK4jUIi3tQs4KaRFKhTHD-RnluE92sypzaKlZKRApmkyQVRLZX1VjzzTnzvdQZqhmEdoOHihdVh4zvOOVtYyxb5yWK1azp9GQahS68FJg';
              }}
              alt="FRIDAY AI" 
              className="w-full h-full object-cover rounded-full"
            />
          </div>
          <div>
            <h3 className="font-heading font-bold text-base text-white">
              {isRegister ? 'Operator Registration' : 'Operator Authentication'}
            </h3>
            <p className="text-[11px] font-mono text-zinc-400">
              FRIDAY Red Team Infrastructure
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="truncate">{error}</span>
          </div>
        )}

        {/* Google Sign In */}
        <button
          onClick={handleGoogle}
          disabled={loading}
          className="w-full py-2.5 px-4 rounded-xl bg-[#14141c] hover:bg-[#1a1a24] border border-[#272736] text-xs font-semibold text-zinc-200 flex items-center justify-center gap-2.5 transition-all shadow-sm active:scale-98 mb-4"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          <span>Continue with Google</span>
        </button>

        <div className="flex items-center my-4">
          <div className="flex-1 border-t border-[#1e1e28]"></div>
          <span className="px-2 text-[10px] font-mono text-zinc-500 uppercase">Or with email</span>
          <div className="flex-1 border-t border-[#1e1e28]"></div>
        </div>

        {/* Email form */}
        <form onSubmit={handleEmailAuth} className="space-y-3">
          <div>
            <label className="block text-[11px] font-mono text-zinc-400 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="operator@redteam.sec"
                className="w-full bg-[#101015] border border-[#20202c] rounded-lg pl-8 pr-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#FF3038]/60 font-mono transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-zinc-400 mb-1">Security Key / Password</label>
            <div className="relative">
              <Lock className="w-3.5 h-3.5 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full bg-[#101015] border border-[#20202c] rounded-lg pl-8 pr-3 py-2 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-[#FF3038]/60 font-mono transition-colors"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-[#FF3038] hover:bg-[#ff4d54] text-white text-xs font-semibold shadow-[0_0_15px_rgba(255,48,56,0.3)] transition-all flex items-center justify-center gap-2 mt-4 active:scale-98"
          >
            <span>{isRegister ? 'Create Operator Account' : 'Authenticate Operator'}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* Toggle mode */}
        <div className="mt-4 text-center">
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              setError('');
            }}
            className="text-[11px] text-zinc-400 hover:text-white transition-colors"
          >
            {isRegister ? 'Already have credentials? Sign in' : "New operator? Initialize access"}
          </button>
        </div>
      </div>
    </div>
  );
}

