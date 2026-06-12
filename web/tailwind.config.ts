import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#05060a",
        panel: "#0b0e16",
        edge: "#1a2030",
        evil: "#ff3b5c",
        warn: "#ffb020",
        good: "#34e2b0",
        cyan: "#46c6ff",
        muted: "#8a93a6",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(70,198,255,0.45)",
        evilglow: "0 0 40px -8px rgba(255,59,92,0.5)",
      },
    },
  },
  plugins: [],
};
export default config;
