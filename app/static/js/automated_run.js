const automatedButton = document.getElementById('executeAutomated');
const progressCard = document.getElementById('automatedProgress');
const percentages = {queued: 5, provisioning: 20, configuring: 40, running: 65, collecting_results: 85, cleaning_up: 95};

async function pollAutomatedRun(runId) {
    try {
        const [operation, run] = await Promise.all([
            fetch('/api/automated-runs/operation').then(item => item.json()),
            fetch(`/api/test-runs/${runId}`).then(item => item.json()),
        ]);
        const percent = percentages[run.status] || 100;
        progressCard.hidden = false;
        const bar = document.getElementById('automatedProgressBar');
        if (bar) {
            bar.style.width = `${percent}%`;
            bar.textContent = `${percent}%`;
            document.getElementById('automatedProgressLabel').textContent = run.status.replaceAll('_', ' ');
            document.getElementById('automatedProgressMessage').textContent = operation.message || 'Automated execution is in progress.';
        }
        if (operation.status === 'running' && !['completed', 'failed'].includes(run.status)) return setTimeout(() => pollAutomatedRun(runId), 750);
        location.reload();
    } catch (error) {
        document.getElementById('automatedProgressMessage').textContent = `Could not refresh progress: ${error.message}`;
        setTimeout(() => pollAutomatedRun(runId), 2000);
    }
}

if (automatedButton) automatedButton.addEventListener('click', async () => {
    automatedButton.disabled = true;
    try {
        const response = await fetch(`/api/test-runs/${automatedButton.dataset.runId}/execute`, {method: 'POST'});
        const body = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(body));
        progressCard.hidden = false;
        pollAutomatedRun(automatedButton.dataset.runId);
    } catch (error) {
        const notice = document.getElementById('actionError');
        notice.textContent = error.message;
        notice.hidden = false;
        automatedButton.disabled = false;
    }
});

if (progressCard) fetch('/api/automated-runs/operation').then(item => item.json()).then(operation => {
    if (operation.status === 'running' && String(operation.test_run_id) === progressCard.dataset.runId) {
        progressCard.hidden = false;
        pollAutomatedRun(progressCard.dataset.runId);
    }
});
