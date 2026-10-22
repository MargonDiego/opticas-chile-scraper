/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}"],
  theme: {
    container: {
      center: true,
      padding: {
        DEFAULT: "20px",
        sm: "24px",
        lg: "32px",
      },
      screens: {
        sm: "640px",
        md: "768px",
        lg: "1024px",
        xl: "1200px",
        "2xl": "1200px",
      },
    },
    extend: {
      /* ------------------------------------------------------------------
       * Colour tokens.
       * The CSS variables hold bare OKLCH channel triplets (L C H), so every
       * entry composes as oklch(var(--token) / <alpha>). The <alpha-value>
       * placeholder is what lets `bg-primary/90` resolve to
       * `oklch(var(--primary) / 0.9)` instead of dropping the alpha.
       * ------------------------------------------------------------------ */
      colors: {
        background: "oklch(var(--background) / <alpha-value>)",
        foreground: "oklch(var(--foreground) / <alpha-value>)",
        border: {
          DEFAULT: "oklch(var(--border) / <alpha-value>)",
          strong: "oklch(var(--border-strong) / <alpha-value>)",
        },
        /* Alias of `border`, named after the DESIGN.md "Hairline" scale. */
        hairline: {
          DEFAULT: "oklch(var(--border) / <alpha-value>)",
          strong: "oklch(var(--border-strong) / <alpha-value>)",
        },
        input: "oklch(var(--input) / <alpha-value>)",
        ring: "oklch(var(--ring) / <alpha-value>)",
        popover: {
          DEFAULT: "oklch(var(--popover) / <alpha-value>)",
          foreground: "oklch(var(--popover-foreground) / <alpha-value>)",
        },
        primary: {
          DEFAULT: "oklch(var(--primary) / <alpha-value>)",
          foreground: "oklch(var(--primary-foreground) / <alpha-value>)",
          hover: "oklch(var(--primary-hover) / <alpha-value>)",
          active: "oklch(var(--primary-active) / <alpha-value>)",
        },
        /* Ink subtle — large text and decorative rules only. */
        ink: {
          subtle: "oklch(var(--ink-subtle) / <alpha-value>)",
        },
        /* Theme-independent ink for content on the always-white product well. */
        "on-white": "oklch(var(--on-white) / <alpha-value>)",
        secondary: {
          DEFAULT: "oklch(var(--secondary) / <alpha-value>)",
          foreground: "oklch(var(--secondary-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "oklch(var(--muted) / <alpha-value>)",
          foreground: "oklch(var(--muted-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "oklch(var(--accent) / <alpha-value>)",
          foreground: "oklch(var(--accent-foreground) / <alpha-value>)",
          hover: "oklch(var(--accent-hover) / <alpha-value>)",
        },
        destructive: {
          DEFAULT: "oklch(var(--destructive) / <alpha-value>)",
          foreground: "oklch(var(--destructive-foreground) / <alpha-value>)",
          hover: "oklch(var(--destructive-hover) / <alpha-value>)",
          active: "oklch(var(--destructive-active) / <alpha-value>)",
        },
        card: {
          DEFAULT: "oklch(var(--card) / <alpha-value>)",
          foreground: "oklch(var(--card-foreground) / <alpha-value>)",
        },
        success: {
          DEFAULT: "oklch(var(--success) / <alpha-value>)",
          foreground: "oklch(var(--success-foreground) / <alpha-value>)",
          tint: "oklch(var(--success-tint) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "oklch(var(--warning) / <alpha-value>)",
          foreground: "oklch(var(--warning-foreground) / <alpha-value>)",
          tint: "oklch(var(--warning-tint) / <alpha-value>)",
        },
        danger: {
          tint: "oklch(var(--danger-tint) / <alpha-value>)",
        },
        surface: {
          sunken: "oklch(var(--surface-sunken) / <alpha-value>)",
        },
      },

      /* One radius per element class; the value steps down as elements get
       * smaller. 6px chips/badges · 9px buttons/inputs · 13px cards ·
       * 18px dialogs and sheets. */
      borderRadius: {
        sm: "6px",
        DEFAULT: "6px",
        md: "9px",
        lg: "13px",
        xl: "18px",
        "2xl": "18px",
        "3xl": "20px",
        full: "9999px",
      },

      /* Two shadow tokens, used only on surfaces that genuinely float. */
      boxShadow: {
        sm: "0 1px 2px oklch(0.20 0.02 250 / 0.05)",
        md: "var(--shadow-overlay)",
        lg: "var(--shadow-overlay)",
        xl: "var(--shadow-modal)",
        "2xl": "var(--shadow-modal)",
        overlay: "var(--shadow-overlay)",
        modal: "var(--shadow-modal)",
      },

      /* One family for everything — hierarchy comes from weight, size and
       * colour, never from a font switch. `mono` and `display` are kept as
       * aliases so legacy markup still compiles without a second typeface. */
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          '"Segoe UI"',
          "sans-serif",
        ],
        mono: [
          '"Plus Jakarta Sans"',
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          '"Segoe UI"',
          "sans-serif",
        ],
        display: [
          '"Plus Jakarta Sans"',
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          '"Segoe UI"',
          "sans-serif",
        ],
      },

      fontSize: {
        display: [
          "30px",
          { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "700" },
        ],
        headline: [
          "22px",
          { lineHeight: "1.25", letterSpacing: "-0.015em", fontWeight: "700" },
        ],
        title: ["16px", { lineHeight: "1.35", fontWeight: "600" }],
        body: ["15px", { lineHeight: "1.6" }],
        "body-sm": ["13.5px", { lineHeight: "1.55" }],
        label: ["13px", { lineHeight: "1.4", fontWeight: "600" }],
        price: ["19px", { lineHeight: "1.2", fontWeight: "700" }],
        "price-lg": ["24px", { lineHeight: "1.2", fontWeight: "700" }],
      },

      transitionDuration: {
        fast: "120ms",
        base: "180ms",
        slow: "240ms",
      },

      transitionTimingFunction: {
        out: "cubic-bezier(0.22, 1, 0.36, 1)",
      },

      maxWidth: {
        page: "1200px",
        prose: "70ch",
      },
    },
  },

  /* Tailwind v3 has no pointer media variants — the design system needs
   * them to switch between 44px touch targets and 40px pointer targets.
   *
   * NOTE: in v3 the top-level `variants.extend` key maps to CORE PLUGIN
   * names, so a media variant declared there is a silent no-op. `addVariant`
   * is the v3 API that registers a variant against every core plugin. */
  plugins: [
    require("tailwindcss-animate"),
    require("tailwindcss/plugin")(({ addVariant }) => {
      addVariant("pointer-coarse", "@media (pointer: coarse)");
      addVariant("pointer-fine", "@media (pointer: fine)");
      addVariant("hover-supported", "@media (hover: hover)");
    }),
  ],
};
