'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import Link from 'next/link';
import { Eye, EyeOff, Mail, Lock, AlertCircle, User, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface RegisterForm {
  email: string;
  password: string;
  confirm_password: string;
  first_name: string;
  last_name: string;
  agency_name: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');

  const { register, handleSubmit, watch, formState: { errors } } = useForm<RegisterForm>({
    defaultValues: {
      email: '',
      password: '',
      confirm_password: '',
      first_name: '',
      last_name: '',
      agency_name: '',
    },
  });

  const onSubmit = async (data: RegisterForm) => {
    try {
      setError('');

      if (data.password !== data.confirm_password) {
        setError('Passwords do not match');
        return;
      }

      const response = await api.post('/auth/register', {
        email: data.email,
        password: data.password,
        first_name: data.first_name,
        last_name: data.last_name,
        agency_name: data.agency_name,
      });

      const { access_token, refresh_token } = response.data;

      // Store tokens
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      toast.success('Account created successfully!');
      router.push('/dashboard');
    } catch (error: any) {
      if (error.response?.status === 400 && error.response.data?.detail === 'Email already registered') {
        setError('An account with this email already exists');
      } else {
        setError(error.response?.data?.detail || 'Registration failed. Please try again.');
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50 px-4">
      <div className="w-full max-w-md bg-card rounded-xl border border-border shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-foreground">Create Account</h1>
          <p className="text-muted-foreground mt-2">Join the Retention Analytics platform</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6" noValidate>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <label htmlFor="first_name" className="block text-sm font-medium text-foreground">
                First Name
              </label>
              <input
                {...register('first_name')}
                type="text"
                id="first_name"
                className="w-full pl-10 pr-4 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="John"
                aria-invalid={!!errors.first_name}
                aria-describedby={errors.first_name ? 'first_name-error' : undefined}
              />
              {errors.first_name && (
                <p id="first_name-error" className="mt-1 text-sm text-destructive" role="alert">
                  <AlertCircle className="inline w-3 h-3 mr-1" />
                  {errors.first_name.message}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="last_name" className="block text-sm font-medium text-foreground">
                Last Name
              </label>
              <input
                {...register('last_name')}
                type="text"
                id="last_name"
                className="w-full pl-10 pr-4 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="Doe"
                aria-invalid={!!errors.last_name}
                aria-describedby={errors.last_name ? 'last_name-error' : undefined}
              />
              {errors.last_name && (
                <p id="last_name-error" className="mt-1 text-sm text-destructive" role="alert">
                  <AlertCircle className="inline w-3 h-3 mr-1" />
                  {errors.last_name.message}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
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

            <div className="flex items-center gap-2">
              <label htmlFor="agency_name" className="block text-sm font-medium text-foreground mb-1.5">
                Agency / Company Name
              </label>
              <input
                {...register('agency_name')}
                type="text"
                id="agency_name"
                className="w-full pl-10 pr-4 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                placeholder="Acme Corp"
                aria-invalid={!!errors.agency_name}
                aria-describedby={errors.agency_name ? 'agency_name-error' : undefined}
              />
              {errors.agency_name && (
                <p id="agency_name-error" className="mt-1 text-sm text-destructive" role="alert">
                  <AlertCircle className="inline w-3 h-3 mr-1" />
                  {errors.agency_name.message}
                </p>
              )}
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  className="w-full pl-10 pr-12 py-2.5 border border-input bg-background rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  placeholder="********"
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
            Create Account
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

        <div className="mt-8 text-center text-xs text-muted-foreground">
          <p>By signing up, you agree to our <Link href="/terms" className="underline">Terms of Service</Link> and <Link href="/privacy" className="underline">Privacy Policy</Link>.</p>
        </div>
      </div>
    </div>
  );
}