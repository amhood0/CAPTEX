let automationPoll;

function renderAutomation(operation) {
    const running = operation.status === 'running';
    document.querySelectorAll('[data-automation-url]').forEach(button => button.disabled = running);
    document.getElementById('automationMessage').textContent = `${operation.status}: ${operation.message || 'No operation has run yet.'}`;
    const steps = document.getElementById('automationSteps');
    steps.replaceChildren();
    for (const step of operation.details?.steps || []) {
        const item = document.createElement('li');
        item.textContent = `${step.name}: ${step.timed_out ? 'timed out' : `exit ${step.exit_code ?? 'unavailable'}`}`;
        steps.append(item);
    }
    const output = [];
    for (const step of operation.details?.steps || []) {
        output.push(`--- ${step.name} ---`, `Command: ${(step.command || []).join(' ')}`,
                    `Exit code: ${step.exit_code ?? 'unavailable'}`, step.stdout || '', step.stderr || '');
    }
    document.getElementById('automationOutput').textContent = output.join('\n');
    clearTimeout(automationPoll);
    if (running) automationPoll = setTimeout(refreshAutomation, 1500);
}

async function refreshAutomation() {
    try {
        const response = await fetch('/api/automation/operation');
        if (!response.ok) throw new Error('Could not read the Ansible operation. Reload this page to retry.');
        renderAutomation(await response.json());
    } catch (error) {
        document.getElementById('automationError').textContent = error.message;
    }
}

document.querySelectorAll('[data-automation-url]').forEach(button => button.addEventListener('click', async () => {
    document.getElementById('automationError').textContent = '';
    document.querySelectorAll('[data-automation-url]').forEach(item => item.disabled = true);
    try {
        const response = await fetch(button.dataset.automationUrl, {method: 'POST'});
        const data = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(data));
        renderAutomation(data);
    } catch (error) {
        document.getElementById('automationError').textContent = error.message;
        await refreshAutomation();
    }
}));

refreshAutomation();
