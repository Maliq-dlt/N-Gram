export function AccountGate() {
  return (
    <>
    <div id="loginTransitionLoader" className="login-transition-loader" hidden>
          <div className="loader-heading"><svg viewBox="0 0 256 256" className="brand-mark" aria-hidden="true"><path fill="currentColor" d="M32 40h40l56 128 56-128h40l-80 176h-32zM112 40h32v64h-32z"/></svg><span>VIDEO INSIGHT</span></div>
          <h1>Menyiapkan studio Anda.</h1>
          <p id="loginTransitionStatus" role="status">Memuat rekaman dan pengaturan workspace…</p>
          <canvas id="loginCrowdCanvas" width="900" height="280" aria-hidden="true"></canvas>
          <button id="loginTransitionRetry" className="button button--primary" type="button" hidden>Coba lagi</button>
        </div>
    <section id="authGate" className="auth-gate" aria-labelledby="loginTitle" hidden>
          <form id="loginForm" className="auth-card auth-card-modern">
            <div className="auth-logo"><svg viewBox="0 0 256 256" className="brand-mark" aria-hidden="true"><path fill="currentColor" d="M32 40h40l56 128 56-128h40l-80 176h-32zM112 40h32v64h-32z"/></svg></div>
            <p className="eyebrow">VIDEO INSIGHT STUDIO</p>
            <h1 id="loginTitle">Selamat datang kembali.</h1>
            <p className="auth-intro">Rekaman, koreksi, dan insight. Dalam satu workspace.</p>
            <label htmlFor="loginUsername">Username</label>
            <input className="input" id="loginUsername" autoComplete="username" required maxLength={80} placeholder="Username akun Anda" />
            <label htmlFor="loginPassword">Password</label>
            <div className="password-field">
              <input className="input" id="loginPassword" type="password" autoComplete="current-password" required maxLength={256} placeholder="Masukkan password" />
              <button type="button" id="toggleLoginPassword" className="password-toggle-eye" aria-label="Tampilkan password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button>
            </div>
            <p id="loginError" className="error" role="alert" hidden></p>
            <button id="loginSubmit" className="button button--primary" type="submit">Masuk ke studio <span aria-hidden="true">→</span></button>
            <p className="auth-account-help">Belum punya akun? Hubungi administrator workspace.</p>
            <details><summary>Akses pertama di perangkat ini</summary><p>Administrator dapat membuat akun melalui <code>uv run python access.py init --username owner</code>. Password diisi secara interaktif.</p></details>
          </form>
          <p className="auth-footnote">Workspace lokal · Data tetap di perangkat Anda</p>
        </section>
    </>
  );
}

export function Profile() {
  return (
    <section
              id="profilePane"
              className="profile-page"
              aria-labelledby="profileTitle"
              hidden
            >
              <button
                id="profileBack"
                className="button button--tertiary button--sm"
                type="button"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="m14 5-7 7 7 7" />
                </svg>
                Kembali ke studio
              </button>
              <header className="profile-heading">
                <span
                  id="profileAvatar"
                  className="avatar avatar--large"
                  aria-hidden="true"
                ></span>
                <div>
                  <p className="profile-kicker">AKUN WORKSPACE</p>
                  <h1 id="profileTitle" tabIndex={-1}>Profil pengguna</h1><p id="profileDisplayName"></p>
                </div>
              </header>
              <section className="profile-section" aria-labelledby="personalTitle">
                <div className="profile-section-heading"><h2 id="personalTitle">Profil Anda</h2><p>Nama dan foto yang ditampilkan di studio.</p></div>
                <div className="personal-fields">
                  <label htmlFor="profileNameInput">Nama tampilan</label>
                  <div className="profile-name-edit"><input className="input" id="profileNameInput" maxLength={80} required placeholder="Nama lengkap atau panggilan" /><button className="button button--secondary" id="saveNameBtn" type="button">Simpan</button></div>
                  <p id="nameSaveStatus" className="hint" role="status"></p>
                  <label className="photo-upload" htmlFor="avatarFileInput">Foto profil<input id="avatarFileInput" type="file" accept="image/jpeg,image/png,image/webp" /></label>
                  <div className="photo-help"><span className="hint">JPG, PNG, WebP · maksimal 2 MB / 4 MP</span><button id="removeAvatarBtn" type="button" className="button button--tertiary button--sm">Hapus foto</button></div>
                  <p id="avatarStatus" className="hint" role="status"></p>
                </div>
              </section>
              <section className="profile-section" aria-labelledby="identityTitle">
                <div className="profile-section-heading">
                  <h2 id="identityTitle">Identitas</h2>
                  <p>Akses Anda pada workspace ini.</p>
                </div>
                <dl className="identity-list">
                  <div>
                    <dt>Username</dt>
                    <dd id="profileUsername"></dd>
                  </div>
                  <div>
                    <dt>Workspace</dt>
                    <dd id="profileWorkspace"></dd>
                  </div>
                  <div>
                    <dt>Peran</dt>
                    <dd id="profileRole"></dd>
                  </div>
                </dl>
              </section>
              <section className="profile-section" aria-labelledby="passwordTitle">
                <div className="profile-section-heading">
                  <h2 id="passwordTitle">Password &amp; keamanan</h2>
                  <p id="passwordHelp">
                    Setelah diperbarui, sesi lain akan keluar. Rekaman Anda tetap
                    terbuka.
                  </p>
                </div>
                <form id="passwordForm">
                  <label htmlFor="currentPassword">Password saat ini</label
                  ><div className="password-field"><input
                    className="input"
                    id="currentPassword"
                    type="password"
                    autoComplete="current-password"
                    maxLength={256}
                    required
                  /><button type="button" className="password-toggle-eye" data-password-target="currentPassword" aria-label="Tampilkan password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div>
                  <label htmlFor="newPassword">Password baru</label
                  ><div className="password-field"><input
                    className="input"
                    id="newPassword"
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={256}
                    aria-describedby="passwordLength"
                    required
                  /><button type="button" className="password-toggle-eye" data-password-target="newPassword" aria-label="Tampilkan password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div>
                  <p id="passwordLength" className="hint">
                    Minimal 12 karakter. Gunakan password yang unik.
                  </p>
    <div id="passwordMeter" className="password-meter" role="meter" aria-label="Kekuatan password baru" aria-valuemin={0} aria-valuemax={4} aria-valuenow={0} aria-valuetext="Kosong"><div className="password-meter-bars"><span className="password-meter-cell"><span className="password-meter-fill"></span></span><span className="password-meter-cell"><span className="password-meter-fill"></span></span><span className="password-meter-cell"><span className="password-meter-fill"></span></span><span className="password-meter-cell"><span className="password-meter-fill"></span></span></div><div className="password-meter-status"><span className="password-meter-label">Kosong</span><span className="password-meter-common" hidden>Pola mudah ditebak</span></div></div><ul className="password-rules-list"><li id="ruleLen" className="password-rule-item"><span className="password-rule-icon" aria-hidden="true">○</span>12+ karakter</li><li id="ruleCase" className="password-rule-item"><span className="password-rule-icon" aria-hidden="true">○</span>Huruf besar & kecil</li><li id="ruleDigit" className="password-rule-item"><span className="password-rule-icon" aria-hidden="true">○</span>Angka</li><li id="ruleSymbol" className="password-rule-item"><span className="password-rule-icon" aria-hidden="true">○</span>Simbol</li></ul><p id="passwordStrengthAnnouncement" className="sr-only" aria-live="polite"></p>
                  <label htmlFor="confirmPassword">Ulangi password baru</label
                  ><div className="password-field"><input
                    className="input"
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    minLength={12}
                    maxLength={256}
                    required
                  /><button type="button" className="password-toggle-eye" data-password-target="confirmPassword" aria-label="Tampilkan password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg></button></div>
                  <p
                    id="passwordStatus"
                    role="status"
                    aria-live="polite"
                    aria-atomic="true"
                  ></p>
                  <button
                    id="passwordSubmit"
                    className="button button--primary"
                    type="submit"
                  >
                    Simpan password
                  </button>
                </form>
              </section>
              <section className="profile-section" aria-labelledby="appearanceTitle"><div className="profile-section-heading"><h2 id="appearanceTitle">Tampilan</h2><p>Pilih tema atau ikuti perangkat.</p></div><div><label htmlFor="themeSelect">Tema studio</label><select id="themeSelect" className="select__trigger"><option value="system">Ikuti sistem</option><option value="light">Terang</option><option value="dark">Gelap</option></select></div></section>
              <section
                className="profile-section profile-signout"
                aria-labelledby="signoutTitle"
              >
                <div className="profile-section-heading">
                  <h2 id="signoutTitle">Sesi perangkat ini</h2>
                  <p>Keluar dari akun setelah selesai bekerja.</p>
                </div>
                <button
                  id="logoutButton"
                  className="button button--outline"
                  type="button"
                >
                  Keluar dari akun
                </button>
              </section>
            </section>
  );
}
