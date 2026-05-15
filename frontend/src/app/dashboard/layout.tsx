import { Sidebar } from "@/components/layout/sidebar";
import { HealthIndicator } from "@/components/operational/health-indicator";
import { ApprovalToast } from "@/components/operational/approval-toast";
import { AlertBanner } from "@/components/operational/alert-banner";
import { SSEProvider } from "@/components/operational/sse-provider";
import { OperationalPulse } from "@/components/operational/operational-pulse";
import { LiveEventTicker } from "@/components/operational/live-event-ticker";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SSEProvider>
      <div className="flex min-h-screen bg-surface-darker">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <AlertBanner />
          <LiveEventTicker />
          <header className="h-14 border-b border-surface-border bg-surface-card/50 backdrop-blur-sm sticky top-0 z-10 flex items-center justify-between px-6">
            <div className="flex items-center gap-4">
              <h1 className="text-sm font-medium text-slate-400">Operations Console</h1>
              <OperationalPulse />
            </div>
            <div className="flex items-center gap-4">
              <HealthIndicator />
            </div>
          </header>
          <div className="flex-1 overflow-auto p-6">
            <div className="max-w-6xl mx-auto">
              {children}
            </div>
          </div>
        </main>
        <ApprovalToast />
      </div>
    </SSEProvider>
  );
}
