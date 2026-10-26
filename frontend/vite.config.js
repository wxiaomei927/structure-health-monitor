import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { NaiveUiResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    // naive-ui 的组件按需自动引入，模板里直接写 <n-card> 即可
    Components({
      resolvers: [NaiveUiResolver()]
    })
  ],
  server: {
    port: 5174,
    proxy: {
      // 前端开发时把 /api 请求转发到本地后端，避免跨域配置
      '/api': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true
      }
    },
    // 开发期间关闭缓存，样式改动后刷新就能看到，不用手动强刷
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate'
    }
  }
})
