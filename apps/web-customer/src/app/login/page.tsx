'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Link from 'next/link';
import { Eye, EyeOff, Loader2, Mail, Lock, AlertCircle } from 'lucide-react';
import { useAppStore } from '@/store';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface LoginForm {
  email: string;
  password: string;
  remember_me: boolean;
  mfa_token?: string;
}

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setAuth, loading, setLoading } = useAppStore();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isMfa, setIsMfa] = useState(false);
  
  const redirect = useSearchParams().get('redirect') || '/';
  
  const { register, handleSubmit, watch, formState: { errors } } = useForm<LoginForm>({
    defaultValues: {
      email: '',
      password: '',
      remember_me: false,
    },
  });

  const onSubmit = async (data: LoginForm) => {
    try {
      setError('');
      const payload = {
        email: data.email,
        password: data.password,
        remember_me: data.remember_me,
        mfa_token: data.mfa_token,
      };

      const response = await api.post('/auth/login', payload);
      const { access_token, refresh_token, user, requires_mfa } = response.data;

      if (requires_mfa) {
        // MFA required - handled by the API returning 401 with mfa_required header
        return;
      }

      // Store tokens
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      // Update store
      // The store will be updated via the auth check on next page load
      window.location.href = redirect;
    } catch (error: any) {
      if (error.response?.status === 401 && error.response.data?.detail === 'MFA required') {
        setIsMfa(true);
        return;
      }
      throw error;
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md bg-card rounded-xl border border-border shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-foreground">Welcome back</h1>
          <p className="text-muted-foreground mt-2">Sign in to your Retention Analytics account</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1.5">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  {...register('email')}
                  type="email"
                  id="email"
                  className="w-full pl-10 pr-4 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="you@company.com"
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                />
                {errors.email && (
                  <p id="email-error" className="mt-1 text-sm text-destructive" role="alert">
                    <AlertCircle className="inline w-3 h-3 mr-1" />
                    {errors.email.message}
                  </p>
                )}
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label htmlFor="password" className="block text-sm font-medium text-foreground">
                  Password
                </label>
                <Link href="/auth/password/reset/request" className="text-sm text-primary hover:underline">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  className="w-full pl-10 pr-12 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="••••••••"
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
                {errors.password && (
                  <p id="password-error" className="mt-1 text-sm text-destructive" role="alert">
                    <AlertCircle className="inline w-3 h-3 mr-1" />
                    {errors.password.message}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  {...register('remember_me')}
                  type="checkbox"
                  className="w-4 h-4 rounded border-input bg-background text-primary focus:ring-2 focus:ring-primary"
                />
                <span className="text-sm text-muted-foreground">Remember me</span>
              </label>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg text-sm" role="alert">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={false}
            className="w-full py-2.5 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Sign in
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link href="/register" className="text-primary hover:underline font-medium">
              Create an account
            </Link>
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            <Link href="/auth/password/reset/request" className="text-primary hover:underline">
              Forgot your password?
            </Link>
          </p>
        </div>
      </div>

      <div className="mt-8 text-center text-xs text-muted-foreground">
        <p>By signing in, you agree to our <Link href="/terms" className="underline">Terms of Service</Link> and <Link href="/privacy" className="underline">Privacy Policy</Link>.</p>
      </div>
    </div>
  );
}
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginFormContent />
    </Suspense>
  );
}
