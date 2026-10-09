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
        return; document.getElementById('reviewSvg')?.setAttribute('aria-label', 'Kotak anotasi tersimpan. Akun viewer hanya dapat melihat.'); for (const id of ['newVideoButton', 'emptyUploadButton', 'uploadButton', 'reanalyzeButton', 'retryJob', 'cancelJob', 'saveReview', 'suggestBoxes', 'applyBoxButton', 'learnDetector', 'exportCorrectedVideo', 'cancelExport', 'cancelLearning', 'startTraining', 'openReview', 'prepareCorrections', 'resultCorrections', 'reviewPlayback', 'boxControls', 'metadataControls']) {
        const node = document.getElementById(id);
        if ((node instanceof HTMLButtonElement || node instanceof HTMLFieldSetElement || node instanceof HTMLInputElement) && !node.disabled)
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
    function renderProfile() {
        if (!session)
            return;
        const user = session.user, initials = Array.from(user.username.trim()).slice(0, 2).join('').toLocaleUpperCase('id');
        for (const id of ['profileAvatar', 'accountAvatar'])
            el(id, HTMLElement).textContent = initials;
        el('accountIdentity', HTMLElement).textContent = user.username;
        el('profileUsername', HTMLElement).textContent = user.username;
        el('profileWorkspace', HTMLElement).textContent = user.tenant_name;
        el('profileRole', HTMLElement).textContent = { admin: 'Administrator', reviewer: 'Reviewer', viewer: 'Viewer' }[user.role];
    }
    function signedIn(value) { if (entered) {
        location.reload();
        return;
    } entered = true; session = value; gate.hidden = true; document.body.classList.remove('signed-out'); renderProfile(); applyRole(); }
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
        const alert = el('authError', HTMLElement);
        alert.textContent = reason instanceof Error ? reason.message : 'Gagal keluar.';
        alert.hidden = false;
    } };
    const passwordForm = el('passwordForm', HTMLFormElement);
    const passwordSubmit = el('passwordSubmit', HTMLButtonElement);
    let passwordPending = false;
    function resetPasswordForm() {
        passwordForm.reset();
        el('confirmPassword', HTMLInputElement).setCustomValidity('');
        el('passwordStatus', HTMLElement).textContent = '';
    }
    el('profileButton', HTMLButtonElement).onclick = async () => {
        if (!(await setView('profile')))
            return;
        resetPasswordForm();
        renderProfile();
        el('profileTitle', HTMLElement).focus();
    };
    el('confirmPassword', HTMLInputElement).oninput = () => el('confirmPassword', HTMLInputElement).setCustomValidity('');
    passwordForm.onsubmit = async (event) => {
        event.preventDefault();
        if (passwordPending)
            return;
        const status = el('passwordStatus', HTMLElement), confirmation = el('confirmPassword', HTMLInputElement);
        const newPassword = el('newPassword', HTMLInputElement).value;
        status.textContent = '';
        if (newPassword !== confirmation.value) {
            confirmation.setCustomValidity('Konfirmasi password tidak cocok.');
            status.textContent = 'Konfirmasi password tidak cocok.';
            confirmation.reportValidity();
            return;
        }
        confirmation.setCustomValidity('');
        if (!passwordForm.reportValidity())
            return;
        passwordPending = true;
        passwordSubmit.disabled = true;
        try {
            const response = await request('/api/auth/password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_password: el('currentPassword', HTMLInputElement).value, new_password: newPassword }) });
            const nextSession = await readSession(response);
            session = nextSession;
            resetPasswordForm();
            status.textContent = 'Password diperbarui. Sesi lain telah keluar; Anda tetap masuk di sini.';
        }
        catch (reason) {
            status.textContent = reason instanceof Error ? reason.message : 'Gagal mengubah password.';
        }
        finally {
            passwordPending = false;
            passwordSubmit.disabled = false;
        }
    };
    new MutationObserver(applyRole).observe(document.body, { subtree: true, attributes: true, attributeFilter: ['disabled'], childList: true });
    // ponytail: playback/editor remains JavaScript; migrate feature contracts when they change.
    return { ready, request, applyRole, resetPasswordForm, renderProfile };
})();
