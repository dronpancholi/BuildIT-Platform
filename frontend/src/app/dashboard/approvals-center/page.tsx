import { redirect, RedirectType } from "next/navigation";

export default function ApprovalsCenterPage() {
  redirect("/dashboard/approvals", RedirectType.replace);
}
