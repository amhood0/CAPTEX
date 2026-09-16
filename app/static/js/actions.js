document.addEventListener('click', async event => {
    const button = event.target.closest('[data-api-action]');
    if (!button) return;
    if (button.dataset.confirm && !confirm(button.dataset.confirm)) return;
    button.disabled = true;
    try {
        const response = await fetch(button.dataset.apiAction, {method: button.dataset.method || 'DELETE'});
        if (!response.ok) {
            const error = await response.json();
            throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
        }
        location.reload();
    } catch (error) { alert(error.message); button.disabled = false; }
});
