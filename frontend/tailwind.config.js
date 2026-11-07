/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Nearly-square interface: applies consistently to cards, buttons,
      // input fields, alerts and panels across the frontend.
      // Keep rounded-full for intentionally circular status indicators.
      borderRadius: {
        DEFAULT: '3px',
        sm: '2px',
        md: '3px',
        lg: '3px',
        xl: '4px',
        '2xl': '4px',
        '3xl': '4px',
      },
      colors: {
        ink: '#101828',
        canvas: '#F7F8FA',
        primary: {
          DEFAULT: '#1652F0',
          dark: '#0B3D91',
          light: '#E8EEFE'
        },
        success: {
          DEFAULT: '#1E8E5A',
          light: '#E5F5EC'
        },
        danger: {
          DEFAULT: '#D64545',
          light: '#FBEAEA'
        },
        border: '#E2E5EA'
      },
      fontFamily: {
        sans: ['"Be Vietnam Pro"', 'system-ui', 'sans-serif']
      },
      fontFeatureSettings: {
        tnum: '"tnum"'
      },
      boxShadow: {
        card: '0 1px 2px rgba(16, 24, 40, 0.06), 0 1px 3px rgba(16, 24, 40, 0.08)'
      }
    }
  },
  plugins: []
}
