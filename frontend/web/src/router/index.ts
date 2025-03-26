import VTKCanvas from '@/components/VTKCanvas.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: VTKCanvas,
    },
  ],
})

export default router
