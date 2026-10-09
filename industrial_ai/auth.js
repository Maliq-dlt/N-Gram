"use strict";
const workspaceAuth = (() => {
    let session = null;
    let entered = false;
    const nativeFetch = window.fetch.bind(window);
    function el(id, type) { const node = document.getElementById(id); if (!(node instanceof type))
        throw new Error(`Missing element ${id}`); return node; }
    const gate = el('authGate', HTMLElement);
    document.getElementById('reviewSvg')?.addEventListener('pointerdown', event => { if (session?.user.role === 'viewer') {
        event.preventDefault();
        event.stopImmediatePropagation();
    } }, true);
    function showLogin() { session = null; gate.hidden = false; document.body.classList.add('signed-out'); el('loginUsername', HTMLInputElement).focus(); }
    function applyRole() { if (session?.user.role !== 'viewer')
        return; document.getElementById('reviewSvg')?.setAttribute('aria-label', 'Kotak anotasi tersimpan. Akun viewer hanya dapat melihat.'); for (const id of ['newVideoButton', 'emptyUploadButton', 'uploadButton', 'reanalyzeButton', 'retryJob', 'cancelJob', 'saveReview', 'suggestBoxes', 'applyBoxButton', 'learnDetector', 'exportCorrectedVideo', 'cancelExport', 'cancelLearning', 'startTraining', 'openReview', 'prepareCorrections', 'reviewPlayback', 'boxControls', 'metadataControls']) {
        const node = document.getElementById(id);
        if ((node instanceof HTMLButtonElement || node instanceof HTMLFieldSetElement) && !node.disabled)
            node.disabled = true;
    } for (const node of document.querySelectorAll('[data-view=annotation]')) {
        if (!node.disabled)
            node.disabled = true;
        node.title = 'Viewer dapat melihat hasil; koreksi membutuhkan reviewer.';
    } for (const node of document.querySelectorAll('#boxList button'))
        if (!node.disabled)
            node.disabled = true; }
    async function request(input, init = {}) { const headers = new Headers(init.headers), method = (init.method || 'GET').toUpperCase(); if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        if (!session) {
            showLogin();
            throw new Error('Silakan masuk kembali.');
        }
        const url = input instanceof Request ? input.url : String(input);
        if (session.user.role === 'viewer' && !url.includes('/api/auth/') && url !== '/api/chat')
            throw new Error('Akun viewer hanya dapat melihat hasil.');
        headers.set('X-CSRF-Token', session.csrf_token);
    } const response = await nativeFetch(input, { ...init, headers, credentials: 'same-origin' }); if (response.status === 401)
        showLogin(); return response; }
    async function readSession(response) { const data = await response.json(); if (!response.ok)
        throw new Error(typeof data === 'object' && data !== null && 'detail' in data ? String(data.detail) : 'Tidak dapat masuk.'); if (typeof data !== 'object' || data === null || !('user' in data) || !('csrf_token' in data))
        throw new Error('Respons sesi tidak valid.'); const user = data.user; if (typeof user !== 'object' || user === null || !('role' in user) || !['admin', 'reviewer', 'viewer'].includes(String(user.role)) || typeof data.csrf_token !== 'string' || !data.csrf_token)
        throw new Error('Respons sesi tidak valid.'); for (const field of ['id', 'username', 'tenant_id', 'tenant_name'])
        if (!(field in user) || typeof Reflect.get(user, field) !== 'string')
            throw new Error('Respons akun tidak valid.'); return data; }
    function signedIn(value) { if (entered) {
        location.reload();
        return;
    } entered = true; session = value; gate.hidden = true; document.body.classList.remove('signed-out'); el('accountIdentity', HTMLElement).textContent = `${value.user.tenant_name} · ${value.user.username} (${value.user.role})`; applyRole(); }
    const ready = (async () => { try {
        signedIn(await readSession(await nativeFetch('/api/auth/session', { credentials: 'same-origin' })));
    }
    catch {
        showLogin();
        await new Promise(resolve => document.addEventListener('workspace-login', () => resolve(), { once: true }));
    } })();
    el('loginForm', HTMLFormElement).onsubmit = async (event) => { event.preventDefault(); const button = el('loginSubmit', HTMLButtonElement), error = el('loginError', HTMLElement); button.disabled = true; error.hidden = true; try {
        signedIn(await readSession(await nativeFetch('/api/auth/login', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: el('loginUsername', HTMLInputElement).value, password: el('loginPassword', HTMLInputElement).value }) })));
        el('loginPassword', HTMLInputElement).value = '';
        document.dispatchEvent(new Event('workspace-login'));
    }
    catch (reason) {
        error.textContent = reason instanceof Error ? reason.message : 'Tidak dapat masuk.';
        error.hidden = false;
    }
    finally {
        button.disabled = false;
    } };
    el('logoutButton', HTMLButtonElement).onclick = async () => { try {
        const response = await request('/api/auth/logout', { method: 'POST' });
        if (!response.ok)
            throw new Error('Gagal keluar.');
        location.reload();
    }
    catch (reason) {
        el('systemStatus', HTMLElement).textContent = reason instanceof Error ? reason.message : 'Gagal keluar.';
    } };
    const dialog = el('passwordDialog', HTMLDialogElement);
    el('passwordButton', HTMLButtonElement).onclick = () => dialog.showModal();
    el('closePassword', HTMLButtonElement).onclick = () => dialog.close();
    el('passwordForm', HTMLFormElement).onsubmit = async (event) => { event.preventDefault(); const status = el('passwordStatus', HTMLElement); try {
        const response = await request('/api/auth/password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_password: el('currentPassword', HTMLInputElement).value, new_password: el('newPassword', HTMLInputElement).value }) });
        if (!response.ok) {
            const data = await response.json();
            throw new Error(typeof data === 'object' && data !== null && 'detail' in data ? String(data.detail) : 'Gagal mengubah password.');
        }
        el('passwordForm', HTMLFormElement).reset();
        status.textContent = 'Password diperbarui.';
    }
    catch (reason) {
        status.textContent = reason instanceof Error ? reason.message : 'Gagal mengubah password.';
    } };
    new MutationObserver(applyRole).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['disabled'], childList: true });
    // ponytail: playback/editor remains JavaScript; migrate feature contracts when they change.
    return { ready, request, applyRole };
})();
