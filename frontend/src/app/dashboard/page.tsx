"use client";

/**
 * Dashboard landing page — replaced with Operator Command Center
 * as part of Phase 1.2. The previous 1023-line page is preserved
 * as page.tsx.bak and can be restored.
 *
 * Sub-routes (campaigns, approvals, providers, etc.) are unchanged.
 */

import { OperatorCommandCenter } from "@/components/operator/operator-command-center";

export default function DashboardPage() {
  return <OperatorCommandCenter />;
}
