import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ArrowUpDown, ExternalLink, Trash2, Eye, ChevronRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { credentialsAPI } from "@/services/api";
import { UserBillingCredential } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { getStatusBadge } from "@/utils/statusBadge";
import { extractErrorMessage } from "@/utils/errorHandling";
import { DEFAULT_VALUES } from "@/utils/defaultValues";
import { EmptyState } from "@/components/EmptyState";

type Provider = {
  id: string;
  email: string;
  provider: string;
  utilityType: "Electricity" | "Gas" | "Water" | "Waste/Trash";
  status: "idle" | "active" | "failed" | "completed";
  billCycle: string;
  daysUntil: number;
  loginUrl: string | null;
  credential?: UserBillingCredential;
};

const utilityTypes = ["Electricity", "Gas", "Water", "Waste/Trash"] as const;

interface ProvidersTableProps {
  readonly searchTerm?: string;
}

export function ProvidersTable({ searchTerm = "" }: ProvidersTableProps) {
  const navigate = useNavigate();
  const [sortField, setSortField] = useState<keyof Provider>("daysUntil");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [activeTab, setActiveTab] = useState<"all" | "idle" | "active" | "failed" | "completed">("all");
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [selectedUtilityTypes, setSelectedUtilityTypes] = useState<string[]>([]);
  const [showAllProviders, setShowAllProviders] = useState(false);
  const { toast } = useToast();

  // Fetch credentials from API
  const { data: credentials, isLoading, error } = useQuery({
    queryKey: ["credentials"],
    queryFn: async () => {
      const response = await credentialsAPI.getAll();
      return response.data;
    },
  });

  // Note: Providers are fetched but not directly used in this component
  // They are available via the credentials' utility_co_name field

  // Transform backend data to frontend format
  const transformedProviders = useMemo(() => {
    if (!credentials) return [];
    
    return credentials
      .filter((cred: UserBillingCredential) => !cred.is_deleted)
      .map((cred: UserBillingCredential) => {
        // Map backend status to frontend status
        const statusMap: Record<string, "idle" | "active" | "failed" | "completed"> = {
          idle: "idle",
          running: "active",
          error: "failed",
          completed: "completed",
        };
        
        const status = statusMap[cred.last_state?.toLowerCase() || "idle"] || "idle";
        
        // Calculate days until next billing cycle
        let daysUntil = 0;
        let billCycle = "N/A";
        if (cred.billing_cycle_day) {
          const today = new Date();
          const currentDay = today.getDate();
          const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
          
          if (currentDay <= cred.billing_cycle_day) {
            daysUntil = cred.billing_cycle_day - currentDay;
          } else {
            daysUntil = daysInMonth - currentDay + cred.billing_cycle_day;
          }
          
          // Format bill cycle text
          let billCycleText: string;
          if (daysUntil === 0) {
            billCycleText = "Today";
          } else if (daysUntil === 1) {
            billCycleText = "1 day";
          } else {
            billCycleText = `${daysUntil} days`;
          }
          billCycle = billCycleText;
        }
        
        // Determine utility type (default to Electricity)
        const utilityName = cred.utility_co_name?.toLowerCase() ?? "";
        let utilityType: "Electricity" | "Gas" | "Water" | "Waste/Trash";
        if (utilityName.includes("gas")) {
          utilityType = "Gas";
        } else if (utilityName.includes("water")) {
          utilityType = "Water";
        } else if (utilityName.includes("waste") || utilityName.includes("trash")) {
          utilityType = "Waste/Trash";
        } else {
          utilityType = "Electricity";
        }
        
        return {
          id: cred.id,
          email: cred.email,
          provider: cred.utility_co_name ?? DEFAULT_VALUES.PROVIDER,
          utilityType,
          status,
          billCycle,
          daysUntil,
          loginUrl: cred.login_url || null,
          credential: cred, // Keep original for actions
        };
      });
  }, [credentials]);

  // Get unique providers list
  const allProviders = useMemo(() => {
    if (!transformedProviders) return [];
    const unique = new Set(transformedProviders.map(p => p.provider));
    return Array.from(unique).sort((a, b) => a.localeCompare(b));
  }, [transformedProviders]);

  const handleSort = (field: keyof Provider) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const toggleProvider = (provider: string) => {
    setSelectedProviders(prev => 
      prev.includes(provider) 
        ? prev.filter(p => p !== provider)
        : [...prev, provider]
    );
  };

  const toggleUtilityType = (type: string) => {
    setSelectedUtilityTypes(prev => 
      prev.includes(type) 
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const handleDelete = async (credId: string) => {
    try {
      await credentialsAPI.delete(credId);
      toast({
        title: "Success",
        description: "Credential deleted successfully",
      });
      // Query will refetch automatically
    } catch (error) {
      toast({
        title: "Error",
        description: extractErrorMessage(error, "Failed to delete credential"),
        variant: "destructive",
      });
    }
  };

  const DeleteConfirmationDialog = ({ credId, providerName }: { credId: string; providerName: string }) => {
    const [isDeleting, setIsDeleting] = useState(false);
    
    const onConfirmDelete = async () => {
      setIsDeleting(true);
      await handleDelete(credId);
      setIsDeleting(false);
    };

    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10">
            <Trash2 className="h-4 w-4" />
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Credential</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the credential for <strong>{providerName}</strong>? This action is irreversible and will permanently remove this credential.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={onConfirmDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  };

  const filteredProviders = transformedProviders.filter((provider) => {
    // Status filter
    if (activeTab !== "all" && provider.status !== activeTab) return false;
    
    // Provider filter
    if (selectedProviders.length > 0 && !selectedProviders.includes(provider.provider)) return false;
    
    // Utility type filter
    if (selectedUtilityTypes.length > 0 && !selectedUtilityTypes.includes(provider.utilityType)) return false;
    
    // Search filter
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      const matchesEmail = provider.email.toLowerCase().includes(searchLower);
      const matchesProvider = provider.provider.toLowerCase().includes(searchLower);
      const matchesClientName = provider.credential?.client_name?.toLowerCase().includes(searchLower);
      const matchesCredId = provider.credential?.cred_id?.toLowerCase().includes(searchLower);
      
      if (!matchesEmail && !matchesProvider && !matchesClientName && !matchesCredId) {
        return false;
      }
    }
    
    return true;
  });

  const sortedProviders = [...filteredProviders].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    const modifier = sortDirection === "asc" ? 1 : -1;
    
    if (typeof aValue === "string" && typeof bValue === "string") {
      return aValue.localeCompare(bValue) * modifier;
    }
    return ((aValue as number) - (bValue as number)) * modifier;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12 text-destructive">
        Failed to load credentials. Please try again.
      </div>
    );
  }


  const displayedProviders = showAllProviders ? allProviders : allProviders.slice(0, 5);
  
  const handleViewBills = (credId: string) => {
    // Navigate to billing results page
    navigate(`/billing-results/${credId}`);
  };

  const handleLoginPortal = (loginUrl: string | null) => {
    if (loginUrl) {
      window.open(loginUrl, '_blank', 'noopener,noreferrer');
    } else {
      toast({
        title: "Login URL not available",
        description: "No login URL found for this provider",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Filter Chips - Providers */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          {displayedProviders.map((provider) => (
            <button
              key={provider}
              onClick={() => toggleProvider(provider)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                selectedProviders.includes(provider)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {provider}
            </button>
          ))}
          {allProviders.length > 5 && (
            <button
              onClick={() => setShowAllProviders(!showAllProviders)}
              className="px-3 py-1.5 rounded-full text-xs font-medium transition-all border bg-muted text-muted-foreground border-border hover:border-primary/50 hover:text-foreground flex items-center gap-1"
            >
              {showAllProviders ? "Show Less" : `Show More (${allProviders.length - 5})`}
              <ChevronRight className={`h-3 w-3 transition-transform ${showAllProviders ? "rotate-90" : ""}`} />
            </button>
          )}
        </div>

        {/* Filter Chips - Utility Types */}
        <div className="flex items-center gap-2 flex-wrap">
          {utilityTypes.map((type) => (
            <button
              key={type}
              onClick={() => toggleUtilityType(type)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                selectedUtilityTypes.includes(type)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border">
        {[
          { key: "all", label: "All Providers" },
          { key: "idle", label: "Idle" },
          { key: "active", label: "Active" },
          { key: "completed", label: "Completed" },
          { key: "failed", label: "Failed" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as typeof activeTab)}
            className={`px-4 py-3 text-sm font-medium transition-colors relative ${
              activeTab === tab.key
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
            {activeTab === tab.key && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-b border-border">
              <TableHead className="w-12"></TableHead>
              <TableHead>
                <button
                  onClick={() => handleSort("email")}
                  className="flex items-center gap-2 hover:text-foreground transition-colors font-medium"
                >
                  Account Email
                  <ArrowUpDown className="h-4 w-4" />
                </button>
              </TableHead>
              <TableHead>
                <button
                  onClick={() => handleSort("provider")}
                  className="flex items-center gap-2 hover:text-foreground transition-colors font-medium"
                >
                  Provider
                  <ArrowUpDown className="h-4 w-4" />
                </button>
              </TableHead>
              <TableHead>
                <button
                  onClick={() => handleSort("status")}
                  className="flex items-center gap-2 hover:text-foreground transition-colors font-medium"
                >
                  Status
                  <ArrowUpDown className="h-4 w-4" />
                </button>
              </TableHead>
              <TableHead>
                <button
                  onClick={() => handleSort("daysUntil")}
                  className="flex items-center gap-2 hover:text-foreground transition-colors font-medium"
                >
                  Bill Cycle
                  <ArrowUpDown className="h-4 w-4" />
                </button>
              </TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedProviders.length > 0 ? (
              sortedProviders.map((provider) => (
                <TableRow key={provider.id} className="hover:bg-muted/50 transition-colors">
                  <TableCell>
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                        {provider.provider.slice(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                  </TableCell>
                  <TableCell className="font-medium text-sm">{provider.email}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-warning/10 text-warning text-xs font-medium">
                        ⚡ {provider.provider}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(provider.status)}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    Your bill cycle runs in {provider.billCycle}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 px-3"
                        onClick={() => handleLoginPortal(provider.loginUrl)}
                        disabled={!provider.loginUrl}
                      >
                        <ExternalLink className="h-4 w-4 mr-1" />
                        Login Portal
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 px-3"
                        onClick={() => handleViewBills(provider.credential?.id || provider.id)}
                      >
                        <Eye className="h-4 w-4 mr-1" />
                        View Bills
                      </Button>
                      <DeleteConfirmationDialog 
                        credId={provider.credential?.id || provider.id}
                        providerName={provider.provider}
                      />
                    </div>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6}>
                  <EmptyState
                    title="No providers found"
                    description="Add a credential to get started"
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
