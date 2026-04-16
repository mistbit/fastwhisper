import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('./views/Dashboard.vue'),
  },
  {
    path: '/tasks',
    name: 'task-list',
    component: () => import('./views/TaskList.vue'),
  },
  {
    path: '/tasks/new',
    name: 'new-task',
    component: () => import('./views/NewTask.vue'),
  },
  {
    path: '/tasks/:id',
    name: 'task-detail',
    component: () => import('./views/TaskDetail.vue'),
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
