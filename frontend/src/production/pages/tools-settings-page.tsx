import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BadgeCheck,
  Bell,
  Building2,
  Database,
  FileKey2,
  Files,
  GitBranch,
  Layers3,
  Network,
  Settings2,
  ShieldCheck,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { hasPermission, useCurrentUser } from "@/production/lib/auth";

type Tool = {
  label: string;
  description: string;
  to: string;
  icon: LucideIcon;
  permission: string;
};

const groups: Array<{ title: string; description: string; tools: Tool[] }> = [
  {
    title: "Owner administration",
    description: "System-wide business controls kept separate from normal employee work.",
    tools: [
      {
        label: "Owner Control Centre",
        description: "People, access, work responsibility, features, data quality and system readiness.",
        to: "/app/owner",
        icon: ShieldCheck,
        permission: "system.owner_control.view",
      },
    ],
  },
  {
    title: "People & locations",
    description: "Maintain the teams and places used across Monika Engineers.",
    tools: [
      {
        label: "Employees",
        description: "Employee records and profiles.",
        to: "/app/employees",
        icon: Users,
        permission: "organization.employee.view",
      },
      {
        label: "Companies",
        description: "Legal entities and company records.",
        to: "/app/organization/companies",
        icon: Building2,
        permission: "organization.company.view",
      },
      {
        label: "Branches",
        description: "Office and workshop locations.",
        to: "/app/organization/branches",
        icon: Network,
        permission: "organization.branch.view",
      },
      {
        label: "Departments",
        description: "The teams people work in.",
        to: "/app/organization/departments",
        icon: Layers3,
        permission: "organization.department.view",
      },
    ],
  },
  {
    title: "Access & records",
    description: "Control access and review who changed what.",
    tools: [
      {
        label: "Roles",
        description: "Group access by job responsibility.",
        to: "/app/access/roles",
        icon: ShieldCheck,
        permission: "rbac.role.view",
      },
      {
        label: "Permissions",
        description: "See the actions that can be allowed.",
        to: "/app/access/permissions",
        icon: FileKey2,
        permission: "rbac.permission.view",
      },
      {
        label: "Role assignments",
        description: "Give the right access to each person.",
        to: "/app/access/assignments",
        icon: BadgeCheck,
        permission: "rbac.assignment.view",
      },
      {
        label: "Activity history",
        description: "See who changed a record and when.",
        to: "/app/activity-history",
        icon: Activity,
        permission: "audit.event.view",
      },
    ],
  },
  {
    title: "Rules & automation",
    description: "Occasional setup for administrators.",
    tools: [
      {
        label: "Company settings",
        description: "Basic preferences for the business.",
        to: "/app/settings/company",
        icon: Settings2,
        permission: "configuration.settings.view",
      },
      {
        label: "Numbering",
        description: "How enquiry, quotation and document numbers are created.",
        to: "/app/settings/numbering",
        icon: Database,
        permission: "numbering.sequence.view",
      },
      {
        label: "Common lists",
        description: "Shared options used in forms and registers.",
        to: "/app/settings/masters",
        icon: Layers3,
        permission: "masters.view",
      },
      {
        label: "Document categories",
        description: "Organize the different types of documents.",
        to: "/app/settings/document-categories",
        icon: Files,
        permission: "documents.category.view",
      },
      {
        label: "Approval rules",
        description: "Decide who approves each type of request.",
        to: "/app/settings/approval-workflows",
        icon: GitBranch,
        permission: "approvals.workflow.view",
      },
      {
        label: "Notifications",
        description: "Choose which alerts you receive.",
        to: "/app/settings/notifications",
        icon: Bell,
        permission: "notifications.notification.manage_preferences",
      },
    ],
  },
];

export default function ToolsSettingsPage() {
  const { data: user } = useCurrentUser();
  const visibleGroups = groups
    .map((group) => ({
      ...group,
      tools: group.tools.filter((tool) =>
        hasPermission(user, tool.permission),
      ),
    }))
    .filter((group) => group.tools.length);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-semibold">Tools & settings</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          These are occasional or specialist tools. Your daily work stays in the
          sidebar, and you only see options allowed for your role.
        </p>
      </div>

      {visibleGroups.length ? (
        <div className="grid items-start gap-4 lg:grid-cols-2">
          {visibleGroups.map((group) => (
            <Card key={group.title} size="sm">
              <CardHeader>
                <CardTitle>{group.title}</CardTitle>
                <CardDescription>{group.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {group.tools.map((tool) => {
                  const Icon = tool.icon;
                  return (
                    <Button
                      key={tool.to}
                      variant="ghost"
                      nativeButton={false}
                      render={<Link to={tool.to} />}
                      className="h-auto w-full justify-start py-3 text-left"
                    >
                      <Icon data-icon="inline-start" />
                      <span className="flex min-w-0 flex-col items-start">
                        <span>{tool.label}</span>
                        <span className="whitespace-normal text-xs font-normal text-muted-foreground">
                          {tool.description}
                        </span>
                      </span>
                    </Button>
                  );
                })}
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card size="sm">
          <CardHeader>
            <CardTitle>No extra tools for this role</CardTitle>
            <CardDescription>
              Everything you need is already available in the main sidebar.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
