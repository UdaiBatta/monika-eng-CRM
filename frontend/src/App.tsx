import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { Spinner } from "@/components/ui/spinner";

const AxisERPMockup = lazy(() => import("@/mockups/axis/axis-erp-mockup"));
const AxisMarketingPreview = lazy(() => import("@/axis-marketing-preview"));
const LoginPage = lazy(() => import("@/production/pages/login-page"));
const AppShell = lazy(() => import("@/production/components/app-shell"));
const AuthBoundary = lazy(
  () => import("@/production/components/auth-boundary"),
);
const DashboardPage = lazy(() => import("@/production/pages/dashboard-page"));
const ResourcePage = lazy(() => import("@/production/pages/resource-page"));
const EmployeeDetailPage = lazy(
  () => import("@/production/pages/employee-detail-page"),
);
const EmployeeFormPage = lazy(
  () => import("@/production/pages/employee-form-page"),
);
const MasterDataPage = lazy(
  () => import("@/production/pages/master-data-page"),
);
const DocumentsPage = lazy(() => import("@/production/pages/documents-page"));
const DocumentDetailPage = lazy(
  () => import("@/production/pages/document-detail-page"),
);
const ApprovalsPage = lazy(() => import("@/production/pages/approvals-page"));
const ApprovalDetailPage = lazy(
  () => import("@/production/pages/approval-detail-page"),
);
const ActivityHistoryPage = lazy(
  () => import("@/production/pages/activity-history-page"),
);
const ApprovalWorkflowsPage = lazy(
  () => import("@/production/pages/approval-workflows-page"),
);
const NotificationSettingsPage = lazy(
  () => import("@/production/pages/notification-settings-page"),
);
const CustomersPage = lazy(() => import("@/production/pages/customers-page"));
const CustomerPage = lazy(() => import("@/production/pages/customer-page"));
const ActivitiesPage = lazy(() => import("@/production/pages/activities-page"));
const EnquiriesPage = lazy(() => import("@/production/pages/enquiries-page"));
const EnquiryCreatePage = lazy(
  () => import("@/production/pages/enquiry-create-page"),
);
const EnquiryPage = lazy(() => import("@/production/pages/enquiry-page"));
const IncomingEnquiriesPage = lazy(
  () => import("@/production/pages/incoming-enquiries-page"),
);
const WebsiteEnquiryPage = lazy(
  () => import("@/production/pages/website-enquiry-page"),
);
const EngineeringPage = lazy(
  () => import("@/production/pages/engineering-page"),
);
const EngineeringReviewPage = lazy(
  () => import("@/production/pages/engineering-review-page"),
);
const EstimatesPage = lazy(() => import("@/production/pages/estimates-page"));
const EstimatePage = lazy(() => import("@/production/pages/estimate-page"));
const QuotationsPage = lazy(() => import("@/production/pages/quotations-page"));
const QuotationPage = lazy(() => import("@/production/pages/quotation-page"));

function PageLoading() {
  return (
    <div className="axis-erp flex min-h-svh items-center justify-center bg-background text-sm text-muted-foreground">
      <Spinner />
      <span className="ml-2">Loading workspace…</span>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoading />}>
        <Routes>
          <Route path="/" element={<AxisMarketingPreview />} />
          <Route path="/mockups/axis" element={<AxisERPMockup />} />
          <Route path="/login" element={<LoginPage />} />

          <Route element={<AuthBoundary />}>
            <Route path="/app" element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route
                path="employees"
                element={<ResourcePage resourceKey="employees" />}
              />
              <Route path="employees/new" element={<EmployeeFormPage />} />
              <Route
                path="employees/:employeeId"
                element={<EmployeeDetailPage />}
              />
              <Route
                path="employees/:employeeId/edit"
                element={<EmployeeFormPage />}
              />
              <Route path="documents" element={<DocumentsPage />} />
              <Route
                path="documents/:documentId"
                element={<DocumentDetailPage />}
              />
              <Route path="approvals" element={<ApprovalsPage />} />
              <Route
                path="approvals/:approvalId"
                element={<ApprovalDetailPage />}
              />
              <Route
                path="activity-history"
                element={<ActivityHistoryPage />}
              />

              <Route path="crm" element={<Navigate to="customers" replace />} />
              <Route path="crm/customers" element={<CustomersPage />} />
              <Route
                path="crm/customers/:customerId"
                element={<CustomerPage />}
              />
              <Route path="crm/activities" element={<ActivitiesPage />} />
              <Route path="crm/enquiries" element={<EnquiriesPage />} />
              <Route
                path="crm/incoming-enquiries"
                element={<IncomingEnquiriesPage />}
              />
              <Route
                path="crm/incoming-enquiries/:submissionId"
                element={<WebsiteEnquiryPage />}
              />
              <Route
                path="crm/website-enquiries"
                element={<Navigate to="/app/crm/incoming-enquiries" replace />}
              />
              <Route
                path="crm/website-enquiries/:submissionId"
                element={<WebsiteEnquiryPage />}
              />
              <Route path="crm/enquiries/new" element={<EnquiryCreatePage />} />
              <Route
                path="crm/enquiries/:enquiryId"
                element={<EnquiryPage />}
              />
              <Route path="crm/engineering" element={<EngineeringPage />} />
              <Route
                path="crm/engineering/:reviewId"
                element={<EngineeringReviewPage />}
              />
              <Route path="crm/estimates" element={<EstimatesPage />} />
              <Route path="crm/estimates/:estimateId" element={<EstimatePage />} />
              <Route path="crm/quotations" element={<QuotationsPage />} />
              <Route path="crm/quotations/:quotationId" element={<QuotationPage />} />

              <Route
                path="organization"
                element={<Navigate to="companies" replace />}
              />
              <Route
                path="organization/companies"
                element={<ResourcePage resourceKey="companies" />}
              />
              <Route
                path="organization/branches"
                element={<ResourcePage resourceKey="branches" />}
              />
              <Route
                path="organization/departments"
                element={<ResourcePage resourceKey="departments" />}
              />
              <Route
                path="organization/designations"
                element={<ResourcePage resourceKey="designations" />}
              />
              <Route
                path="organization/warehouses"
                element={<ResourcePage resourceKey="warehouses" />}
              />

              <Route path="access" element={<Navigate to="roles" replace />} />
              <Route
                path="access/roles"
                element={<ResourcePage resourceKey="roles" />}
              />
              <Route
                path="access/permissions"
                element={<ResourcePage resourceKey="permissions" />}
              />
              <Route
                path="access/assignments"
                element={<ResourcePage resourceKey="role-assignments" />}
              />
              <Route
                path="access/overrides"
                element={<ResourcePage resourceKey="permission-overrides" />}
              />

              <Route
                path="settings"
                element={<Navigate to="company" replace />}
              />
              <Route
                path="settings/company"
                element={<ResourcePage resourceKey="company-settings" />}
              />
              <Route
                path="settings/features"
                element={<ResourcePage resourceKey="feature-flags" />}
              />
              <Route
                path="settings/numbering"
                element={<ResourcePage resourceKey="document-sequences" />}
              />
              <Route path="settings/masters" element={<MasterDataPage />} />
              <Route
                path="settings/document-categories"
                element={<ResourcePage resourceKey="document-categories" />}
              />
              <Route
                path="settings/approval-workflows"
                element={<ApprovalWorkflowsPage />}
              />
              <Route
                path="settings/notifications"
                element={<NotificationSettingsPage />}
              />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
