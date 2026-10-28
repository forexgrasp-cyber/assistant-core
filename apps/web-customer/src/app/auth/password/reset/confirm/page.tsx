'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Link from 'next/link';
import { Lock, AlertCircle, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface PasswordResetConfirmForm {
  password: string;
  confirm_password: string;
}

export default function PasswordResetConfirmPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState('');
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const token = searchParams.get('token') || '';

  const { register, handleSubmit, formState: { errors } } = useForm<PasswordResetConfirmForm>({
    defaultValues: {
      password: '',
      confirm_password: '',
    },
  });

  const onSubmit = async (data: PasswordResetConfirmForm) => {
    try {
      setError('');

      if (data.password !== data.confirm_password) {
        setError('Passwords do not match');
        return;
      }

      const response = await api.post('/auth/password/reset/confirm', {
        token,
        password: data.password,
      });

      if (response.ok) {
        toast.success('Password reset successfully');
        router.push('/login');
      } else {
        throw new Error(response.data?.detail || 'Failed to reset password');
      }
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to reset password. Please try again.');
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4">
        <div className="w-full max-w-md bg-card rounded-xl border border-border shadow-xl p-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-foreground">Invalid Reset Link</h1>
            <p className="text-muted-foreground mt-2">The password reset link is invalid or has expired.</p>
            <Link href="/login" className="text-primary hover:underline mt-4 inline-block">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md bg-card rounded-xl border border-border shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-foreground">Reset Password</h1>
          <p className="text-muted-foreground mt-2">Create a new password for your account</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
          <div className="space-y-4">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1.5">
                New Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  {...register('password')}
                  type={showConfirmPassword ? 'text' : 'password'}
                  id="password"
                  className="w-full pl-10 pr-12 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="********"
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
                {errors.password && (
                  <p id="password-error" className="mt-1 text-sm text-destructive" role="alert">
                    <AlertCircle className="inline w-3 h-3 mr-1" />
                    {errors.password.message}
                  </p>
                )}
              </div>
            </div>

            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-foreground mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  {...register('confirm_password')}
                  type={showConfirmPassword ? 'text' : 'password'}
                  id="confirm_password"
                  className="w-full pl-10 pr-12 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="********"
                  aria-invalid={!!errors.confirm_password}
                  aria-describedby={errors.confirm_password ? 'confirm_password-error' : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
                {errors.confirm_password && (
                  <p id="confirm_password-error" className="mt-1 text-sm text-destructive" role="alert">
                    <AlertCircle className="inline w-3 h-3 mr-1" />
                    {errors.confirm_password.message}
                  </p>
                )}
              </div>
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
            Reset Password
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}