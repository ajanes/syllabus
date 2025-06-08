 document.addEventListener('DOMContentLoaded', () => {
   document.querySelectorAll('input[data-warning]').forEach(cb => {
     cb.addEventListener('change', () => {
       const text = cb.dataset.warning;
       const ignore = cb.checked;
       fetch('/toggle_warning', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ text, ignore })
       }).then(() => {
         const p = cb.parentElement.querySelector('p');
         if (p) {
           if (ignore) {
             p.classList.remove('text-yellow-700');
             p.classList.add('text-gray-400');
           } else {
             p.classList.add('text-yellow-700');
             p.classList.remove('text-gray-400');
           }
         }
       });
     });
   });
 });
