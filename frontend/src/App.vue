<template>
  <div class="min-h-screen bg-dark-950">
    <!-- Subtle background -->
    <div class="fixed inset-0 pointer-events-none">
      <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-dark-900 via-dark-950 to-dark-950"></div>
    </div>

    <Layout>
      <router-view />
    </Layout>
  </div>
</template>

<script setup>
import Layout from './components/Layout.vue'
</script>