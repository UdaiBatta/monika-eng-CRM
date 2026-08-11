import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "@/production/lib/types";
import ToolsSettingsPage from "./tools-settings-page";

const user = {
  permissions: ["engineering.feasibility.view", "numbering.sequence.view"],
} as CurrentUser;

vi.mock("@/production/lib/auth", () => ({
  useCurrentUser: () => ({ data: user }),
  hasPermission: (currentUser: CurrentUser | undefined, permission: string) =>
    Boolean(currentUser?.permissions.includes(permission)),
}));

describe("tools and settings page", () => {
  afterEach(() => cleanup());

  it("shows only permitted tools with plain-language explanations", () => {
    render(
      <MemoryRouter>
        <ToolsSettingsPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /Engineering checks/ })).toBeInTheDocument();
    expect(screen.getByText("Record whether an enquiry can be built.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Numbering/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Roles/ })).not.toBeInTheDocument();
  });
});
