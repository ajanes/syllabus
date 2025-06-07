const socket = io();

const targetSelect = document.getElementById('targetCourse');
const yearSelect = document.getElementById('yearSelect');
const semesterSelect = document.getElementById('semesterSelect');
const courseSelect = document.getElementById('courseSelect');
const topicsContainer = document.getElementById('topicsContainer');
const topicsHeader = document.getElementById('topicsHeader');

function requestUpdate() {
  socket.emit('filter', {
    year: yearSelect.value,
    semester: semesterSelect.value,
    course: courseSelect.value,
  });
}

socket.on('filtered', (data) => {
  courseSelect.innerHTML = '<option value="">Select a Course</option>';
  data.courses.forEach((c) => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    if (c.id === data.selected_course) opt.selected = true;
    courseSelect.appendChild(opt);
  });
  renderTopics(data.topics);
});

function renderTopics(topics) {
  topicsContainer.innerHTML = '';
  if (!topics || topics.length === 0) {
    topicsHeader.style.display = 'none';
    return;
  }
  topicsHeader.style.display = 'block';
  topics.forEach((t) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex gap-4 bg-neutral-50 px-4 py-3 justify-between';
    wrapper.innerHTML = `<div class="flex items-start gap-4">
        <div class="flex size-7 items-center justify-center">
          <input type="checkbox" data-topic="${t}" class="h-5 w-5 rounded border-[#dbdbdb] border-2 bg-transparent text-black checked:bg-black checked:border-black checked:bg-[image:--checkbox-tick-svg] focus:ring-0 focus:ring-offset-0 focus:border-[#dbdbdb] focus:outline-none" />
        </div>
        <div class="flex flex-1 flex-col justify-center">
          <p class="text-[#141414] text-base font-medium leading-normal">${t}</p>
          <input placeholder="Subtopic" class="form-input mt-1 flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#141414] focus:outline-0 focus:ring-0 border border-[#dbdbdb] bg-neutral-50 focus:border-[#dbdbdb] h-10 placeholder:text-neutral-500 p-[10px] text-sm font-normal leading-normal" />
          <input placeholder="Add notes here" class="form-input mt-1 flex w-full min-w-0 flex-1 resize-none overflow-hidden rounded-xl text-[#141414] focus:outline-0 focus:ring-0 border border-[#dbdbdb] bg-neutral-50 focus:border-[#dbdbdb] h-10 placeholder:text-neutral-500 p-[10px] text-sm font-normal leading-normal" />
        </div>
      </div>`;
    wrapper.querySelector('input[type="checkbox"]').addEventListener('change', (e) => {
      if (e.target.checked) {
        socket.emit('add_dependency', {
          target_id: targetSelect.value,
          topic: t,
        });
      }
    });
    topicsContainer.appendChild(wrapper);
  });
}

yearSelect.addEventListener('change', requestUpdate);
semesterSelect.addEventListener('change', requestUpdate);
courseSelect.addEventListener('change', requestUpdate);

document.addEventListener('DOMContentLoaded', () => {
  requestUpdate();
});
