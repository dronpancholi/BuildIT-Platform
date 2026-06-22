"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";
import { Search, Users, ChevronDown, ArrowLeft } from "lucide-react";
import { safeArr, safeLower } from "@/lib/safe";

interface Client {
  id: string;
  name: string;
  domain: string;
  niche: string | null;
  business_type: string | null;
}

export function CustomerSwitcher() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: clients = [] } = useQuery<Client[]>({
    queryKey: ["clients"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/clients?tenant_id=${tenantId}`);
      return response?.data || [];
    },
  });

  const filteredClients = safeArr<Client>(clients).filter(client =>
    safeLower(client.name, "").includes(safeLower(searchQuery, "")) ||
    safeLower(client.domain, "").includes(safeLower(searchQuery, ""))
  );

  const handleSelectClient = (clientId: string) => {
    router.push(`/dashboard/customers/${clientId}`);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border rounded-lg transition-colors"
      >
        <Users className="w-4 h-4 text-platform-400" />
        <span className="text-sm font-mono text-slate-300 max-w-[150px] truncate">
          {clients.length > 0 ? `${clients.length} Customers` : "No Customers"}
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-2 w-80 max-h-96 overflow-hidden bg-slate-800 border border-surface-border rounded-lg shadow-xl z-50">
            {/* Search */}
            <div className="p-3 border-b border-surface-border">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search customers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
                />
              </div>
            </div>

            {/* Customer List */}
            <div className="overflow-y-auto max-h-80">
              {filteredClients.length === 0 ? (
                <div className="p-4 text-center">
                  <Users className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                  <p className="text-xs font-mono text-slate-500">
                    {searchQuery ? "No customers found" : "No customers yet"}
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-surface-border">
                  {filteredClients.map((client) => (
                    <button
                      key={client.id}
                      onClick={() => handleSelectClient(client.id)}
                      className="w-full p-3 hover:bg-surface-border transition-colors text-left"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-sm flex-shrink-0">
                          {client.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-bold font-mono text-slate-200 truncate">
                              {client.name}
                            </h4>
                          </div>
                          <p className="text-[10px] font-mono text-slate-500 truncate">
                            {client.domain}
                          </p>
                          {client.niche && (
                            <p className="text-[10px] font-mono text-platform-500 truncate">
                              {client.niche}
                            </p>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-surface-border bg-slate-900">
              <button
                onClick={() => router.push("/dashboard")}
                className="w-full px-3 py-2 text-xs font-mono text-slate-400 hover:text-slate-300 flex items-center justify-center gap-2 transition-colors"
              >
                <ArrowLeft className="w-3 h-3" />
                Back to Dashboard
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}