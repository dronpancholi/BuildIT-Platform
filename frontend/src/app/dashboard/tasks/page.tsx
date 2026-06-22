import { redirect } from 'next/navigation';

// Tasks is consolidated under the existing Execution → Action Center surface.
// This page intentionally performs a server-side redirect (no UI) so the
// sidebar entry resolves without a 404 and lands the user on the Tasks tab
// of Action Center. No new business logic, no placeholder content.
export default function TasksRedirect(): never {
  redirect('/dashboard/action-center?tab=task');
}
