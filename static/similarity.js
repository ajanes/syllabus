const socket = io();

const headEl = document.getElementById('simHead');
const bodyEl = document.getElementById('simBody');
const tableEl = document.getElementById('simTable');
const loadingEl = document.getElementById('loading');
const progressEl = document.getElementById('progress');
const recalcBtn = document.getElementById('recalcBtn');
const initData = JSON.parse(document.getElementById('init-data').textContent);

function buildTable(data) {
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
    th.className = 'border px-2 py-1 text-left';
    th.textContent = data.courses[idx];
    tr.appendChild(th);
    row.forEach((val, j) => {
      const td = document.createElement('td');
      td.className = 'border px-2 py-1 text-center';
      if (data.colors && data.colors[idx] && data.colors[idx][j]) {
        td.style.backgroundColor = data.colors[idx][j];
      }
      td.textContent = val.toFixed(2);
      tr.appendChild(td);
    });
    bodyEl.appendChild(tr);
  });
}

buildTable(initData);

recalcBtn.addEventListener('click', () => {
  loadingEl.classList.remove('hidden');
  progressEl.textContent = '0%';
  socket.emit('start_similarity', { force: true });
});

socket.on('similarity_progress', (data) => {
  if (progressEl) {
    progressEl.textContent = data.progress + '%';
  }
});

socket.on('similarity_result', (data) => {
  loadingEl.classList.add('hidden');
  if (progressEl) {
    progressEl.textContent = '100%';
  }
  buildTable(data);
});

window.addEventListener('beforeunload', () => {
  socket.disconnect();
});
