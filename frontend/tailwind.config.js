/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        banker: {
          DEFAULT: "#3B82F6",
          light: "#60A5FA",
          dark: "#1E40AF"
        },
        player: {
          DEFAULT: "#EF4444",
          light: "#F87171",
          dark: "#B91C1C"
        },
        tie: {
          DEFAULT: "#10B981",
          light: "#34D399",
          dark: "#047857"
        },
        casino: {
          bg: "#0F172A",
          card: "#1E293B",
          border: "#334155",
          gold: "#FBBF24",
          green: "#10B981"
        }
      },
      animation: {
        "pulse-glow": "pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "slide-up": "slide-up 0.3s ease-out"
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": {
            opacity: 1,
            boxShadow: "0 0 20px rgba(251, 191, 36, 0.5)"
          },
          "50%": {
            opacity: 0.8,
            boxShadow: "0 0 40px rgba(251, 191, 36, 0.8)"
          }
        },
        "slide-up": {
          "0%": {
            opacity: 0,
            transform: "translateY(20px)"
          },
          "100%": {
            opacity: 1,
            transform: "translateY(0)"
          }
        }
      }
    }
  },
  plugins: []
}
