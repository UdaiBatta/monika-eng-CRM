import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      type="button"
      variant="outline"
      className="relative w-[72px] overflow-hidden rounded-full px-2"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      title={isDark ? "Light mode" : "Dark mode"}
    >
      <span
        aria-hidden="true"
        className={cn(
          "absolute top-1/2 size-7 -translate-y-1/2 rounded-full bg-muted shadow-sm transition-[left]",
          isDark ? "left-1" : "left-[calc(100%-2rem)]",
        )}
      />
      <span className="relative flex w-full items-center justify-between">
        <Moon
          data-icon="inline-start"
          aria-hidden="true"
          className={cn(
            "transition-opacity",
            isDark ? "opacity-100" : "opacity-35",
          )}
        />
        <Sun
          data-icon="inline-end"
          aria-hidden="true"
          className={cn(
            "transition-opacity",
            isDark ? "opacity-35" : "opacity-100",
          )}
        />
      </span>
    </Button>
  );
}
