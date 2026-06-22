'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronRight } from 'lucide-react';


const SEGMENT_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  executive: 'Executive',
  campaigns: 'Customers',
  keywords: 'Keywords',
  plans: 'Plans',
  approvals: 'Approvals',
  reports: 'Reports',
  recommendations: 'Recommendations',
  'local-seo': 'Local SEO',
  automation: 'Operations',
  settings: 'Settings',
  clients: 'Clients',
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split('/').filter(Boolean);

  const items = segments.map((segment, index) => {
    const href = '/' + segments.slice(0, index + 1).join('/');
    const label = SEGMENT_LABELS[segment] ?? segment;
    const isLast = index === segments.length - 1;

    return { href, label, isLast };
  });

  if (items.length <= 1) return null;

  return (
    <nav className="flex items-center gap-1.5 text-sm">
      {items.map((item, index) => (
        <div key={item.href} className="flex items-center gap-1.5">
          {index > 0 && (
            <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
          )}
          {item.isLast ? (
            <span className="text-slate-200 font-medium">{item.label}</span>
          ) : (
            <Link
              href={item.href}
              className="text-slate-400 hover:text-slate-200 transition-colors"
            >
              {item.label}
            </Link>
          )}
        </div>
      ))}
    </nav>
  );
}
