import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        muted: "hsl(var(--muted))",
        accent: "hsl(var(--accent))",
        primary: "hsl(var(--primary))",
      },
      boxShadow: {
        panel: "0 18px 60px rgba(0, 0, 0, 0.22)",
      },
    },
  },
  plugins: [],
};

export default config;
