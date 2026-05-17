import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:18081',
        changeOrigin: true
      },
      '/health': {
        target: process.env.VITE_API_BASE_URL || 'http://127.0.0.1:18081',
        changeOrigin: true
      }
    }
  }
})
