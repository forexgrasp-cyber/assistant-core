/**
 * VA Matching Platform - Main JavaScript Application
 * 
 * Handles common UI interactions, form validation, toast notifications,
 * and shared utilities across the platform.
 */

(function() {
  'use strict';

  // ========================================
  // UTILITIES
  // ========================================
  
  const Utils = {
    // Debounce function
    debounce(fn, delay) {
      let timeoutId;
      return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => fn.apply(this, args), delay);
      };
    },
    
    // Throttle function
    throttle(fn, limit) {
      let inThrottle;
      return (...args) => {
        if (!inThrottle) {
          fn.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },
    
    // Format currency
    formatCurrency(amount, currency = 'USD') {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount);
    },
    
    // Format date
    formatDate(date, options = {}) {
      const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      };
      return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
    },
    
    // Generate UUID
    generateId() {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
    },
    
    // Get CSRF token from meta tag
    getCsrfToken() {
      const meta = document.querySelector('meta[name="csrf-token"]');
      return meta ? meta.content : null;
    },
    
    // Show/hide loading state on button
    setButtonLoading(button, loading) {
      if (loading) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner spinner-sm mr-2"></span>Loading...';
        button.disabled = true;
      } else {
        button.innerHTML = button.dataset.originalText || button.innerHTML;
        button.disabled = false;
      }
    }
  };
  
  // ========================================
  // TOAST NOTIFICATIONS
  // ========================================
  
  const Toast = {
    container: null,
    
    init() {
      if (!this.container) {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
          this.container = document.createElement('div');
          this.container.id = 'toast-container';
          this.container.className = 'fixed bottom-4 right-4 z-50 space-y-2';
          this.container.setAttribute('aria-live', 'polite');
          this.container.setAttribute('aria-label', 'Notifications');
          document.body.appendChild(this.container);
        }
      }
    },
    
    show(message, type = 'info', duration = 5000) {
      this.init();
      
      const toast = document.createElement('div');
      toast.className = `toast toast-${type} animate-slide-up`;
      toast.setAttribute('role', 'alert');
      toast.setAttribute('aria-live', 'assertive');
      
      const icons = {
        success: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>',
        error: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>',
        warning: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3h13.856c1.54 0 2.502-1.667 1.732-3z"></path></svg>',
        info: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
      };
      
      toast.innerHTML = `
        ${icons[type] || icons.info}
        <span class="flex-1">${message}</span>
        <button type="button" class="toast-close" aria-label="Dismiss" onclick="this.parentElement.remove()">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      `;
      
      toast.className = `toast toast-${type} animate-slide-up`;
      toast.setAttribute('role', 'alert');
      toast.setAttribute('aria-live', 'assertive');
      
      this.container.appendChild(toast);
      
      // Auto-remove after duration
      if (duration > 0) {
        setTimeout(() => {
          toast.style.animation = 'slide-up 0.3s ease-out reverse';
          setTimeout(() => toast.remove(), 300);
        }, duration);
      }
      
      // Click to dismiss
      toast.addEventListener('click', () => {
        toast.style.animation = 'slide-up 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
      });
    },
    
    success(message, duration) { this.show(message, 'success', duration); },
    error(message, duration) { this.show(message, 'error', duration); },
    warning(message, duration) { this.show(message, 'warning', duration); },
    info(message, duration) { this.show(message, 'info', duration); }
  };
  
  // ========================================
  // FORM VALIDATION
  // ========================================
  
  const FormValidator = {
    rules: {
      required: (value) => value !== '' && value !== null && value !== undefined,
      email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
      minLength: (value, min) => value.length >= min,
      maxLength: (value, max) => value.length <= max,
      pattern: (value, regex) => regex.test(value),
      number: (value) => !isNaN(parseFloat(value)) && isFinite(value),
      min: (value, min) => parseFloat(value) >= min,
      max: (value, max) => parseFloat(value) <= max
    },
    
    validateField(field, rules) {
      const value = field.value;
      const errors = [];
      
      for (const [rule, params] of Object.entries(rules)) {
        const validator = this.rules[rule];
        if (validator) {
          const args = Array.isArray(params) ? params : [params];
          if (!validator(value, ...args)) {
            errors.push(this.getErrorMessage(rule, params));
          }
        }
      }
      
      return errors;
    },
    
    getErrorMessage(rule, params) {
      const messages = {
        required: 'This field is required',
        email: 'Please enter a valid email address',
        minLength: `Must be at least ${params} characters`,
        maxLength: `Must be no more than ${params} characters`,
        pattern: 'Invalid format',
        number: 'Must be a valid number',
        min: `Must be at least ${params}`,
        max: `Must be no more than ${params}`
      };
      return messages[rule] || 'Invalid value';
    },
    
    validateForm(form, fieldRules) {
      let isValid = true;
      const allErrors = {};
      
      for (const [fieldName, rules] of Object.entries(fieldRules)) {
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (!field) continue;
        
        const errors = this.validateField(field, rules);
        if (errors.length > 0) {
          isValid = false;
          allErrors[fieldName] = errors;
          this.showFieldError(field, errors[0]);
        } else {
          this.clearFieldError(field);
        }
      }
      
      return { isValid, errors: allErrors };
    },
    
    showFieldError(field, message) {
      field.classList.add('border-error');
      field.setAttribute('aria-invalid', 'true');
      field.setAttribute('aria-describedby', `${field.id}-error`);
      
      let errorEl = document.getElementById(`${field.id}-error`);
      if (!errorEl) {
        errorEl = document.createElement('div');
        errorEl.id = `${field.id}-error`;
        errorEl.className = 'form-error';
        errorEl.setAttribute('role', 'alert');
        field.parentNode.appendChild(errorEl);
      }
      errorEl.textContent = message;
    },
    
    clearFieldError(field) {
      field.classList.remove('border-error');
      field.removeAttribute('aria-invalid');
      field.removeAttribute('aria-describedby');
      const errorEl = document.getElementById(`${field.id}-error`);
      if (errorEl) errorEl.remove();
    }
  };
  
  // ========================================
  // API CLIENT
  // ========================================
  
  const Api = {
    baseUrl: '/api',
    
    async request(endpoint, options = {}) {
      const url = `${this.baseUrl}${endpoint}`;
      const options_ = {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      };
      
      const csrfToken = Utils.getCsrfToken();
      if (csrfToken) {
        options_.headers['X-CSRF-Token'] = csrfToken;
      }
      
      const response = await fetch(url, options_);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      
      return response.json();
    },
    
    get(endpoint) {
      return this.request(endpoint, { method: 'GET' });
    },
    
    post(endpoint, data) {
      return this.request(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
      });
    },
    
    put(endpoint, data) {
      return this.request(endpoint, {
        method: 'PUT',
        body: JSON.stringify(data)
      });
    },
    
    delete(endpoint) {
      return this.request(endpoint, { method: 'DELETE' });
    }
  };
  
  // ========================================
  // CHART HELPERS
  // ========================================
  
  const Charts = {
    defaults: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'var(--color-neutral-900)',
          titleColor: 'var(--color-text-inverse)',
          bodyColor: 'var(--color-text-inverse)',
          borderColor: 'var(--color-border-primary)',
          borderWidth: 1,
          padding: 12,
          cornerRadius: 8,
          displayColors: false
        }
      },
      scales: {
        x: { grid: { color: 'var(--color-border-primary)' } },
        y: { grid: { color: 'var(--color-border-primary)' } }
      }
    },
    
    createLineChart(ctx, data, options = {}) {
      return new Chart(ctx, {
        type: 'line',
        data,
        options: { ...this.defaults, ...options }
      });
    },
    
    createBarChart(ctx, data, options = {}) {
      return new Chart(ctx, {
        type: 'bar',
        data,
        options: { 
          ...this.defaults, 
          indexAxis: 'y',
          ...options 
        }
      });
    },
    
    createDoughnutChart(ctx, data, options = {}) {
      return new Chart(ctx, {
        type: 'doughnut',
        data,
        options: {
          ...this.defaults,
          cutout: '60%',
          plugins: {
            ...this.defaults.plugins,
            legend: { position: 'right' }
          },
          ...options
        }
      });
    }
  };
  
  // ========================================
  // MODAL HELPER
  // ========================================
  
  const Modal = {
    open(modalId) {
      const modal = document.getElementById(modalId);
      if (!modal) return;
      
      modal.classList.remove('hidden');
      modal.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      
      // Focus first focusable element
      const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
      
      // Trap focus
      this.trapFocus(modal);
      
      return modal;
    },
    
    close(modalId) {
      const modal = document.getElementById(modalId);
      if (!modal) return;
      
      modal.classList.add('hidden');
      modal.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
    },
    
    trapFocus(modal) {
      const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      
      modal.addEventListener('keydown', function trap(e) {
        if (e.key !== 'Tab') return;
        
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      });
    }
  };
  
  // ========================================
  // INITIALIZATION
  // ========================================
  
  document.addEventListener('DOMContentLoaded', () => {
    // Initialize toast container
    Toast.init();
    
    // Initialize all forms with validation
    document.querySelectorAll('form[data-validate]').forEach(form => {
      const rules = JSON.parse(form.dataset.validate || '{}');
      form.addEventListener('submit', (e) => {
        const { isValid } = FormValidator.validateForm(form, rules);
        if (!isValid) {
          e.preventDefault();
        }
      });
    });
    
    // Add focus-visible polyfill behavior
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        document.body.classList.add('keyboard-nav');
      }
    });
    
    document.addEventListener('mousedown', () => {
      document.body.classList.remove('keyboard-nav');
    });
    
    // Global error handlers
    window.addEventListener('error', (e) => {
      console.error('Global error:', e.error);
    });
    
    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled rejection:', e.reason);
    });
    
    // Expose utilities globally
    window.VAPlatform = {
      Utils,
      Toast,
      FormValidator,
      Api,
      Charts,
      Modal
    };
  });
  
})();