import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Aligned 1:1 with the live dashboard's holographic command interface
        // (src/findevil/ui/static/find-evil.html + fe-holo.js), so the site
        // reads as a preview of the 3-D molecular field.
        ink: "#060a10",
        panel: "#0b121c",
        panel2: "#13202e",
        edge: "rgba(0,212,255,0.14)",
        evil: "#ff3864",
        warn: "#ffb86c",
        good: "#00ff9f",
        cyan: "#00d4ff",
        blue: "#6cc6ff",
        muted: "#7a8899",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["'Inter'", "'Space Grotesk'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(0,212,255,0.5)",
        evilglow: "0 0 40px -8px rgba(255,56,100,0.5)",
        greenglow: "0 0 40px -8px rgba(0,255,159,0.5)",
      },
    },
  },
  plugins: [],
};
export default config;
