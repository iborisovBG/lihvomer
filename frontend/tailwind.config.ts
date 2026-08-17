import type { Config } from "tailwindcss";

const config: Config = {
  // Класовете dark: следват избора на потребителя, а не системната
  // настройка. Скриптът в layout.tsx винаги оставя явен data-theme.
  darkMode: ["selector", '[data-theme="dark"]'],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        border: "hsl(var(--border))",
        ring: "hsl(var(--ring))",
        surface: "hsl(var(--surface))",
        accent: "hsl(var(--accent))",
        good: "hsl(var(--good))",
        warn: "hsl(var(--warn))",
        bad: "hsl(var(--bad))",
        label: {
          DEFAULT: "hsl(var(--foreground))",
          secondary: "hsl(var(--foreground) / 0.6)",
          tertiary: "hsl(var(--foreground) / 0.3)",
        },
      },
    },
  },
  plugins: [],
};

export default config;
