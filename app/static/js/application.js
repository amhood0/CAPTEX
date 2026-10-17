document.getElementById('exitCaptex')?.addEventListener('click', async event => {
    if (!confirm('Exit CAPTEX? Your database and uploaded artifacts will be preserved.')) return;
    event.target.disabled = true;
    try {
        const response = await fetch('/api/application/exit', {method: 'POST'});
        const data = await response.json();
        if (!response.ok) throw new Error(window.apiErrorMessage(data));
        document.body.innerHTML = '<main class="container py-5"><h1>CAPTEX has stopped</h1><p>Your data was saved. You can close this tab and launch CAPTEX again when needed.</p></main>';
        window.close();
    } catch (error) {
        const notice = document.getElementById('actionError');
        notice.textContent = error.message;
        notice.hidden = false;
        notice.focus();
        event.target.disabled = false;
    }
});
