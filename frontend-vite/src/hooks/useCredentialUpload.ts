import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { credentialsAPI, providerAPI } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { extractErrorMessage } from "@/utils/errorHandling";
import { Provider } from "@/types";

export function useCredentialUpload() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedProvider, setSelectedProvider] = useState("");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch providers for the dropdown
  const { data: providers } = useQuery({
    queryKey: ["providers"],
    queryFn: async () => {
      const response = await providerAPI.getAll();
      return response.data;
    },
  });

  // Get providers list sorted by name
  const allProviders = useMemo(() => {
    if (!providers) return [];
    return [...providers].sort((a, b) => a.name.localeCompare(b.name));
  }, [providers]);

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
      queryClient.invalidateQueries({ queryKey: ["agentJobs"] });
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
    const file = e.target.files?.[0];
    if (file) {
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

    const provider = providers?.find((p: Provider) => p.id === selectedProvider);
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

  return {
    isDialogOpen,
    setIsDialogOpen,
    selectedFile,
    setSelectedFile,
    selectedProvider,
    setSelectedProvider,
    allProviders,
    uploadMutation,
    handleFileChange,
    handleUpload,
  };
}

