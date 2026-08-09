"use client";

import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

type ColorThemeContextType = {
  colorTheme: string;
  setColorTheme: (theme: string) => void;
};

const ColorThemeContext = createContext<ColorThemeContextType | undefined>(undefined);

export function ColorThemeProvider({ children }: { children: ReactNode }) {
  const [colorTheme, setColorThemeState] = useState<string>("sunny");

  useEffect(() => {
    const saved = localStorage.getItem("color-theme");
    if (saved && (saved === "basil" || saved === "forest" || saved === "sunny")) {
      setColorThemeState(saved);
    }
  }, []);

  const setColorTheme = (theme: string) => {
    setColorThemeState(theme);
    if (typeof window !== "undefined") {
      localStorage.setItem("color-theme", theme);
    }
  };

  return (
    <ColorThemeContext.Provider value={{ colorTheme, setColorTheme }}>
      {children}
    </ColorThemeContext.Provider>
  );
}

export function useColorTheme() {
  const context = useContext(ColorThemeContext);
  if (!context) {
    throw new Error("useColorTheme must be used within ColorThemeProvider");
  }
  return context;
}
