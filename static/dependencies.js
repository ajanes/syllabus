const socket = io();

const targetSelect = document.getElementById('targetCourse');
const yearSelect = document.getElementById('yearSelect');
const semesterSelect = document.getElementById('semesterSelect');
const courseSelect = document.getElementById('courseSelect');
const topicsContainer = document.getElementById('topicsContainer');
const topicsHeader = document.getElementById('topicsHeader');
const commentContainer = document.getElementById('commentContainer');
const commentInput = document.getElementById('courseComment');
let currentDependencies = [];
let currentTopics = [];
let presetCourse = null;

function updateControlBackgrounds(root = document) {
  root
    .querySelectorAll('input:not([type="checkbox"]), select, textarea')
    .forEach((el) => {
      if (el.disabled) {
        el.classList.remove('bg-white');
      } else {
        el.classList.add('bg-white');
      }
    });
}

function updateDropdownState() {
  const disabled = !targetSelect.value;
  yearSelect.disabled = disabled;
  semesterSelect.disabled = disabled;
  courseSelect.disabled = disabled;
  updateControlBackgrounds();
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
    if (presetCourse ? c.id === presetCourse : c.id === data.selected_course)
      opt.selected = true;
    courseSelect.appendChild(opt);
  });
  if (presetCourse) {
    courseSelect.value = presetCourse;
    presetCourse = null;
    courseSelect.dispatchEvent(new Event('change'));
  }
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
    wrapper.className = 'flex gap-4 px-4 py-3 justify-between';
    wrapper.dataset.baseTopic = t;
    wrapper.dataset.topicIndex = idx + 1;
    wrapper.innerHTML = `<div class="flex items-start gap-4">
        <div class="flex size-7 items-center justify-center">
          <input type="checkbox" data-topic="${idx + 1}" class="h-5 w-5 rounded border-[#dbdbdb] border-2 bg-transparent text-black checked:bg-black checked:border-black checked:bg-[image:--checkbox-tick-svg] focus:ring-0 focus:ring-offset-0 focus:border-[#dbdbdb] focus:outline-none" />
        </div>
        <div class="flex flex-1 flex-col justify-center">
          <p class="text-[#141414] text-base font-medium leading-normal">${t}</p>
          <input placeholder="Subtopic" class="form-input mt-1 w-[300px] resize-none overflow-hidden rounded-xl text-[#141414] focus:outline-0 focus:ring-0 border border-[#dbdbdb] focus:border-[#dbdbdb] h-10 placeholder:text-neutral-500 p-[10px] text-sm font-normal leading-normal" />
          <input placeholder="Add notes here" class="form-input mt-1 w-[300px] resize-none overflow-hidden rounded-xl text-[#141414] focus:outline-0 focus:ring-0 border border-[#dbdbdb] focus:border-[#dbdbdb] h-10 placeholder:text-neutral-500 p-[10px] text-sm font-normal leading-normal" />
        </div>
      </div>`;
    const checkbox = wrapper.querySelector('input[type="checkbox"]');
    const subInput = wrapper.querySelector('input[placeholder="Subtopic"]');
    const noteInput = wrapper.querySelector('input[placeholder="Add notes here"]');

    checkbox.addEventListener('change', (e) => {
      if (e.target.checked) {
        const sub = subInput.value.trim();
        const note = noteInput.value.trim();
        socket.emit('add_dependency', {
          target_id: targetSelect.value,
          source_id: courseSelect.value,
          base_topic: wrapper.dataset.topicIndex,
          subtopic: sub,
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
        subtopic: sub,
        note: note,
      });
      wrapper.dataset.storedTopic = sub || t;
    }

    subInput.addEventListener('blur', sendUpdate);
    noteInput.addEventListener('blur', sendUpdate);

    topicsContainer.appendChild(wrapper);
    updateControlBackgrounds(wrapper);
  });
  applyDependencies();
  updateControlBackgrounds();
}

function applyDependencies() {
  const courseName = courseSelect.options[courseSelect.selectedIndex]?.textContent || '';
  commentContainer.style.display = courseSelect.value ? 'block' : 'none';
  commentInput.value = '';
  document.querySelectorAll('#topicsContainer > div').forEach((wrapper) => {
    const base = wrapper.dataset.baseTopic;
    const baseIdx = parseInt(wrapper.dataset.topicIndex, 10);
    const checkbox = wrapper.querySelector('input[type="checkbox"]');
    const subInput = wrapper.querySelector('input[placeholder="Subtopic"]');
    const noteInput = wrapper.querySelector('input[placeholder="Add notes here"]');
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
            if (t['subtopic']) {
              subInput.value = t['subtopic'];
              wrapper.dataset.storedTopic = t['subtopic'];
            } else {
              wrapper.dataset.storedTopic = base;
            }
            if (t.note) noteInput.value = t.note;
          }
        });
      }
    });
  });
  updateControlBackgrounds();
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
  const params = new URLSearchParams(window.location.search);
  if (params.has('target')) {
    targetSelect.value = params.get('target');
  }
  if (params.has('year')) {
    yearSelect.value = params.get('year');
  }
  if (params.has('semester')) {
    semesterSelect.value = params.get('semester');
  }
  if (params.has('source')) {
    presetCourse = params.get('source');
  }
  updateDropdownState();
  requestUpdate();
  updateControlBackgrounds();
  loadDependencies();
});

socket.on('saved', () => {
  if (window.updateWarningBadge) window.updateWarningBadge();
});

commentInput.addEventListener('blur', () => {
  if (!targetSelect.value || !courseSelect.value) return;
  socket.emit('update_comment', {
    target_id: targetSelect.value,
    source_id: courseSelect.value,
    comment: commentInput.value.trim(),
  });
});
