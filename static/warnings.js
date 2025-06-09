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
        const wrapper = cb.parentElement;
        const p = wrapper.querySelector('p');
        if (p) {
          const activeText = cb.dataset.warning ? 'text-yellow-700' : 'text-red-700';
          const activeBg = cb.dataset.warning ? 'bg-yellow-50' : 'bg-red-50';
          if (ignore) {
            p.classList.remove(activeText);
            p.classList.add('text-gray-400');
            wrapper.classList.remove(activeBg);
            wrapper.classList.add('bg-gray-100');
          } else {
            p.classList.add(activeText);
            p.classList.remove('text-gray-400');
            wrapper.classList.add(activeBg);
            wrapper.classList.remove('bg-gray-100');
          }
        }
        if (window.updateWarningBadge) window.updateWarningBadge();
      });
    });
  });
});
