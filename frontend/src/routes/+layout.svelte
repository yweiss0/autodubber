<script>
    import "../app.css";
</script>

<div class="min-h-screen bg-gray-100 flex flex-col">
  <nav class="bg-white border-b border-gray-200 px-4 py-3 shadow-sm">
    <div class="container mx-auto flex items-center">
      <h1 class="text-2xl font-semibold text-blue-700">AutoVoiceOver - AI Video Voiceover</h1>
    </div>
  </nav>
  
  <main class="container mx-auto flex-grow p-4">
    <slot />
  </main>
  
  <footer class="bg-white border-t border-gray-200 p-4">
    <div class="container mx-auto text-center text-gray-500 text-sm">
      &copy; {new Date().getFullYear()} AutoVoiceOver - AI-powered video voiceover by YW
    </div>
  </footer>
</div>