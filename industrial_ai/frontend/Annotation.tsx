export function Annotation() {
  return (
    <section
                    id="reviewPanel"
                    className="card card--default review"
                    aria-labelledby="reviewTitle"
                    hidden
                  >
                    <div className="section-head">
                      <div>
                        <h2 id="reviewTitle">Anotasi video</h2>
                        <p className="hint">
                          Jeda → koreksi kotak → Putar &amp; ikuti. Klik kanan
                          membatalkan kotak baru.
                        </p>
                      </div>
                      <div className="review-window-actions">
                        <button
                          className="button button--outline button--sm"
                          id="fullscreenReview"
                          type="button"
                          aria-pressed="false"
                          title="Video dan panel koreksi dalam layar penuh"
                        >
                          Layar penuh</button
                        ><button
                          className="button button--tertiary button--sm"
                          id="closeReview"
                          type="button"
                        >
                          Tutup anotasi
                        </button>
                      </div>
                    </div>
                    <div className="review-actions">
                      <label htmlFor="reviewGroup">Yang dikoreksi</label
                      ><select id="reviewGroup" className="select__trigger">
                        <option value="objects">Semua objek pada posisi ini</option>
                        <option value="helmets">
                          Kepala &amp; helm pada posisi ini
                        </option></select
                      ><button
                        className="button button--secondary button--sm"
                        id="suggestBoxes"
                        type="button"
                      >
                        Ambil kotak AI
                      </button>
                    </div>
                    <div className="review-player-controls">
                      <button
                        className="button button--secondary button--sm"
                        id="reviewPlayback"
                        type="button"
                      >
                        Putar &amp; ikuti kotak</button
                      ><label className="sr-only" htmlFor="reviewTimeline"
                        >Posisi video anotasi</label
                      ><input
                        id="reviewTimeline"
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        defaultValue="0"
                      /><output id="reviewPlayTime">00:00</output
                      ><span id="drawingStatus" className="hint" role="status"
                        >Video dijeda; klik dua titik atau tarik kotak.</span
                      >
                    </div>
                    <details className="frame-settings">
                      <summary>Posisi presisi</summary>
                      <fieldset id="reviewControls" className="review-controls">
                        <label
                          >Detik video<input
                            className="input"
                            id="reviewSeconds"
                            type="number"
                            min="0"
                            step="0.1" /></label
                        ><button
                          className="button button--secondary button--sm"
                          id="loadReviewFrame"
                          type="button"
                        >
                          Buka frame</button
                        ><button
                          className="button button--outline button--sm"
                          id="previousReviewFrame"
                          type="button"
                          aria-label="Frame sebelumnya"
                        >
                          ←</button
                        ><button
                          className="button button--outline button--sm"
                          id="nextReviewFrame"
                          type="button"
                          aria-label="Frame berikutnya"
                        >
                          →
                        </button>
                      </fieldset>
                    </details>
                    <div className="review-grid">
                      <div>
                        <div className="review-canvas">
                          <div id="reviewStage" className="annotation-stage" hidden>
                            <video
                              id="reviewVideo"
                              playsInline
                              preload="metadata"
                              aria-label="Video untuk anotasi manual"
                            ></video
                            ><img
                              id="reviewImage"
                              alt="Frame asli untuk koreksi manual"
                              hidden
                            /><svg
                              id="reviewSvg"
                              viewBox="0 0 1 1"
                              preserveAspectRatio="none"
                              role="img"
                              tabIndex={0}
                              aria-label="Area menggambar kotak manual. Klik kiri dua titik atau tarik; klik kanan dan Escape membatalkan."
                            ></svg>
                          </div>
                        </div>
                        <details className="coordinate-details">
                          <summary>Koordinat dengan keyboard</summary>
                          <form id="boxForm">
                            <fieldset id="boxControls" className="review-controls">
                              <legend className="sr-only">
                                Alternatif keyboard: koordinat dalam persen gambar
                              </legend>
                              <label
                                >Kiri (%)<input
                                  className="input"
                                  id="boxX"
                                  type="number"
                                  min="0"
                                  max="99.9"
                                  step="any"
                                  defaultValue="0"
                                  required /></label
                              ><label
                                >Atas (%)<input
                                  className="input"
                                  id="boxY"
                                  type="number"
                                  min="0"
                                  max="99.9"
                                  step="any"
                                  defaultValue="0"
                                  required /></label
                              ><label
                                >Lebar (%)<input
                                  className="input"
                                  id="boxW"
                                  type="number"
                                  min="0.1"
                                  max="100"
                                  step="any"
                                  defaultValue="20"
                                  required /></label
                              ><label
                                >Tinggi (%)<input
                                  className="input"
                                  id="boxH"
                                  type="number"
                                  min="0.1"
                                  max="100"
                                  step="any"
                                  defaultValue="20"
                                  required /></label
                              ><button
                                className="button button--secondary button--sm"
                                id="addManualBox"
                                type="submit"
                              >
                                Tambah kotak
                              </button>
                            </fieldset>
                          </form>
                        </details>
                      </div>
                      <div className="annotation-inspector">
                        <section className="review-queue">
                          <div className="review-actions">
                            <strong>Antrean review</strong
                            ><label className="sr-only" htmlFor="queueFilter"
                              >Filter antrean</label
                            ><select id="queueFilter" className="select__trigger">
                              <option value="pending">Belum disahkan</option>
                              <option value="all">Semua posisi</option></select
                            ><button
                              id="nextPending"
                              className="button button--secondary button--sm"
                              type="button"
                            >
                              Posisi berikutnya
                            </button>
                          </div>
                          <p id="queueStatus" className="hint" role="status"></p>
                          <div id="reviewQueue" className="queue-list"></div>
                        </section>
                        <fieldset id="metadataControls">
                          <div className="label-shortcuts">
                            <button
                              className="button button--outline button--sm"
                              data-label="person"
                              type="button"
                            >
                              Orang</button
                            ><button
                              className="button button--outline button--sm"
                              data-label="Hardhat"
                              type="button"
                            >
                              Helm</button
                            ><button
                              className="button button--outline button--sm"
                              data-label="karung"
                              type="button"
                            >
                              Karung
                            </button>
                          </div>
                          <label htmlFor="reviewLabel">Jenis objek</label
                          ><select className="select__trigger" id="reviewLabel">
                            <option value="person">Orang</option>
                            <option value="car">Mobil</option>
                            <option value="bus">Bus</option>
                            <option value="truck">Truk</option>
                            <option value="motorcycle">Motor</option>
                            <option value="bicycle">Sepeda</option>
                            <option value="Hardhat">Helm</option>
                            <option value="NO-Hardhat">Kepala tanpa helm</option>
                            <option value="karung">Karung</option>
                            <option value="__custom__">
                              ＋ Objek / label lainnya
                            </option>
                          </select>
                          <div id="customLabelField" hidden>
                            <label htmlFor="customLabel">Kelas baru</label
                            ><input
                              className="input"
                              id="customLabel"
                              maxLength={40}
                              pattern="[A-Za-z][A-Za-z0-9_-]{0,39}"
                              placeholder="Contoh: forklift"
                            />
                            <p className="hint">
                              Huruf, angka, _ atau -. Kotak langsung bisa diikuti;
                              mengenali kelas di video lain memerlukan training.
                            </p>
                          </div>
                          <label htmlFor="reviewName">Nama / keterangan</label
                          ><input
                            className="input"
                            id="reviewName"
                            maxLength={60}
                            placeholder="Opsional, mis. bus sekolah"
                          /><label htmlFor="reviewColorMode">Warna kotak</label>
                          <div className="color-field">
                            <select className="select__trigger" id="reviewColorMode">
                              <option value="auto">Otomatis sesuai label</option>
                              <option value="custom">
                                Pilih warna sendiri
                              </option></select
                            ><input
                              id="reviewColor"
                              type="color"
                              aria-label="Warna khusus kotak"
                              defaultValue="#0f766e"
                              disabled
                            />
                          </div>
                        </fieldset>
                        <div id="editActions" hidden>
                          <button
                            className="button button--secondary button--sm"
                            id="applyBoxButton"
                            type="button"
                          >
                            Terapkan perubahan</button
                          ><button
                            className="button button--tertiary button--sm"
                            id="cancelEditButton"
                            type="button"
                          >
                            Batal edit
                          </button>
                        </div>
                        <p className="hint">
                          Pilih jenis objek sebelum menggambar. Periksa kotak
                          tracker sebelum disahkan untuk latihan.
                        </p>
                        <p id="reviewCounts"></p>
                        <ol id="boxList" className="box-list"></ol>
                      </div>
                    </div>
                    <div className="review-actions">
                      <button
                        className="button button--primary button--sm"
                        id="saveReview"
                        type="button"
                      >
                        Sahkan &amp; simpan koreksi</button
                      ><button
                        className="button button--secondary button--sm"
                        id="reloadReview"
                        type="button"
                      >
                        Muat ulang tersimpan</button
                      ><button
                        className="button button--outline button--sm"
                        id="exportCorrectedVideo"
                        type="button"
                      >
                        Ekspor video koreksi</button
                      ><button
                        className="button button--outline button--sm"
                        id="exportDataset"
                        type="button"
                      >
                        Ekspor dataset YOLO
                      </button>
                    </div>
                    <p className="hint" id="reviewStatus" role="status"></p>
                    <p className="error" id="reviewError" role="alert" hidden></p>
                    <details className="frame-settings">
                      <summary>Status belajar otomatis</summary>
                      <p className="hint">
                        Setelah seluruh antrean kelompok selesai disahkan,
                        fine-tuning YOLO berjalan otomatis dan analisis baru dibuka.
                        Minimal dua sumber asli berbeda diperlukan; jika belum
                        cukup, koreksi tersimpan sambil menunggu. Lebih berat
                        daripada mengikuti kotak. Hasil tracker tidak otomatis masuk
                        dataset; hanya posisi yang Anda periksa dan simpan. Gambar
                        latihan tidak memiliki border.
                      </p>
                      <button
                        className="button button--outline button--sm"
                        id="learnDetector"
                        type="button"
                      >
                        Coba belajar lagi
                      </button>
                    </details>
                  </section>
  );
}
