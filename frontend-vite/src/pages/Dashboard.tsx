import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Plus, ChevronDown, ChevronUp, Loader2, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DashboardStats } from "@/components/DashboardStats";
import { ProvidersTable } from "@/components/ProvidersTable";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { credentialsAPI, providerAPI } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { extractErrorMessage } from "@/utils/errorHandling";

export default function Dashboard() {
  const [statsOpen, setStatsOpen] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedProvider, setSelectedProvider] = useState("");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch credentials to get count
  const { data: credentials } = useQuery({
    queryKey: ["credentials"],
    queryFn: async () => {
      const response = await credentialsAPI.getAll();
      return response.data;
    },
  });

  // Fetch providers for the dropdown
  const { data: providers } = useQuery({
    queryKey: ["providers"],
    queryFn: async () => {
      const response = await providerAPI.getAll();
      return response.data;
    },
  });

  // Upload credentials mutation
  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      return await credentialsAPI.upload(formData);
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Credentials uploaded successfully",
      });
      queryClient.invalidateQueries({ queryKey: ["credentials"] });
      setIsDialogOpen(false);
      setSelectedFile(null);
      setSelectedProvider("");
    },
    onError: (error: unknown) => {
      toast({
        title: "Error",
        description: extractErrorMessage(error, "Failed to upload credentials"),
        variant: "destructive",
      });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith('.csv')) {
        toast({
          title: "Invalid file type",
          description: "Please upload a CSV file",
          variant: "destructive",
        });
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      toast({
        title: "No file selected",
        description: "Please select a CSV file",
        variant: "destructive",
      });
      return;
    }

    if (!selectedProvider) {
      toast({
        title: "No provider selected",
        description: "Please select a provider",
        variant: "destructive",
      });
      return;
    }

    const provider = providers?.find((p: any) => p.id === selectedProvider);
    if (!provider) {
      toast({
        title: "Provider not found",
        description: "Selected provider is invalid",
        variant: "destructive",
      });
      return;
    }

    const formData = new FormData();
    formData.append("csv_file", selectedFile);
    formData.append("login_url", provider.login_url ?? "");
    formData.append("billing_url", provider.billing_url ?? "");

    uploadMutation.mutate(formData);
  };

  const activeCredentials = credentials?.filter((cred: any) => !cred.is_deleted) ?? [];
  // Count unique providers (by utility_co_name)
  const uniqueProviders = new Set(
    activeCredentials
      .filter((cred: any) => cred.utility_co_name)
      .map((cred: any) => cred.utility_co_name)
  );
  const providerCount = uniqueProviders.size;

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
              placeholder="Search providers, clients, or account numbers..."
              className="pl-10 bg-card border-border"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2 bg-primary hover:bg-primary-hover text-primary-foreground">
                <Plus className="h-4 w-4" />
                Create Session
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Create Session - Upload Credentials</DialogTitle>
              </DialogHeader>
              <div className="space-y-6 py-4">
                {/* Provider Selection */}
                <div className="space-y-2">
                  <label htmlFor="provider-select-dialog" className="text-sm font-medium text-foreground">Provider</label>
                  <select
                    id="provider-select-dialog"
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-card text-foreground"
                  >
                    <option value="">Select a provider</option>
                    {providers?.map((provider: any) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* CSV File Input */}
                <div className="space-y-2">
                  <label htmlFor="csv-file-input" className="text-sm font-medium text-foreground">CSV File</label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="csv-file-input"
                      type="file"
                      accept=".csv"
                      onChange={handleFileChange}
                      className="flex-1"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Upload a CSV file with credentials (email, password, etc.)
                  </p>
                  {selectedFile && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <FileText className="h-4 w-4" />
                      <span className="truncate">{selectedFile.name}</span>
                      <button
                        onClick={() => setSelectedFile(null)}
                        className="ml-auto text-destructive hover:text-destructive/80"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>

                {/* Upload Button */}
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setIsDialogOpen(false)}
                    disabled={uploadMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleUpload}
                    disabled={uploadMutation.isPending || !selectedFile || !selectedProvider}
                  >
                    {uploadMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      "Upload Credentials"
                    )}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Providers Table */}
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-muted-foreground">
            Showing {providerCount} of {providerCount} providers
          </div>
        </div>

        <ProvidersTable searchTerm={searchTerm} />
      </div>
    </div>
  );
}
