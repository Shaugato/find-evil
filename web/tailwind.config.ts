import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Aligned 1:1 with the live dashboard (src/findevil/ui/static/find-evil.html)
        // refined command-shell palette, so the site reads as a product preview.
        ink: "#0a0e14",
        panel: "#0e141d",
        panel2: "#161e2b",
        edge: "rgba(137,221,255,0.10)",
        evil: "#ff3864",
        warn: "#ffb86c",
        good: "#00ff9f",
        cyan: "#89ddff",
        blue: "#6cc6ff",
        muted: "#9aa4b2",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["'Inter'", "'Space Grotesk'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(137,221,255,0.45)",
        evilglow: "0 0 40px -8px rgba(255,56,100,0.5)",
        greenglow: "0 0 40px -8px rgba(0,255,159,0.5)",
      },
    },
  },
  plugins: [],
};
export default config;
