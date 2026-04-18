import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { ShellProvider } from "./ShellContext";
import { AppShell, ApprovalAliasRedirect } from "../components/AppShell";
import { AuditPage } from "../pages/AuditPage";
import { ComplianceDashboardPage } from "../pages/ComplianceDashboardPage";
import { IntakePage } from "../pages/IntakePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PipelinesPage } from "../pages/PipelinesPage";
import { TracePage } from "../pages/TracePage";
import { VendorDetailPage } from "../pages/VendorDetailPage";
import { VendorPortalPage } from "../pages/VendorPortalPage";
import { VendorReportPage } from "../pages/VendorReportPage";
import { VendorsPage } from "../pages/VendorsPage";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 15_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ShellProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Navigate replace to="/pipelines" />} />
              <Route path="/pipelines" element={<PipelinesPage />} />
              <Route path="/vendors" element={<VendorsPage />} />
              <Route path="/vendors/:vendorId" element={<VendorDetailPage />} />
              <Route
                path="/vendors/:vendorId/report"
                element={<VendorReportPage />}
              />
              <Route path="/trace" element={<TracePage />} />
              <Route path="/trace/:vendorId" element={<TracePage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/audit/:vendorId" element={<AuditPage />} />
              <Route path="/dashboard/compliance" element={<ComplianceDashboardPage />} />
              <Route path="/approvals" element={<Navigate replace to="/audit" />} />
              <Route path="/approvals/:vendorId" element={<ApprovalAliasRedirect />} />
              <Route path="/intake" element={<IntakePage />} />
              <Route path="/vendor/register" element={<VendorPortalPage healthcare={false} />} />
              <Route path="/vendor/healthcare/register" element={<VendorPortalPage healthcare />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </ShellProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
