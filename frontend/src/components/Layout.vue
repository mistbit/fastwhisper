<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="sticky top-0 z-50 backdrop-blur-xl bg-dark-900/80 border-b border-dark-700/50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <router-link to="/" class="flex items-center space-x-3">
            <div class="w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <span class="text-lg font-semibold text-dark-100">FastWhisper</span>
          </router-link>

          <!-- Nav -->
          <nav class="flex items-center space-x-4">
            <router-link
              to="/"
              class="px-3 py-2 text-sm font-medium text-dark-300 hover:text-dark-100 transition-colors"
              :class="{ 'text-primary-400': $route.path === '/' }"
            >
              任务列表
            </router-link>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main content -->
    <main class="flex-1 relative">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <slot />
      </div>
    </main>

    <!-- Footer -->
    <footer class="border-t border-dark-700/50 py-6">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <p class="text-center text-sm text-dark-400">
          FastWhisper - 录音转会议纪要服务
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup>
</script>