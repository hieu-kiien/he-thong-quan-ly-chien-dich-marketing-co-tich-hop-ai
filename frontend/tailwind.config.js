/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
        },
        sidebar: {
          bg: '#0F172A',
          hover: '#1E293B',
          text: '#94A3B8',
          active: '#FFFFFF'
        }
      }
    },
  },
  plugins: [],
}
