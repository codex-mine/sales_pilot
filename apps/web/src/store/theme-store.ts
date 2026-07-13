import { create } from "zustand";
type Theme = "light" | "dark" | "system";
export const useThemeStore = create<{ theme: Theme; setTheme: (theme: Theme) => void }>((set) => ({ theme: "system", setTheme: (theme) => set({ theme }) }));
