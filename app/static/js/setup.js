let setupTimer;

function showSetupOperation(operation) {
    const running = operation.status === 'running';
    document.getElementById('checkSetup').disabled = running;
    document.getElementById('setupStatus').textContent = operation.message || 'No prerequisite check has run yet.';
    const checks = document.getElementById('setupChecks');
    checks.replaceChildren();
    for (const check of operation.readiness?.checks || []) {
        const item = document.createElement('div');
        item.className = `alert ${check.ready ? 'alert-success' : 'alert-warning'} py-2`;
        item.textContent = `${check.ready ? 'Ready' : 'Missing'}: ${check.name}${check.ready ? '' : `. ${check.action}`}`;
        checks.append(item);
    }
    const output = [];
    for (const check of operation.readiness?.checks || []) output.push(`${check.name}: ${check.detail || ''}`);
    document.getElementById('setupOutput').textContent = output.join('\n\n');
    clearTimeout(setupTimer);
    if (running) setupTimer = setTimeout(refreshSetup, 1000);
}

async function refreshSetup() {
    try {
        const response = await fetch('/api/virtualization/operation');
        if (!response.ok) throw new Error('Could not read prerequisite status.');
        showSetupOperation(await response.json());
    } catch (error) {
        document.getElementById('setupError').textContent = error.message;
    }
}

document.getElementById('checkSetup').addEventListener('click', async () => {
    document.getElementById('setupError').textContent = '';
    document.getElementById('checkSetup').disabled = true;
    try {
        const response = await fetch('/api/virtualization/check', {method: 'POST'});
        const data = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(data));
        showSetupOperation(data);
    } catch (error) {
        document.getElementById('setupError').textContent = error.message;
        document.getElementById('checkSetup').disabled = false;
    }
});

document.getElementById('finishSetup').addEventListener('click', async () => {
    try {
        const response = await fetch('/api/setup/complete', {method: 'POST'});
        const data = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(data));
        location.assign(data.redirect);
    } catch (error) {
        document.getElementById('setupError').textContent = error.message;
    }
});

document.querySelectorAll('[data-setup-install]').forEach(button => button.addEventListener('click', async () => {
    document.getElementById('setupError').textContent = '';
    document.querySelectorAll('[data-setup-install]').forEach(item => item.disabled = true);
    try {
        const response = await fetch(`/api/virtualization/install/${button.dataset.setupInstall}`, {method: 'POST'});
        const data = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(data));
        showSetupOperation(data);
    } catch (error) {
        document.getElementById('setupError').textContent = error.message;
    } finally {
        document.querySelectorAll('[data-setup-install]').forEach(item => item.disabled = false);
    }
}));

refreshSetup();
