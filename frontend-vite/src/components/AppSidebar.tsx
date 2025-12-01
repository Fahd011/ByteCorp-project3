import { Home, FileText, Download, LogOut, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink } from "@/components/NavLink";
import { useAuth } from "@/context/AuthContext";
import { auditLogsAPI } from "@/services/api";
import { useToast } from "@/hooks/use-toast";
import { SagilityLogo } from "@/components/SagilityLogo";
import { extractErrorMessage } from "@/utils/errorHandling";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  useSidebar,
} from "@/components/ui/sidebar";

const menuItems = [
  { title: "Dashboard", url: "/", icon: Home },
  { title: "Manual Bill Extraction", url: "/extraction", icon: FileText },
];

export function AppSidebar() {
  const { open } = useSidebar();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [isDownloadingLogs, setIsDownloadingLogs] = useState(false);

  const handleLogout = () => {
    logout();
    // Clear all React Query cache
    queryClient.clear();
    navigate("/auth", { replace: true });
  };

  const handleDownloadLogs = async () => {
    setIsDownloadingLogs(true);
    try {
      const response = await auditLogsAPI.downloadCSV();
      
      // Create blob from response
      const blob = new Blob([response.data], { type: "text/csv" });
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      
      // Generate filename with timestamp
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, -5);
      a.download = `audit_logs_${timestamp}.csv`;
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast({
        title: "Download started",
        description: "Audit logs CSV is being downloaded",
      });
    } catch (error: unknown) {
      toast({
        title: "Download failed",
        description: extractErrorMessage(error, "Failed to download audit logs"),
        variant: "destructive",
      });
    } finally {
      setIsDownloadingLogs(false);
    }
  };

  return (
    <Sidebar className="border-r border-border">
      <SidebarHeader className="border-b border-border px-6 py-4">
        <div className="flex items-center gap-3">
          <SagilityLogo className="text-foreground" width={open ? 28 : 24} height={open ? 36 : 32} />
          {open && <span className="font-semibold text-lg text-foreground">Sagiliti</span>}
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end
                      className="flex items-center gap-3 px-3 py-2 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-lg transition-colors"
                      activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                    >
                      <item.icon className="h-5 w-5" />
                      {open && <span>{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <div className="mt-auto border-t border-border">
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <button 
                      onClick={handleDownloadLogs}
                      disabled={isDownloadingLogs}
                      className="flex items-center gap-3 px-3 py-2 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-lg transition-colors w-full disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isDownloadingLogs ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : (
                        <Download className="h-5 w-5" />
                      )}
                      {open && <span>Download Logs</span>}
                    </button>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton asChild>
                    <button 
                      onClick={handleLogout}
                      className="flex items-center gap-3 px-3 py-2 text-destructive hover:bg-destructive/10 rounded-lg transition-colors w-full"
                    >
                      <LogOut className="h-5 w-5" />
                      {open && <span>Logout</span>}
                    </button>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </div>
      </SidebarContent>
    </Sidebar>
  );
}
