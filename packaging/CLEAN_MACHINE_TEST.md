# Clean Windows validation

Run this checklist on a Windows x64 machine or VM that does not have Python or the CAPTEX repository.

1. Install `CAPTEX-Setup-0.1.0.exe` as a standard user and leave **Launch CAPTEX** selected.
2. Confirm the browser opens `http://127.0.0.1:8000/setup` and the database check is ready.
3. Continue without VMware prerequisites and create a capability, plan, and manual run.
4. Close CAPTEX, launch it from the Start Menu, and confirm the saved records remain.
5. Launch CAPTEX a second time and confirm it opens the existing server rather than reporting a port conflict.
6. Install VMware Workstation Pro, Vagrant, and Vagrant VMware Utility from the setup links. Install the provider plugin and pinned box using the displayed commands.
7. Restart CAPTEX, run **Check prerequisites**, and confirm all checks pass.
8. Select the bundled Phase 6 demo, run its automated test, and confirm the VM returns to its prior power state.
9. Uninstall CAPTEX and confirm `%LOCALAPPDATA%\CAPTEX` remains available for backup or a later reinstall.

The build-time smoke test validates startup, migration, local storage, health, and setup-page rendering. This checklist covers installer behavior and third-party desktop integration that cannot be proven by the build host alone.
