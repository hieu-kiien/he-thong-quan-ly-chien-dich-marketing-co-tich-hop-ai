(function () {
  try {
    var stored = localStorage.getItem('mf-theme');
    var dark =
      stored === 'dark' ||
      (stored !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    if (dark) document.documentElement.classList.add('dark');
  } catch (e) {
    /* localStorage không khả dụng: giữ giao diện sáng */
  }
})();
