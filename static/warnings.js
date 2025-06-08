document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[data-warning], input[data-error]').forEach(cb => {
    cb.addEventListener('change', () => {
      const text = cb.dataset.warning || cb.dataset.error;
      const ignore = cb.checked;
      const url = cb.dataset.warning ? '/toggle_warning' : '/toggle_error';
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, ignore })
      }).then(() => {
        const p = cb.parentElement.querySelector('p');
        if (p) {
          const activeClass = cb.dataset.warning ? 'text-yellow-700' : 'text-red-700';
          if (ignore) {
            p.classList.remove(activeClass);
            p.classList.add('text-gray-400');
          } else {
            p.classList.add(activeClass);
            p.classList.remove('text-gray-400');
          }
        }
      });
    });
  });
});
