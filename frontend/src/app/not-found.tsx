import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-[#0a0b0d] text-slate-300">
      <div className="flex flex-col items-center text-center max-w-md px-6">
        <h1 className="text-7xl font-bold text-platform-500 mb-4">404</h1>
        <h2 className="text-xl font-semibold text-slate-100 mb-2">Page Not Found</h2>
        <p className="text-sm text-slate-500 mb-6">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link href="/dashboard">
          <Button variant="default" size="sm">
            Back to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
