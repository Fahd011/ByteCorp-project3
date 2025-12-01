import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, FileText, FileSpreadsheet, FileJson, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { credentialsAPI } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { getStatusBadge } from "@/utils/statusBadge";
import { formatDate, formatBillingMonth } from "@/utils/dateFormatting";
import { extractFilename } from "@/utils/filenameExtraction";
import { extractErrorMessage } from "@/utils/errorHandling";
import { getDefaultProviderFull } from "@/utils/defaultValues";
import { EmptyState } from "@/components/EmptyState";

interface BillingResult {
  id: string;
  azure_blob_url: string;
  excel_blob_url?: string | null;
  json_blob_url?: string | null;
  run_time: string;
  status: string;
  year: string;
  month: string;
  created_at: string;
  username: string;
}

export default function BillingResults() {
  const { credId } = useParams<{ credId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  // Fetch billing results
  const { data: billingResults, isLoading, error } = useQuery({
    queryKey: ["billing-results", credId],
    queryFn: async () => {
      if (!credId) throw new Error("Credential ID is required");
      const response = await credentialsAPI.getBillingResults(credId);
      return response.data as BillingResult[];
    },
    enabled: !!credId,
  });

  // Fetch credential to get provider name
  const { data: credentials } = useQuery({
    queryKey: ["credentials"],
    queryFn: async () => {
      const response = await credentialsAPI.getAll();
      return response.data;
    },
  });

  const credential = credentials?.find((c: any) => c.id === credId);
  const providerName = credential?.utility_co_name ?? getDefaultProviderFull();

  const handleDownload = async (type: "pdf" | "excel" | "json", blobName: string) => {
    try {
      let response;
      if (type === "pdf") {
        response = await credentialsAPI.downloadPDF(blobName);
      } else if (type === "excel") {
        response = await credentialsAPI.downloadExcel(blobName);
      } else if (type === "json") {
        response = await credentialsAPI.downloadJSON(blobName);
      } else {
        throw new Error("Invalid download type");
      }

      const blob = new Blob([response.data], {
        type: type === "pdf" ? "application/pdf" : type === "excel" ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" : "application/json",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const extension = type === "pdf" ? "pdf" : type === "excel" ? "xlsx" : "json";
      const extractedFilename = extractFilename(blobName);
      a.download = extractedFilename.endsWith(`.${extension}`) ? extractedFilename : `${extractedFilename}.${extension}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: "Download started",
        description: `Downloading ${type.toUpperCase()} file`,
      });
    } catch (error: unknown) {
      toast({
        title: "Download failed",
        description: extractErrorMessage(error, "Failed to download file"),
        variant: "destructive",
      });
    }
  };


  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-destructive mb-4">Failed to load billing results</p>
          <Button onClick={() => navigate("/dashboard")}>Go Back to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate("/dashboard")}
            className="mb-4 gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-semibold text-foreground mb-2">Billing Results</h1>
          <p className="text-muted-foreground">
            Provider: <span className="font-medium">{providerName}</span>
            {credential?.email && (
              <> • Account: <span className="font-medium">{credential.email}</span></>
            )}
          </p>
        </div>

        {/* Table */}
        <div className="rounded-lg border border-border bg-card overflow-hidden shadow-sm">
          {!billingResults || billingResults.length === 0 ? (
            <EmptyState
              title="No billing results found"
              description="No billing results found for this credential"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent border-b border-border">
                  <TableHead className="font-medium">Date</TableHead>
                  <TableHead className="font-medium">Month/Year</TableHead>
                  <TableHead className="font-medium">Status</TableHead>
                  <TableHead className="font-medium">Username</TableHead>
                  <TableHead className="text-right font-medium">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {billingResults.map((result) => (
                  <TableRow key={result.id} className="hover:bg-muted/50 transition-colors">
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(result.run_time)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatBillingMonth(result.month, result.year)}
                    </TableCell>
                    <TableCell>{getStatusBadge(result.status)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {result.username}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {result.excel_blob_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-success hover:text-success hover:bg-success/10"
                            onClick={() => handleDownload("excel", result.excel_blob_url!)}
                            title="Download Excel"
                          >
                            <FileSpreadsheet className="h-4 w-4" />
                          </Button>
                        )}
                        {result.json_blob_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-primary hover:text-primary hover:bg-primary/10"
                            onClick={() => handleDownload("json", result.json_blob_url!)}
                            title="Download JSON"
                          >
                            <FileJson className="h-4 w-4" />
                          </Button>
                        )}
                        {result.azure_blob_url && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleDownload("pdf", result.azure_blob_url)}
                            title="Download PDF"
                          >
                            <FileText className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
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

