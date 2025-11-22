/**
 * Analytics integration
 * Supports Google Analytics, Plausible, và custom analytics
 */

// Google Analytics
declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
    dataLayer?: any[];
    plausible?: (event: string, options?: { props?: Record<string, any> }) => void;
  }
}

export interface AnalyticsConfig {
  googleAnalyticsId?: string;
  plausibleDomain?: string;
  enabled: boolean;
}

let analyticsConfig: AnalyticsConfig = {
  enabled: false,
};

/**
 * Initialize analytics
 */
export function initAnalytics(config: AnalyticsConfig): void {
  analyticsConfig = { ...analyticsConfig, ...config };

  if (!analyticsConfig.enabled) {
    return;
  }

  // Google Analytics
  if (analyticsConfig.googleAnalyticsId) {
    initGoogleAnalytics(analyticsConfig.googleAnalyticsId);
  }

  // Plausible
  if (analyticsConfig.plausibleDomain) {
    initPlausible(analyticsConfig.plausibleDomain);
  }
}

/**
 * Initialize Google Analytics
 */
function initGoogleAnalytics(gaId: string): void {
  // Load gtag script
  const script1 = document.createElement('script');
  script1.async = true;
  script1.src = `https://www.googletagmanager.com/gtag/js?id=${gaId}`;
  document.head.appendChild(script1);

  // Initialize dataLayer
  window.dataLayer = window.dataLayer || [];
  window.gtag = function(...args: any[]) {
    window.dataLayer.push(args);
  };

  window.gtag('js', new Date());
  window.gtag('config', gaId, {
    page_path: window.location.pathname,
  });
}

/**
 * Initialize Plausible
 */
function initPlausible(domain: string): void {
  const script = document.createElement('script');
  script.defer = true;
  script['data-domain'] = domain;
  script.src = 'https://plausible.io/js/script.js';
  document.head.appendChild(script);
}

/**
 * Track page view
 */
export function trackPageView(path: string): void {
  if (!analyticsConfig.enabled) return;

  // Google Analytics
  if (window.gtag) {
    window.gtag('config', analyticsConfig.googleAnalyticsId, {
      page_path: path,
    });
  }

  // Plausible
  if (window.plausible) {
    window.plausible('pageview', {
      props: { path },
    });
  }
}

/**
 * Track event
 */
export function trackEvent(
  eventName: string,
  category?: string,
  label?: string,
  value?: number
): void {
  if (!analyticsConfig.enabled) return;

  // Google Analytics
  if (window.gtag) {
    window.gtag('event', eventName, {
      event_category: category,
      event_label: label,
      value: value,
    });
  }

  // Plausible
  if (window.plausible) {
    window.plausible(eventName, {
      props: {
        category,
        label,
        value,
      },
    });
  }
}

/**
 * Track custom event
 */
export function trackCustomEvent(
  eventName: string,
  properties?: Record<string, any>
): void {
  if (!analyticsConfig.enabled) return;

  // Google Analytics
  if (window.gtag) {
    window.gtag('event', eventName, properties);
  }

  // Plausible
  if (window.plausible) {
    window.plausible(eventName, {
      props: properties,
    });
  }
}

/**
 * Track error
 */
export function trackError(error: Error, context?: Record<string, any>): void {
  if (!analyticsConfig.enabled) return;

  trackEvent('error', 'exception', error.message, 1);

  // Google Analytics
  if (window.gtag) {
    window.gtag('event', 'exception', {
      description: error.message,
      fatal: false,
      ...context,
    });
  }
}

// Auto-initialize from environment
if (import.meta.env.VITE_ANALYTICS_ENABLED === 'true') {
  initAnalytics({
    enabled: true,
    googleAnalyticsId: import.meta.env.VITE_GA_ID,
    plausibleDomain: import.meta.env.VITE_PLAUSIBLE_DOMAIN,
  });
}

