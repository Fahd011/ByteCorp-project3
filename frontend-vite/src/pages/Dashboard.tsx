import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DashboardStats } from "@/components/DashboardStats";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { CredentialUploadDialog } from "@/components/CredentialUploadDialog";
import { credentialsAPI, agentJobsAPI } from "@/services/api";
import { UserBillingCredential, AgentJob } from "@/types";
import { formatDate, formatTime } from "@/utils/dateFormatting";

export default function Dashboard() {
  const [statsOpen, setStatsOpen] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch credentials for stats
  const { data: credentials } = useQuery({
    queryKey: ["credentials"],
    queryFn: async () => {
      const response = await credentialsAPI.getAll();
      return response.data;
    },
  });

  // Fetch agent jobs
  const { data: agentJobs, isLoading } = useQuery({
    queryKey: ["agentJobs"],
    queryFn: async () => {
      const response = await agentJobsAPI.getAll();
      return response.data;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const activeCredentials = credentials?.filter((cred: UserBillingCredential) => !cred.is_deleted) ?? [];

  // Filter jobs based on search
  const filteredJobs = agentJobs?.filter((job: AgentJob) => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      job.provider_name?.toLowerCase().includes(search) ||
      job.username?.toLowerCase().includes(search) ||
      job.status?.toLowerCase().includes(search)
    );
  }) ?? [];

  const getStatusBadge = (status: string) => {
    const statusColors: Record<string, string> = {
      pending: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      running: "bg-blue-500/10 text-blue-500 border-blue-500/20",
      completed: "bg-green-500/10 text-green-500 border-green-500/20",
      failed: "bg-red-500/10 text-red-500 border-red-500/20",
      retrying: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    };
    
    return (
      <Badge variant="outline" className={statusColors[status] || "bg-gray-500/10 text-gray-500"}>
        {status}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-foreground mb-2">Dashboard</h1>
          <p className="text-muted-foreground">Manage your utility providers and billing</p>
        </div>

        {/* Collapsible Stats Section */}
        <Collapsible open={statsOpen} onOpenChange={setStatsOpen} className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-foreground">Overview</h2>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2">
                {statsOpen ? (
                  <>
                    <ChevronUp className="h-4 w-4" />
                    Hide
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-4 w-4" />
                    Show
                  </>
                )}
              </Button>
            </CollapsibleTrigger>
          </div>
          <CollapsibleContent>
            <DashboardStats credentials={activeCredentials} />
          </CollapsibleContent>
        </Collapsible>

        {/* Search and Actions */}
        <div className="flex items-center gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by provider, username, or status..."
              className="pl-10 bg-card border-border"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <CredentialUploadDialog />
        </div>

        {/* Agent Jobs Table */}
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-muted-foreground">
            Showing {filteredJobs.length} of {agentJobs?.length || 0} agent jobs
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredJobs.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              No agent jobs found
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent border-b border-border">
                  <TableHead className="font-medium">Provider</TableHead>
                  <TableHead className="font-medium">Username</TableHead>
                  <TableHead className="font-medium">Status</TableHead>
                  <TableHead className="font-medium">Retries</TableHead>
                  <TableHead className="font-medium">Created</TableHead>
                  <TableHead className="font-medium">Started</TableHead>
                  <TableHead className="font-medium">Completed</TableHead>
                  <TableHead className="font-medium">Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJobs.map((job: AgentJob) => (
                  <TableRow key={job.id} className="hover:bg-muted/50 transition-colors">
                    <TableCell className="font-medium">{job.provider_name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.username || "N/A"}
                    </TableCell>
                    <TableCell>{getStatusBadge(job.status)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.retry_count} / {job.max_retries}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.created_at ? formatDate(job.created_at) : "N/A"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.started_at ? formatTime(job.started_at) : "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {job.completed_at ? formatTime(job.completed_at) : "—"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                      {job.error_message || "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  );
}
