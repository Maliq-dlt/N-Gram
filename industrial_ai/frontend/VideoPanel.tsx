export function VideoPanel() {
  return (
    <>
    <div id="analysisPane">
                    <section
                      id="compare"
                      className="compare"
                      data-layout="split"
                      aria-labelledby="comparisonTitle"
                    >
                      <div className="section-head comparison-head">
                        <div>
                          <h2 id="comparisonTitle">Pratinjau rekaman</h2>
                          <p id="currentFile" className="sr-only">
                            Pilih rekaman untuk mulai.
                          </p>
                        </div>

                        <label className="sr-only" htmlFor="comparisonLayout"
                          >Tata letak video</label
                        >
                        <select
                          id="comparisonLayout"
                          className="select__trigger"
                          aria-label="Tata letak video"
                        >
                          <option value="split">Berdampingan</option>
                          <option value="tracking">Fokus hasil</option>
                          <option value="original">Fokus asli</option>
                        </select>
                        <fieldset className="result-switch">
                          <legend className="sr-only">Hasil yang ditampilkan</legend>
                          <label
                            ><input
                              id="resultAi"
                              type="radio"
                              name="resultView"
                              value="ai"
                              defaultChecked
                            /><span>Model AI</span></label
                          ><label
                            ><input
                              id="resultCorrections"
                              type="radio"
                              name="resultView"
                              value="corrections"
                            /><span>Koreksi saya</span></label
                          >
                        </fieldset>
                        <label className="sr-only" htmlFor="resultMode"
                          >Hasil yang ditampilkan</label
                        ><select id="resultMode" hidden>
                          <option value="ai">Analisis model AI</option>
                          <option id="correctedOption" value="corrections" disabled>
                            Koreksi pengguna
                          </option>
                        </select>
                      </div>
                      <div id="emptyVideos" className="empty">
                        <svg viewBox="0 0 64 64" aria-hidden="true">
                          <rect x="9" y="14" width="46" height="36" rx="8" />
                          <path d="m27 25 13 7-13 7z" />
                        </svg>
                        <h3>Mulai dari satu video</h3>
                        <p>
                          Unggah rekaman untuk membandingkan video asli dan hasil
                          tracking AI.
                        </p>
                        <button
                          className="button button--secondary"
                          id="emptyUploadButton"
                          type="button"
                        >
                          Pilih video
                        </button>
                      </div>
                      <div id="videoContent" hidden>
                        <div className="video-grid">
                          <div className="video-pane video-pane--original">
                            <div className="video-label">
                              <span
                                ><i className="label-dot original-dot"></i>Video
                                asli</span
                              >
                            </div>
                            <video
                              id="originalVideo"
                              controls
                              playsInline
                              preload="metadata"
                              aria-label="Video asli"
                            ></video>
                          </div>
                          <div className="video-pane video-pane--tracking">
                            <div className="video-label">
                              <span
                                ><i className="label-dot tracked-dot"></i
                                ><span id="trackingPaneTitle"
                                  >Tracking AI</span
                                ></span
                              >
                            </div>
                            <video
                              id="trackedVideo"
                              controls
                              playsInline
                              preload="metadata"
                              muted
                              aria-label="Video hasil tracking AI"
                            ></video>
                          </div>
                        </div>
                        <div className="toolbar">
                          <div>
                            <button
                              className="button button--secondary button--sm"
                              id="playBoth"
                              type="button"
                            >
                              Putar bersama</button
                            ><button
                              className="button button--tertiary button--sm"
                              id="restartVideos"
                              type="button"
                            >
                              Dari awal</button
                            ><span className="time" id="videoTime">00:00 / 00:00</span>
                          </div>
                          <button
                            className="button button--outline button--sm"
                            id="openReview"
                            type="button"
                          >
                            Koreksi kotak
                          </button>
                        </div>
                        <div className="moment-row">
                          <span id="visibleNow"></span
                          ><span id="comparisonBadge" className="badge" role="status"
                            >Menunggu video</span
                          >
                        </div>
                      </div>
                    </section>
                    <div
                      id="stats"
                      className="stats"
                      aria-label="Ringkasan hasil"
                      hidden
                    >
                      <div className="stat">
                        <span>Orang bersamaan</span
                        ><strong id="peakPeople"></strong>
                      </div>

                      <div className="stat">
                        <span>Objek lain bersamaan</span
                        ><strong id="peakCars"></strong>
                      </div>

                      <div className="stat">
                        <span>Lintasan</span><strong id="crossingCount"></strong>
                      </div>

                      <div className="stat">
                        <span>Tanpa helm (kandidat)</span
                        ><strong id="candidateCount"></strong>
                      </div>
                    </div>
                    <details className="analysis-details">
                      <summary>Detail hasil &amp; koreksi</summary>
                      <p
                        id="correctionCounts"
                        className="hint"
                        role="status"
                        aria-live="polite"
                      ></p>
                      <button
                        id="prepareCorrections"
                        className="button button--outline button--sm"
                        type="button"
                      >
                        Perbarui tampilan koreksi
                      </button>
                      <div className="legend">
                        <span><i className="dot green"></i>Helm</span
                        ><span><i className="dot red"></i>Tanpa helm</span
                        ><span><i className="dot yellow"></i>Belum jelas</span
                        ><span><i className="dot blue"></i>Kendaraan</span>
                      </div>

                      <p className="hint">
                        Maksimum adalah jumlah yang terlihat bersamaan. Lintasan
                        dihitung saat pusat kotak melewati garis putus-putus. ID
                        track sementara, bukan identitas orang.
                      </p>

                      <p className="hint">
                        Salinan analisis: 10 FPS, maksimal 720p. Hasil koreksi
                        terpisah dari hasil model AI.
                      </p>
                    </details>
                  </div>
    <div id="evidencePane" hidden>
                    <section
                      className="card card--default results"
                      aria-labelledby="resultsTitle"
                    >
                      <div className="section-head">
                        <h2 id="resultsTitle">Bukti &amp; hasil</h2>
                        <span className="chip chip--sm">Tersimpan lokal</span>
                      </div>
                      <p className="hint" id="resultsEmpty">
                        Pilih rekaman yang selesai dianalisis.
                      </p>
                      <div id="resultsContent" hidden>
                        <dl id="resultDetails"></dl>
                        <div className="filter">
                          <h3>Foto bukti</h3>
                          <label className="sr-only" htmlFor="evidenceFilter"
                            >Jenis bukti</label
                          ><select className="select__trigger" id="evidenceFilter">
                            <option value="all">Semua objek</option>
                            <option value="person">Orang</option>
                            <option value="car">Mobil</option>
                            <option value="bus">Bus</option>
                            <option value="truck">Truk</option>
                            <option value="motorcycle">Motor</option>
                            <option value="bicycle">Sepeda</option>
                            <option value="helmet">Kandidat tanpa helm</option>
                          </select>
                        </div>
                        <div className="evidence-list" id="evidenceList"></div>
                        <div className="downloads">
                          <a
                            className="button button--outline button--sm"
                            id="downloadTracked"
                            >Unduh video</a
                          ><a
                            className="button button--outline button--sm"
                            id="downloadSummary"
                            >JSON analisis</a
                          ><a
                            className="button button--tertiary button--sm"
                            id="downloadOriginal"
                            >Upload asli</a
                          >
                        </div>
                        <p className="hint">
                          Foto menandai target dan ID. Jumlah track bukan jumlah
                          individu unik.
                        </p>
                      </div>
                    </section>
                  </div>
    </>
  );
}
