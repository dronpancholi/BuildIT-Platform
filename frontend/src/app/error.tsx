'use client';
import { useEffect } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[GlobalError]', error);
  }, [error]);

  return (
    <html lang="en" className="dark">
      <body className="flex items-center justify-center min-h-screen bg-[#0a0b0d] text-slate-300">
        <div className="flex flex-col items-center text-center max-w-md px-6">
          <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100 mb-2">Application Error</h1>
          <p className="text-sm text-slate-500 mb-6">
            {error.message || 'A critical error occurred. Please refresh the page.'}
          </p>
          {error.digest && (
            <p className="text-xs text-slate-600 font-mono mb-4">Error ID: {error.digest}</p>
          )}
          <div className="flex gap-3">
            <Button onClick={reset} variant="default" size="sm">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
            <Button onClick={() => (window.location.href = '/dashboard')} variant="outline" size="sm">
              Go to Dashboard
            </Button>
          </div>
        </div>
      </body>
    </html>
  );
}
