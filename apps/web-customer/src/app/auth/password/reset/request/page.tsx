'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Link from 'next/link';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface PasswordResetRequestForm {
  email: string;
}

export default function PasswordRequestPage() {
  const router = useRouter();
  const [emailSent, setEmailSent] = useState(false);
  const [error, setError] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<PasswordResetRequestForm>({
    defaultValues: {
      email: '',
    },
  });

  const onSubmit = async (data: PasswordResetRequestForm) => {
    try {
      setError('');
      const response = await api.post('/auth/password/reset/request', {
        email: data.email,
      });

      if (response.ok || response.status === 200) {
        setEmailSent(true);
      } else {
        throw new Error(response.data?.detail || 'Failed to send reset email');
      }
    } catch (error: any) {
      // Always show success to prevent email enumeration
      setEmailSent(true);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md bg-card rounded-xl border border-border shadow-xl p-8">
        {emailSent ? (
          <div className="text-center">
            <h1 className="text-2xl font-bold text-foreground">Check Your Email</h1>
            <p className="text-muted-foreground mt-2">We've sent a password reset link to your email</p>
          </div>
        ) : (
          <>
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-foreground">Forgot Password</h1>
              <p className="text-muted-foreground mt-2">Enter your email and we'll send you a reset link</p>
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
                  Send Reset Link
                </button>
              </div>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-muted-foreground">
                Already have an account?{' '}
                <Link href="/login" className="text-primary hover:underline font-medium">
                  Sign in
                </Link>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}