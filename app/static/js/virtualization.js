let pollTimer;
function renderOperation(operation) {
    const running = operation.status === 'running';
    document.querySelectorAll('[data-vm-url]').forEach(button => button.disabled = running);
    document.getElementById('vmMessage').textContent = `${operation.status}: ${operation.message || 'No operation has run yet.'}`;
    document.getElementById('vmState').textContent = operation.vm ? `VM state: ${operation.vm.state} (checked ${operation.completed_at || operation.started_at})` : 'VM state: not checked by this operation';
    const checks = document.getElementById('vmChecks');
    checks.replaceChildren();
    for (const check of operation.readiness?.checks || []) {
        const entry = document.createElement('p');
        entry.textContent = `${check.ready ? 'Ready' : 'Missing'}: ${check.name}. ${check.ready ? '' : check.action}`;
        checks.append(entry);
        const details = document.createElement('details');
        const summary = document.createElement('summary');
        summary.textContent = `${check.name} details`;
        const output = document.createElement('pre');
        output.textContent = check.detail || '';
        details.append(summary, output);
        checks.append(details);
    }
    const output = [`Operation: ${operation.action || 'none'}`, `Started: ${operation.started_at || '-'}`, `Completed: ${operation.completed_at || '-'}`];
    for (const command of [operation.command, operation.vm?.command].filter(Boolean)) {
        output.push(`Command: ${(command.command || []).join(' ')}`, `Exit code: ${command.exit_code ?? 'unavailable'}`, command.stdout || '', command.stderr || '');
    }
    document.getElementById('vmOutput').textContent = output.join('\n');
    clearTimeout(pollTimer);
    if (running) pollTimer = setTimeout(refresh, 1500);
}
async function refresh() {
    try {
        const response = await fetch('/api/virtualization/operation');
        if (!response.ok) throw new Error('Could not read VM operation status. Reload this page to retry.');
        renderOperation(await response.json());
    } catch (error) { document.getElementById('vmError').textContent = error.message; }
}
document.querySelectorAll('[data-vm-url]').forEach(button => button.addEventListener('click', async () => {
    if (button.dataset.vmConfirm && !confirm(button.dataset.vmConfirm)) return;
    document.getElementById('vmError').textContent = '';
    document.querySelectorAll('[data-vm-url]').forEach(item => item.disabled = true);
    try {
        const response = await fetch(button.dataset.vmUrl, {method: 'POST'});
        const data = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(data));
        renderOperation(data);
    } catch (error) {
        document.getElementById('vmError').textContent = error.message;
        await refresh();
    }
}));
document.getElementById('registerVM')?.addEventListener('click', async event => {
    event.target.disabled = true;
    try {
        const response = await fetch('/api/virtualization/environment', {method: 'POST'});
        if (!response.ok) throw new Error(window.apiErrorMessage(await response.json()));
        location.reload();
    } catch (error) { document.getElementById('vmError').textContent = error.message; event.target.disabled = false; }
});
refresh();
