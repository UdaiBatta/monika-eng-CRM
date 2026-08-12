import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "./theme-switch";

const theme = vi.hoisted(() => ({
  resolvedTheme: "dark",
  setTheme: vi.fn(),
}));

vi.mock("next-themes", () => ({
  useTheme: () => theme,
}));

describe("ThemeToggle", () => {
  afterEach(() => theme.setTheme.mockClear());

  it.each([
    ["dark", "Switch to light theme", "light"],
    ["light", "Switch to dark theme", "dark"],
  ])("switches from %s mode", (current, label, next) => {
    theme.resolvedTheme = current;
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(theme.setTheme).toHaveBeenCalledWith(next);
  });
});
