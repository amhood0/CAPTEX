window.bindArtifactUpload = function (button) {
    button.addEventListener('click', async () => {
        const input = document.getElementById(button.dataset.fileInput);
        const select = document.getElementById(button.dataset.artifactSelect);
        const status = document.getElementById(button.dataset.statusTarget);
        if (!input.files.length) { status.textContent = 'Choose a ZIP file first.'; return; }
        button.disabled = true; status.textContent = 'Uploading and validating...';
        try {
            const file = input.files[0];
            const response = await fetch('/api/artifacts', {method: 'POST', headers: {
                'Content-Type': 'application/zip', 'X-CAPTEX-Filename': encodeURIComponent(file.name)
            }, body: file});
            const body = await response.json();
            if (!response.ok) throw new Error(window.apiErrorMessage(body));
            document.querySelectorAll('select[data-artifact-picker]').forEach(item => {
                item.add(new Option(`${body.name} (uploaded)`, body.id));
            });
            select.value = body.id;
            status.textContent = 'Upload ready.';
        } catch (error) { status.textContent = error.message; }
        finally { button.disabled = false; }
    });
};
document.querySelectorAll('[data-artifact-upload]').forEach(window.bindArtifactUpload);
