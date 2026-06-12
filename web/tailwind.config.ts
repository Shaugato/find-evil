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
        // so the site reads as a preview of the actual product.
        ink: "#050507",
        panel: "#0a0a14",
        panel2: "#0f0f1e",
        edge: "rgba(255,255,255,0.08)",
        evil: "#ff1744",
        warn: "#ffab00",
        good: "#00e676",
        cyan: "#00e5ff",
        blue: "#2979ff",
        muted: "#8a93a6",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["'Space Grotesk'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(0,229,255,0.45)",
        evilglow: "0 0 40px -8px rgba(255,23,68,0.5)",
        greenglow: "0 0 40px -8px rgba(0,230,118,0.5)",
      },
    },
  },
  plugins: [],
};
export default config;
