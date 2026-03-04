<template>
  <div class="min-h-screen flex flex-col">
    <!-- Header -->
    <header class="header">
      <div class="header-inner">
        <router-link to="/" class="logo">
          <div class="logo-icon">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <span class="logo-text">FastWhisper</span>
        </router-link>
      </div>
    </header>

    <!-- Main -->
    <main class="flex-1">
      <div class="main-container">
        <slot />
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <p>录音转会议纪要服务</p>
    </footer>
  </div>
</template>

<script setup>
</script>

<style scoped>
.header {
  @apply sticky top-0 z-50 backdrop-blur-xl bg-dark-950/80 border-b border-dark-800/50;
}

.header-inner {
  @apply max-w-4xl mx-auto px-6 h-14 flex items-center justify-between;
}

.logo {
  @apply flex items-center gap-2.5;
}

.logo-icon {
  @apply w-8 h-8 bg-gradient-to-br from-primary-400 to-primary-600 rounded-lg flex items-center justify-center;
}

.logo-text {
  @apply text-base font-semibold text-dark-100;
}

.main-container {
  @apply max-w-4xl mx-auto px-6 py-8;
}

.footer {
  @apply py-5 text-center text-xs text-dark-600 border-t border-dark-800/50;
}
</style>