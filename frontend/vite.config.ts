import { fileURLToPath, URL } from 'node:url'

import { viteCommonjs } from '@originjs/vite-plugin-commonjs'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import { defineConfig, loadEnv } from 'vite'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  console.log(env)

  return {
    plugins: [vue(), vueJsx(), vueDevTools(), viteCommonjs()],
    optimizeDeps: {
      exclude: ['@cornerstonejs/dicom-image-loader'],
      include: ['dicom-parser'],
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        // Proxy all API requests to FastAPI backend during development
        '/api': {
          target: env.VITE_API_URL,
          rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
          changeOrigin: true,
          secure: false,
          configure: (proxy, _options) => {
            proxy.on('error', (err, _req, _res) => {
              console.log('proxy error', err)
            })
          },
        },
      },
    },
  }
})
