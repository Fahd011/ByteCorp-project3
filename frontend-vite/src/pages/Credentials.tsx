import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { ProvidersTable } from "@/components/ProvidersTable";
import { CredentialUploadDialog } from "@/components/CredentialUploadDialog";
import { credentialsAPI } from "@/services/api";
import { UserBillingCredential } from "@/types";

export default function Credentials() {
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch credentials to get count
  const { data: credentials } = useQuery({
    queryKey: ["credentials"],
    queryFn: async () => {
      const response = await credentialsAPI.getAll();
      return response.data;
    },
  });

  const activeCredentials = credentials?.filter((cred: UserBillingCredential) => !cred.is_deleted) ?? [];
  // Count unique providers (by utility_co_name)
  const uniqueProviders = new Set(
    activeCredentials
      .filter((cred: UserBillingCredential) => cred.utility_co_name)
      .map((cred: UserBillingCredential) => cred.utility_co_name)
  );
  const providerCount = uniqueProviders.size;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-foreground mb-2">Credentials</h1>
          <p className="text-muted-foreground">Manage your credentials and providers</p>
        </div>

        {/* Search and Actions */}
        <div className="flex items-center gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search providers, clients, or account numbers..."
              className="pl-10 bg-card border-border"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <CredentialUploadDialog />
        </div>

        {/* Providers Table */}
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-muted-foreground">
            Showing {providerCount} of {providerCount} providers
          </div>
        </div>

        <ProvidersTable searchTerm={searchTerm} showTabs={false} />
      </div>
    </div>
  );
}

