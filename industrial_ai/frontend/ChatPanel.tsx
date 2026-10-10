export function ChatPanel() {
  return (
    <section className="chat" aria-labelledby="chatTitle">
                  <div className="section-head">
                    <h2 id="chatTitle">Tanya rekaman</h2>
                    <button
                      className="button button--tertiary button--sm"
                      id="clearChat"
                      type="button"
                      aria-label="Hapus percakapan"
                    >
                      ↺
                    </button>
                  </div>

                  <div
                    className="messages"
                    id="messages"
                    role="log"
                    aria-live="polite"
                    aria-relevant="additions"
                  ></div>

    <div id="chatThinkingOrb" className="chat-thinking-box" hidden><canvas id="chatOrbCanvas" width="144" height="144" aria-hidden="true"></canvas><span>Meninjau pertanyaan Anda<span className="thinking-subtitle">Menghubungkan jawaban dengan konteks.</span></span></div>
                  <div className="suggestions">
                    <button
                      className="button button--outline button--sm"
                      type="button"
                      data-question="Ringkas hasil video ini"
                    >
                      Ringkasan</button
                    ><button
                      className="button button--outline button--sm"
                      type="button"
                      data-question="Berapa orang pada detik 3?"
                    >
                      Orang di detik 3</button
                    ><button
                      className="button button--outline button--sm"
                      type="button"
                      data-question="Siapa kandidat tanpa helm?"
                    >
                      Tanpa helm
                    </button>
                  </div>

                  <form className="chat-form" id="chatForm">
                    <label htmlFor="chatInput" className="sr-only">Pesan untuk AI</label
                    ><textarea
                      className="textarea"
                      id="chatInput"
                      rows={2}
                      maxLength={600}
                      placeholder="Tanya tentang rekaman…"
                      required
                    ></textarea
                    ><button
                      className="button button--primary button--sm"
                      id="sendChat"
                      type="submit"
                      aria-label="Kirim pesan"
                    >
                      ↑
                    </button>
                  </form>

                  <p className="hint" id="chatStatus" role="status"></p>
                  <p className="error" id="chatError" role="alert" hidden></p>

                  <details className="chat-information">
                    <summary>Sumber jawaban</summary>
                    <p className="hint" id="chatContext">
                      Chat umum tersedia. Pilih hasil video untuk bertanya tentang
                      analisis.
                    </p>
                    <p className="hint">
                      Angka berasal dari hasil tersimpan. Percakapan umum memakai
                      model lokal.
                    </p>
                  </details>
                </section>
  );
}
