/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        claude: {
          orange: '#D97757',
          dark: '#1A1A1A',
          darker: '#111111',
          surface: '#242424',
          border: '#333333',
          text: '#E5E5E5',
          muted: '#888888',
        },
        orch: {
          gold: '#C9A84C',
          dark: '#0D0F14',
          darker: '#080A0E',
          surface: '#161922',
          border: '#2A2D3A',
          text: '#E8E0CC',
          muted: '#7A7464',
          red: '#8B2020',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        jp: ['Noto Sans JP', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { transform: 'translateY(10px)', opacity: 0 }, '100%': { transform: 'translateY(0)', opacity: 1 } },
      }
    }
  },
  plugins: []
}
