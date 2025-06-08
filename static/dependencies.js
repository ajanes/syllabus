const socket = io();

const targetSelect = document.getElementById('targetCourse');
const yearSelect = document.getElementById('yearSelect');
const semesterSelect = document.getElementById('semesterSelect');
const courseSelect = document.getElementById('courseSelect');
const topicsContainer = document.getElementById('topicsContainer');
const topicsHeader = document.getElementById('topicsHeader');
const commentInput = document.getElementById('courseComment');
let currentDependencies = [];
let currentTopics = [];

function updateDropdownState() {
  const disabled = !targetSelect.value;
  yearSelect.disabled = disabled;
  semesterSelect.disabled = disabled;
  courseSelect.disabled = disabled;
}

function requestUpdate() {
  socket.emit('filter', {
    year: yearSelect.value,
    semester: semesterSelect.value,
    course: courseSelect.value,
  });
}

function loadDependencies() {
  if (!targetSelect.value) return;
  socket.emit('get_dependencies', { target_id: targetSelect.value });
}

socket.on('dependencies', (data) => {
  if (data.target_id !== targetSelect.value) return;
  currentDependencies = data.dependencies || [];
  applyDependencies();
});

socket.on('filtered', (data) => {
  courseSelect.innerHTML = '<option value="">Select a Course</option>';
  data.courses.forEach((c) => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    if (c.id === data.selected_course) opt.selected = true;
    courseSelect.appendChild(opt);
  });
  currentTopics = data.topics;
  renderTopics(currentTopics);
  loadDependencies();
});

function renderTopics(topics) {
  topicsContainer.innerHTML = '';
  if (!topics || topics.length === 0) {
    topicsHeader.style.display = 'none';
    return;
  }
  topicsHeader.style.display = 'block';
  topics.forEach((t, idx) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'flex gap-4 bg-neutral-50 px-4 py-3 justify-between';
    wrapper.dataset.baseTopic = t;
    wrapper.dataset.topicIndex = idx + 1;
    wrapper.innerHTML = `<div class="flex items-start gap-4">
        <div class="flex size-7 items-center justify-center">
          <input type="checkbox" data-topic="${idx + 1}" class="h-5 w-5 rounded border-[#dbdbdb] border-2 bg-transparent text-black checked:bg-black checked:border-black checked:bg-[image:--checkbox-tick-svg] focus:ring-0 focus:ring-offset-0 focus:border-[#dbdbdb] focus:outline-none" />
        </div>
        <div class="flex flex-1 flex-col justify-center">
          <p class="text-[#141414] text-base font-medium leading-normal">${t}</p>
          <textarea placeholder="Subtopic" rows="2" class="form-input mt-1 w-[300px] resize-none overflow-hidden rounded-xl text-[#141414] focus:outline-0 focus:ring-0 border border-[#dbdbdb] bg-neutral-50 focus:border-[#dbdbdb] h-20 placeholder:text-neutral-500 p-[10px] text-sm font-normal leading-normal"></textarea>
          <textarea placeholder="Add notes here" rows="3" class="form-input mt-1 w-[300px] resize-none overflow-hidden rounded-xl text-[#141414] focus:outline-0 focus:ring-0 border border-[#dbdbdb] bg-neutral-50 focus:border-[#dbdbdb] h-24 placeholder:text-neutral-500 p-[10px] text-sm font-normal leading-normal"></textarea>
        </div>
      </div>`;
    const checkbox = wrapper.querySelector('input[type="checkbox"]');
    const subInput = wrapper.querySelector('textarea[placeholder="Subtopic"]');
    const noteInput = wrapper.querySelector('textarea[placeholder="Add notes here"]');

    checkbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        const sub = subInput.value.trim();
        const note = noteInput.value.trim();
        socket.emit('add_dependency', {
          target_id: targetSelect.value,
          source_id: courseSelect.value,
          base_topic: wrapper.dataset.topicIndex,
          sub_topic: sub,
          note: note,
        });
        wrapper.dataset.storedTopic = sub || t;
      } else {
        socket.emit('remove_dependency', {
          target_id: targetSelect.value,
          source_id: courseSelect.value,
          base_topic: wrapper.dataset.topicIndex,
        });
        wrapper.dataset.storedTopic = '';
        subInput.value = '';
        noteInput.value = '';
      }
    });

    function sendUpdate() {
      if (!checkbox.checked) return;
      const sub = subInput.value.trim();
      const note = noteInput.value.trim();
      socket.emit('update_dependency', {
        target_id: targetSelect.value,
        source_id: courseSelect.value,
        base_topic: wrapper.dataset.topicIndex,
        sub_topic: sub,
        note: note,
      });
      wrapper.dataset.storedTopic = sub || t;
    }

    subInput.addEventListener('blur', sendUpdate);
    noteInput.addEventListener('blur', sendUpdate);

    topicsContainer.appendChild(wrapper);
  });
  applyDependencies();
}

function applyDependencies() {
  const courseName = courseSelect.options[courseSelect.selectedIndex]?.textContent || '';
  commentInput.value = '';
  document.querySelectorAll('#topicsContainer > div').forEach((wrapper) => {
    const base = wrapper.dataset.baseTopic;
    const baseIdx = parseInt(wrapper.dataset.topicIndex, 10);
    const checkbox = wrapper.querySelector('input[type="checkbox"]');
    const subInput = wrapper.querySelector('textarea[placeholder="Subtopic"]');
    const noteInput = wrapper.querySelector('textarea[placeholder="Add notes here"]');
    checkbox.checked = false;
    wrapper.dataset.storedTopic = base;
    subInput.value = '';
    noteInput.value = '';
    currentDependencies.forEach((dep) => {
      if (dep.course === courseName) {
        if (dep.comment) commentInput.value = dep.comment;
        (dep.topics || []).forEach((t) => {
          if (parseInt(t.topic, 10) === baseIdx) {
            checkbox.checked = true;
            if (t['sub-topic']) {
              subInput.value = t['sub-topic'];
              wrapper.dataset.storedTopic = t['sub-topic'];
            } else {
              wrapper.dataset.storedTopic = base;
            }
            if (t.note) noteInput.value = t.note;
          }
        });
      }
    });
  });
}

yearSelect.addEventListener('change', requestUpdate);
semesterSelect.addEventListener('change', requestUpdate);
courseSelect.addEventListener('change', () => {
  requestUpdate();
  loadDependencies();
  applyDependencies();
});
targetSelect.addEventListener('change', () => {
  updateDropdownState();
  loadDependencies();
  applyDependencies();
});

document.addEventListener('DOMContentLoaded', () => {
  updateDropdownState();
  requestUpdate();
});

commentInput.addEventListener('blur', () => {
  if (!targetSelect.value || !courseSelect.value) return;
  socket.emit('update_comment', {
    target_id: targetSelect.value,
    source_id: courseSelect.value,
    comment: commentInput.value.trim(),
  });
});
