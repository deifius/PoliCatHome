// Copy only visible, fixed command examples. Never execute or send commands to a server.
document.querySelectorAll('button[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const source = document.getElementById(button.dataset.copy);
    const feedback = document.getElementById('copyFeedback');
    if (!source) return;
    try {
      await navigator.clipboard.writeText(source.textContent);
      feedback.textContent = 'Commands copied. Inspect them in your own terminal before running.';
      button.textContent = 'Copied';
    } catch {
      feedback.textContent = 'Clipboard permission blocked. Select the command text and copy it manually.';
    }
  });
});
