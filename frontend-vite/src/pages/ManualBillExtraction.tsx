import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Upload, X, FileText, ChevronRight, ExternalLink, FileJson, FileSpreadsheet, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { manualBillsAPI, providerAPI } from "@/services/api";
import { ManualBill } from "@/types";
import { getStatusBadge } from "@/utils/statusBadge";
import { formatDate, formatBillingMonth } from "@/utils/dateFormatting";
import { extractFilename } from "@/utils/filenameExtraction";
import { extractErrorMessage } from "@/utils/errorHandling";
import { DEFAULT_VALUES } from "@/utils/defaultValues";
import { EmptyState } from "@/components/EmptyState";

type UploadedBill = {
  id: string;
  filename: string;
  provider: string;
  uploadDate: string;
  status: "processing" | "completed" | "failed";
  billingMonth: string;
  loginUrl: string | null;
  originalData?: ManualBill;
};

export default function ManualBillExtraction() {
  const [searchQuery, setSearchQuery] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [selectedProviderFilters, setSelectedProviderFilters] = useState<string[]>([]);
  const [selectedStatusFilters, setSelectedStatusFilters] = useState<string[]>([]);
  const [showAllProviders, setShowAllProviders] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch manual bills from API
  const { data: manualBills, isLoading, error } = useQuery({
    queryKey: ["manual-bills"],
    queryFn: async () => {
      const response = await manualBillsAPI.getAll();
      return response.data;
    },
  });

  // Fetch providers from API
  const { data: providers } = useQuery({
    queryKey: ["providers"],
    queryFn: async () => {
      const response = await providerAPI.getAll();
      return response.data;
    },
  });

  // Transform backend data to frontend format
  const uploadedBills = useMemo(() => {
    if (!manualBills) return [];
    
    return manualBills.map((bill: ManualBill) => ({
      id: bill.id,
      filename: bill.original_filename ?? DEFAULT_VALUES.FILENAME,
      provider: bill.provider_name ?? DEFAULT_VALUES.PROVIDER,
      uploadDate: bill.created_at,
      status: bill.status?.toLowerCase() === "completed" ? "completed" as const :
              bill.status?.toLowerCase() === "processing" ? "processing" as const :
              bill.status?.toLowerCase() === "failed" ? "failed" as const :
              "processing" as const,
      billingMonth: formatBillingMonth(bill.month, bill.year),
      loginUrl: bill.login_url ?? null,
      originalData: bill,
    }));
  }, [manualBills]);

  // Get unique providers list
  const allProviders = useMemo(() => {
    if (!providers) return [];
    return providers.map((p: any) => p.name).sort((a, b) => a.localeCompare(b));
  }, [providers]);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: async ({ files, providerId }: { files: FileList; providerId: string }) => {
      const formData = new FormData();
      Array.from(files).forEach((file) => {
        formData.append("files", file);
      });
      formData.append("provider_id", providerId);
      
      if (files.length === 1) {
        return await manualBillsAPI.upload(formData);
      } else {
        return await manualBillsAPI.bulkUpload(formData);
      }
    },
    onSuccess: () => {
      toast({
        title: "Upload started",
        description: "Your bill(s) are being processed",
      });
      setIsDialogOpen(false);
      setSelectedFiles(null);
      setSelectedProvider("");
      queryClient.invalidateQueries({ queryKey: ["manual-bills"] });
    },
    onError: (error: unknown) => {
      toast({
        title: "Upload failed",
        description: extractErrorMessage(error, "Failed to upload bills"),
        variant: "destructive",
      });
    },
  });

  const toggleProviderFilter = (provider: string) => {
    setSelectedProviderFilters(prev => 
      prev.includes(provider) 
        ? prev.filter(p => p !== provider)
        : [...prev, provider]
    );
  };

  const toggleStatusFilter = (status: string) => {
    setSelectedStatusFilters(prev => 
      prev.includes(status) 
        ? prev.filter(s => s !== status)
        : [...prev, status]
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    // Validate number of files
    if (files.length > 10) {
      toast({
        title: "Too many files",
        description: "You can only upload up to 10 files at a time.",
        variant: "destructive",
      });
      return;
    }

    // Validate file sizes (15MB = 15 * 1024 * 1024 bytes)
    const maxSize = 15 * 1024 * 1024;
    for (let i = 0; i < files.length; i++) {
      if (files[i].size > maxSize) {
        toast({
          title: "File too large",
          description: `${files[i].name} exceeds the 15MB limit.`,
          variant: "destructive",
        });
        return;
      }
    }

    setSelectedFiles(files);
  };

  const handleUpload = () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      toast({
        title: "No files selected",
        description: "Please select at least one file to upload.",
        variant: "destructive",
      });
      return;
    }

    if (!selectedProvider) {
      toast({
        title: "Provider required",
        description: "Please select a provider.",
        variant: "destructive",
      });
      return;
    }

    // Find provider ID from name
    const provider = providers?.find((p: any) => p.name === selectedProvider);
    if (!provider) {
      toast({
        title: "Provider not found",
        description: "Please select a valid provider.",
        variant: "destructive",
      });
      return;
    }

    uploadMutation.mutate({ files: selectedFiles, providerId: provider.id });
  };

  // Helper function to create and trigger download
  const triggerDownload = (blob: Blob, filename: string, extension: string) => {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename.endsWith(`.${extension}`) ? filename : `${filename}.${extension}`;
    document.body.appendChild(link);
    link.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(link);
  };

  // Download configuration mapping
  const downloadConfig = {
    json: {
      blobUrlKey: "json_blob_url" as const,
      downloadFn: manualBillsAPI.downloadJSON,
      mimeType: "application/json",
      extension: "json",
    },
    excel: {
      blobUrlKey: "excel_blob_url" as const,
      downloadFn: manualBillsAPI.downloadExcel,
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      extension: "xlsx",
    },
    pdf: {
      blobUrlKey: "azure_blob_url" as const,
      downloadFn: manualBillsAPI.downloadPDF,
      mimeType: "application/pdf",
      extension: "pdf",
    },
  } as const;

  const handleDownload = async (type: "json" | "excel" | "pdf", bill: UploadedBill) => {
    if (!bill.originalData) return;
    
    const config = downloadConfig[type];
    const blobUrl = bill.originalData[config.blobUrlKey];
    
    if (!blobUrl) {
      toast({
        title: "File not available",
        description: `${type.toUpperCase()} file is not available for this bill`,
        variant: "destructive",
      });
      return;
    }

    try {
      const response = await config.downloadFn(blobUrl);
      const blob = new Blob([response.data], { type: config.mimeType });
      const filename = extractFilename(blobUrl, bill.filename);
      
      triggerDownload(blob, filename, config.extension);
      
      toast({
        title: "Download started",
        description: `Downloading ${type.toUpperCase()} file...`,
      });
    } catch (error: unknown) {
      toast({
        title: "Download failed",
        description: extractErrorMessage(error, "Failed to download file"),
        variant: "destructive",
      });
    }
  };

  const filteredBills = uploadedBills.filter((bill) => {
    // Search filter
    const matchesSearch = bill.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      bill.provider.toLowerCase().includes(searchQuery.toLowerCase());
    
    // Provider filter
    const matchesProvider = selectedProviderFilters.length === 0 || 
      selectedProviderFilters.includes(bill.provider);
    
    // Status filter
    const matchesStatus = selectedStatusFilters.length === 0 || 
      selectedStatusFilters.includes(bill.status);
    
    return matchesSearch && matchesProvider && matchesStatus;
  });


  const displayedProviders = showAllProviders ? allProviders : allProviders.slice(0, 5);
  const statusOptions = ["processing", "completed", "failed"];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold text-foreground">Manual Bill Extraction</h1>
        <p className="text-muted-foreground">Upload bills manually for automatic data extraction</p>
      </div>

      {/* Filter Chips */}
      <div className="space-y-3">
        {/* Provider Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {displayedProviders.map((provider) => (
            <button
              key={provider}
              onClick={() => toggleProviderFilter(provider)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                selectedProviderFilters.includes(provider)
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

        {/* Status Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {statusOptions.map((status) => (
            <button
              key={status}
              onClick={() => toggleStatusFilter(status)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                selectedStatusFilters.includes(status)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-card text-muted-foreground border-border hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Search and Upload Section */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by filename or provider..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Upload className="h-4 w-4" />
              Upload Bill
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle>Upload Bill</DialogTitle>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {/* File Input */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">PDF File(s)</label>
                <div className="flex items-center gap-2">
                  <Input
                    type="file"
                    accept=".pdf"
                    multiple
                    onChange={handleFileChange}
                    className="flex-1"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Max 10 files, 15MB per file
                </p>
                {selectedFiles && selectedFiles.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {Array.from(selectedFiles).map((file, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <FileText className="h-4 w-4" />
                        <span className="truncate">{file.name}</span>
                        <span className="text-xs">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Provider Select */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-foreground">Provider</label>
                <Select value={selectedProvider} onValueChange={setSelectedProvider}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a provider..." />
                  </SelectTrigger>
                  <SelectContent className="max-h-[300px]">
                    {allProviders.length > 0 ? (
                      allProviders.map((provider: string) => (
                        <SelectItem key={provider} value={provider}>
                          {provider}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="loading" disabled>Loading providers...</SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setIsDialogOpen(false);
                  setSelectedFiles(null);
                  setSelectedProvider("");
                }}
              >
                Cancel
              </Button>
              <Button 
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  "Upload Bill"
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border bg-card overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-12 text-destructive">
            Failed to load bills. Please try again.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent border-b border-border">
                <TableHead className="font-medium">Filename</TableHead>
                <TableHead className="font-medium">Provider</TableHead>
                <TableHead className="font-medium">Upload Date</TableHead>
                <TableHead className="font-medium">Status</TableHead>
                <TableHead className="font-medium">Billing Month</TableHead>
                <TableHead className="text-right font-medium">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredBills.length > 0 ? (
              filteredBills.map((bill) => (
                <TableRow key={bill.id} className="hover:bg-muted/50 transition-colors">
                  <TableCell className="font-medium text-sm">{bill.filename}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-warning/10 text-warning text-xs font-medium">
                      ⚡ {bill.provider}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(bill.uploadDate)}
                  </TableCell>
                  <TableCell>{getStatusBadge(bill.status)}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{bill.billingMonth}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      {bill.status === "completed" ? (
                        <>
                          <TooltipProvider>
                            <div className="flex items-center gap-1">
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0 text-primary hover:text-primary hover:bg-primary/10"
                                    onClick={() => handleDownload("json", bill)}
                                  >
                                    <FileJson className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Download JSON</p>
                                </TooltipContent>
                              </Tooltip>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0 text-success hover:text-success hover:bg-success/10"
                                    onClick={() => handleDownload("excel", bill)}
                                  >
                                    <FileSpreadsheet className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Download Excel</p>
                                </TooltipContent>
                              </Tooltip>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDownload("pdf", bill)}
                                  >
                                    <FileText className="h-4 w-4" />
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p>Download PDF</p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          </TooltipProvider>
                        </>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6}>
                  <EmptyState
                    title="No bills found"
                    description="Upload your first bill to get started"
                  />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        )}
      </div>
    </div>
  );
}
