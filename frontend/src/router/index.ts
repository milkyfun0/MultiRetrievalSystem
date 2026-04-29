import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/search',
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('@/views/SearchPage.vue'),
      meta: { title: '检索' },
    },
    {
      path: '/prepare',
      name: 'prepare',
      component: () => import('@/views/PreparePage.vue'),
      meta: { title: '资源准备' },
    },
    {
      path: '/stores',
      name: 'stores',
      component: () => import('@/views/StoreManagePage.vue'),
      meta: { title: '资源管理' },
    },
  ],
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? ''} - 多模态检索系统`
})

export default router
