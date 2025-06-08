const socket = io();

const headEl = document.getElementById('simHead');
const bodyEl = document.getElementById('simBody');
const tableEl = document.getElementById('simTable');
const loadingEl = document.getElementById('loading');

socket.on('connect', () => {
  socket.emit('start_similarity');
});

socket.on('similarity_result', (data) => {
  loadingEl.style.display = 'none';
  tableEl.classList.remove('hidden');
  headEl.innerHTML = '';
  bodyEl.innerHTML = '';

  const headRow = document.createElement('tr');
  const emptyTh = document.createElement('th');
  emptyTh.className = 'border px-2 py-1 text-left';
  headRow.appendChild(emptyTh);
  data.courses.forEach((name) => {
    const th = document.createElement('th');
    th.className = 'border px-2 py-1 text-left';
    th.textContent = name;
    headRow.appendChild(th);
  });
  headEl.appendChild(headRow);

  data.matrix.forEach((row, idx) => {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.className = 'border px-2 py-1 text-left whitespace-nowrap';
    th.textContent = data.courses[idx];
    tr.appendChild(th);
    row.forEach((val) => {
      const td = document.createElement('td');
      td.className = 'border px-2 py-1 text-center';
      if (val > 0.8) {
        td.classList.add('bg-red-300');
      } else if (val > 0.6) {
        td.classList.add('bg-orange-300');
      } else {
        td.classList.add('bg-gray-200');
      }
      td.textContent = val.toFixed(2);
      tr.appendChild(td);
    });
    bodyEl.appendChild(tr);
  });
});

window.addEventListener('beforeunload', () => {
  socket.disconnect();
});
