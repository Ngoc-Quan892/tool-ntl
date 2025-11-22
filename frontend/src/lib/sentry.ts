/**
 * Sentry error tracking integration for frontend
 */

let sentryInitialized = false;

/**
 * Initialize Sentry
 */
export function initSentry(dsn?: string, environment: string = 'development'): void {
  if (sentryInitialized || !dsn) {
    return;
  }

  import('@sentry/react').then((Sentry) => {
    Sentry.init({
      dsn,
      environment,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],
      // Performance Monitoring
      tracesSampleRate: environment === 'production' ? 0.1 : 1.0,
      // Session Replay
      replaysSessionSampleRate: environment === 'production' ? 0.1 : 1.0,
      replaysOnErrorSampleRate: 1.0,
      // Release tracking
      release: import.meta.env.VITE_APP_VERSION || '1.0.0',
    });

    sentryInitialized = true;
    console.log('Sentry initialized');
  }).catch((error) => {
    console.warn('Failed to initialize Sentry:', error);
  });
}

/**
 * Capture exception
 */
export async function captureException(
  error: Error,
  context?: Record<string, any>
): Promise<void> {
  if (!sentryInitialized) {
    console.error('Exception (Sentry not initialized):', error);
    return;
  }

  try {
    const Sentry = await import('@sentry/react');
    Sentry.captureException(error, {
      contexts: {
        custom: context,
      },
    });
  } catch (e) {
    console.error('Failed to capture exception:', e);
  }
}

/**
 * Capture message
 */
export async function captureMessage(
  message: string,
  level: 'info' | 'warning' | 'error' = 'info'
): Promise<void> {
  if (!sentryInitialized) {
    return;
  }

  try {
    const Sentry = await import('@sentry/react');
    Sentry.captureMessage(message, level);
  } catch (e) {
    console.error('Failed to capture message:', e);
  }
}

/**
 * Set user context
 */
export async function setUser(userId?: string, email?: string, username?: string): Promise<void> {
  if (!sentryInitialized) {
    return;
  }

  try {
    const Sentry = await import('@sentry/react');
    Sentry.setUser({
      id: userId,
      email,
      username,
    });
  } catch (e) {
    console.error('Failed to set Sentry user:', e);
  }
}

// Auto-initialize from environment
if (import.meta.env.VITE_SENTRY_DSN) {
  initSentry(
    import.meta.env.VITE_SENTRY_DSN,
    import.meta.env.MODE || 'development'
  );
}

