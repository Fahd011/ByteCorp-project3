import { Loader2, Plus, FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ProviderSelect } from "@/components/ProviderSelect";
import { useCredentialUpload } from "@/hooks/useCredentialUpload";

export function CredentialUploadDialog() {
  const {
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
  } = useCredentialUpload();

  return (
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
          <ProviderSelect
            value={selectedProvider}
            onValueChange={setSelectedProvider}
            providers={allProviders}
            id="provider-select-dialog"
          />

          {/* CSV File Input */}
          <div className="space-y-2">
            <label htmlFor="csv-file-input" className="text-sm font-medium text-foreground">
              CSV File
            </label>
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
  );
}

