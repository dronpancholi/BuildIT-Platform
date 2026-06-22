"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Users,
  UserPlus,
  Loader2,
  ChevronDown,
  UserCheck,
  UserX,
} from "lucide-react";
import { userApi, User } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";

const ROLES = ["admin", "manager", "operator", "viewer"] as const;

const ROLE_BADGE: Record<string, "default" | "secondary" | "warning" | "outline"> = {
  admin: "default",
  manager: "secondary",
  operator: "warning",
  viewer: "outline",
};

function RoleBadge({ role }: { role: string }) {
  return (
    <Badge variant={ROLE_BADGE[role] ?? "outline"} className="capitalize">
      {role}
    </Badge>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <Badge variant={active ? "success" : "destructive"}>
      {active ? "Active" : "Inactive"}
    </Badge>
  );
}

export default function UserManagementPage() {
  const queryClient = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");

  const { data: users = [], isLoading } = useQuery<User[]>({
    queryKey: ["users"],
    queryFn: userApi.listUsers,
  });

  const inviteMutation = useMutation({
    mutationFn: userApi.inviteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("User invited");
      setInviteOpen(false);
      setInviteName("");
      setInviteEmail("");
      setInviteRole("viewer");
    },
    onError: (e: Error) => toast.error("Invite failed", { description: e.message }),
  });

  const toggleActiveMutation = useMutation({
    mutationFn: (user: User) =>
      user.is_active ? userApi.deactivateUser(user.id) : userApi.activateUser(user.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("User updated");
    },
    onError: (e: Error) => toast.error("Update failed", { description: e.message }),
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      userApi.updateUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Role updated");
    },
    onError: (e: Error) => toast.error("Update failed", { description: e.message }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">User Management</h1>
          <p className="text-slate-400 mt-1">Manage team members and their roles.</p>
        </div>
        <button
          onClick={() => setInviteOpen(true)}
          className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-sm font-medium transition-all shadow-lg shadow-platform-900/20 flex items-center gap-2"
        >
          <UserPlus className="w-4 h-4" />
          Invite User
        </button>
      </div>

      <div className="glass-panel overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-platform-400" />
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500">
            <Users className="w-10 h-10 mb-3 opacity-40" />
            <p className="text-sm">No users found.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border">
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Email</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Role</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                <th className="text-right px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-surface-darker/50 transition-colors">
                  <td className="px-6 py-4 text-slate-200 font-medium">{user.name}</td>
                  <td className="px-6 py-4 text-slate-400">{user.email}</td>
                  <td className="px-6 py-4">
                    <div className="relative inline-block">
                      <select
                        value={user.role}
                        onChange={(e) =>
                          roleMutation.mutate({ userId: user.id, role: e.target.value })
                        }
                        className="appearance-none bg-transparent border border-surface-border rounded-md px-2 py-1 pr-7 text-xs text-slate-300 focus:outline-none focus:border-platform-500/50 cursor-pointer"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r} className="bg-surface-darker capitalize">
                            {r.charAt(0).toUpperCase() + r.slice(1)}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500 pointer-events-none" />
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge active={user.is_active} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => toggleActiveMutation.mutate(user)}
                      disabled={toggleActiveMutation.isPending}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                        user.is_active
                          ? "text-red-400 hover:bg-red-500/10"
                          : "text-emerald-400 hover:bg-emerald-500/10"
                      }`}
                    >
                      {user.is_active ? (
                        <>
                          <UserX className="w-3.5 h-3.5" />
                          Deactivate
                        </>
                      ) : (
                        <>
                          <UserCheck className="w-3.5 h-3.5" />
                          Reactivate
                        </>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Invite Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite User</DialogTitle>
            <DialogDescription>
              Send an invitation to a new team member.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Name</label>
              <input
                type="text"
                value={inviteName}
                onChange={(e) => setInviteName(e.target.value)}
                placeholder="Full name"
                className="w-full bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-platform-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="user@example.com"
                className="w-full bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-platform-500/50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Role</label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full appearance-none bg-surface-darker border border-surface-border rounded-md py-2 px-3 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r} className="bg-surface-darker capitalize">
                    {r.charAt(0).toUpperCase() + r.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <button
              onClick={() => setInviteOpen(false)}
              className="px-4 py-2 rounded-md text-sm font-medium text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => inviteMutation.mutate({ name: inviteName, email: inviteEmail, role: inviteRole })}
              disabled={!inviteName || !inviteEmail || inviteMutation.isPending}
              className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-sm font-medium transition-all flex items-center gap-2 disabled:opacity-60"
            >
              {inviteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Send Invite
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
