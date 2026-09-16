import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true }
    }
  },
  // Rendertests voor de schermen (vitest). De pure functies in src/lib blijven met
  // `node --test` draaien; die hebben geen DOM nodig.
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.render.test.jsx'],
    restoreMocks: true,
  },
})
