/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paytm: {
          blue: '#00BAF2',
          'dark-blue': '#002970',
          'light-blue': '#E8F7FC',
          gold: '#FFB800',
          navy: '#004BA8',
        },
        primary: {
          50: '#E8F7FC',
          100: '#CCF0FA',
          200: '#99E1F5',
          300: '#66D2F0',
          400: '#33C3EB',
          500: '#00BAF2',
          600: '#0095D9',
          700: '#0070A3',
          800: '#004B6D',
          900: '#002537',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        'paytm': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'paytm-lg': '0 4px 16px rgba(0, 0, 0, 0.12)',
      }
    },
  },
  plugins: [],
}
