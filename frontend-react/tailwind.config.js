/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4A90E2',
          50: '#EBF2FC',
          100: '#D7E6F9',
          200: '#AFCDF3',
          300: '#87B4ED',
          400: '#5F9BE7',
          500: '#4A90E2',
          600: '#2372D3',
          700: '#1B5AA4',
          800: '#144175',
          900: '#0C2946',
        },
        secondary: '#357ABD',
        agent: {
          ideological: {
            DEFAULT: '#ff6b6b',
            light: '#ff8787',
            dark: '#e85555',
          },
          evaluation: {
            DEFAULT: '#48dbfb',
            light: '#6fe3fc',
            dark: '#22c7e5',
          },
          task: {
            DEFAULT: '#1dd1a1',
            light: '#45d9b3',
            dark: '#15b88a',
          },
          exploration: {
            DEFAULT: '#feca57',
            light: '#fed674',
            dark: '#e5b343',
          },
          competition: {
            DEFAULT: '#5f27cd',
            light: '#7b4dd4',
            dark: '#4a1fa8',
          },
          course: {
            DEFAULT: '#ff9ff3',
            light: '#ffb8f6',
            dark: '#e580d9',
          },
        },
      },
      fontFamily: {
        sans: ['PingFang SC', 'Source Han Sans', 'Arial', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in-left': 'slideInLeft 0.3s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        slideInLeft: {
          '0%': { transform: 'translateX(-20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(74, 144, 226, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(74, 144, 226, 0.8)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
