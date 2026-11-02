import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    babel({ presets: [reactCompilerPreset()] })
  ],
  server: {
    proxy: {
      '/search': 'http://127.0.0.1:8000',
      '/dictionary': 'http://127.0.0.1:8000',
      '/benchmark': 'http://127.0.0.1:8000',
      '/algorithm': 'http://127.0.0.1:8000',
    },
  },
})
