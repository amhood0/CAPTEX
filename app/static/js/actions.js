window.apiErrorMessage = function (error) {
    if (typeof error.detail === 'string') return error.detail;
    if (Array.isArray(error.detail)) return error.detail.map(item => `${item.loc.slice(1).join('.')}: ${item.msg}`).join('; ');
    return 'The request failed. Please try again.';
};
document.addEventListener('click', async event => {
    const button = event.target.closest('[data-api-action]');
    if (!button) return;
    if (button.dataset.confirm && !confirm(button.dataset.confirm)) return;
    button.disabled = true;
    try {
        const response = await fetch(button.dataset.apiAction, {method: button.dataset.method || 'DELETE'});
        if (!response.ok) {
            const error = await response.json();
            throw new Error(window.apiErrorMessage(error));
        }
        location.reload();
    } catch (error) { const notice = document.getElementById('actionError'); notice.textContent = error.message; notice.hidden = false; notice.focus(); button.disabled = false; }
});
