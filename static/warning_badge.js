function updateWarningBadge() {
  fetch('/warning_stats')
    .then((r) => r.json())
    .then((data) => {
      const el = document.getElementById('warningsMenuText');
      if (!el) return;
      const total = (data.warnings || 0) + (data.errors || 0);
      el.textContent = total > 0 ? `Warnings (${total})` : 'Warnings';
    });
}

document.addEventListener('DOMContentLoaded', updateWarningBadge);
window.updateWarningBadge = updateWarningBadge;
