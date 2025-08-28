async function pollProgress(jobId) {
  const label = document.getElementById('label');
  const bar = document.getElementById('bar');
  const ready = document.getElementById('ready');
  const error = document.getElementById('error');

  async function tick() {
    try {
      const res = await fetch(`/api/progress/${jobId}`);
      const data = await res.json();
      if (data.error) {
        error.textContent = data.error;
        error.classList.remove('hide');
        return;
      }
      bar.style.width = (data.progress || 0) + '%';
      label.textContent = data.message || '';
      if (data.error) {
        error.textContent = data.error;
        error.classList.remove('hide');
      }
      if (data.ready) {
        ready.classList.remove('hide');
        return; // stop polling
      }
    } catch (e) {
      console.error(e);
    }
    setTimeout(tick, 1000);
  }
  tick();
}

if (window.JOB_ID) {
  pollProgress(window.JOB_ID);
}
