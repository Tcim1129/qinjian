(function () {
    const DB_NAME = 'qj-local-first';
    const DB_VERSION = 1;
    const DRAFT_STORE = 'checkin_drafts';
    const WORKER_INIT_TIMEOUT_MS = 2500;

    const DEFAULT_PREFS = {
        aiAssistEnabled: true,
        privacyMode: 'cloud',
        preferredEntry: 'daily',
    };

    function normalizePrefs(raw = {}) {
        return {
            aiAssistEnabled: raw?.ai_assist_enabled !== false,
            privacyMode: raw?.privacy_mode === 'local_first' ? 'local_first' : 'cloud',
            preferredEntry: ['daily', 'emergency', 'reflection'].includes(raw?.preferred_entry)
                ? raw.preferred_entry
                : 'daily',
        };
    }

    function supportsIndexedDb() {
        return typeof window.indexedDB !== 'undefined';
    }

    function openDraftDb() {
        if (!supportsIndexedDb()) {
            return Promise.reject(new Error('indexeddb_unavailable'));
        }

        return new Promise((resolve, reject) => {
            const request = window.indexedDB.open(DB_NAME, DB_VERSION);
            request.onupgradeneeded = () => {
                const db = request.result;
                if (!db.objectStoreNames.contains(DRAFT_STORE)) {
                    const store = db.createObjectStore(DRAFT_STORE, { keyPath: 'id' });
                    store.createIndex('status', 'status', { unique: false });
                    store.createIndex('updatedAt', 'updatedAt', { unique: false });
                }
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error || new Error('indexeddb_open_failed'));
        });
    }

    async function withStore(mode, callback) {
        const db = await openDraftDb();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(DRAFT_STORE, mode);
            const store = tx.objectStore(DRAFT_STORE);
            let result;
            tx.oncomplete = () => {
                db.close();
                resolve(result);
            };
            tx.onerror = () => {
                db.close();
                reject(tx.error || new Error('indexeddb_transaction_failed'));
            };
            tx.onabort = () => {
                db.close();
                reject(tx.error || new Error('indexeddb_transaction_aborted'));
            };
            result = callback(store, tx);
        });
    }

    function readFileAsDataUrl(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result || ''));
            reader.onerror = () => reject(reader.error || new Error('file_read_failed'));
            reader.readAsDataURL(file);
        });
    }

    function loadImageElement(src) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error('image_decode_failed'));
            image.src = src;
        });
    }

    async function compressImageFile(file) {
        const dataUrl = await readFileAsDataUrl(file);
        const image = await loadImageElement(dataUrl);
        const maxEdge = 1600;
        const scale = Math.min(1, maxEdge / Math.max(image.width || 1, image.height || 1));
        const width = Math.max(1, Math.round(image.width * scale));
        const height = Math.max(1, Math.round(image.height * scale));
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(image, 0, 0, width, height);
        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.84));
        const outputBlob = blob || file;
        const outputFile = new File([outputBlob], file.name.replace(/\.[^.]+$/, '.jpg'), {
            type: outputBlob.type || 'image/jpeg',
            lastModified: Date.now(),
        });
        return {
            file: outputFile,
            previewUrl: URL.createObjectURL(outputFile),
            deviceMeta: {
                original_type: file.type,
                output_type: outputFile.type,
                original_size: file.size,
                compressed_size: outputFile.size,
                width,
                height,
                exif_removed: true,
            },
        };
    }

    async function getAudioDuration(file) {
        const objectUrl = URL.createObjectURL(file);
        try {
            const audio = document.createElement('audio');
            audio.preload = 'metadata';
            const duration = await new Promise((resolve, reject) => {
                audio.onloadedmetadata = () => resolve(Number(audio.duration) || null);
                audio.onerror = () => reject(new Error('audio_metadata_failed'));
                audio.src = objectUrl;
            });
            return duration;
        } finally {
            URL.revokeObjectURL(objectUrl);
        }
    }

    async function analyzeAudioSignal(file) {
        if (typeof window.AudioContext === 'undefined' && typeof window.webkitAudioContext === 'undefined') {
            return { silence_ratio: null, peak_level: null };
        }

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const context = new AudioCtx();
        try {
            const buffer = await file.arrayBuffer();
            const audioBuffer = await context.decodeAudioData(buffer.slice(0));
            const channel = audioBuffer.getChannelData(0);
            if (!channel || !channel.length) {
                return { silence_ratio: null, peak_level: null };
            }

            let silentSamples = 0;
            let peak = 0;
            for (let index = 0; index < channel.length; index += 1) {
                const amplitude = Math.abs(channel[index]);
                if (amplitude < 0.015) {
                    silentSamples += 1;
                }
                if (amplitude > peak) {
                    peak = amplitude;
                }
            }

            return {
                silence_ratio: Number((silentSamples / channel.length).toFixed(3)),
                peak_level: Number(peak.toFixed(3)),
            };
        } catch (error) {
            return { silence_ratio: null, peak_level: null };
        } finally {
            if (typeof context.close === 'function') {
                context.close().catch(() => null);
            }
        }
    }

    async function inspectVoiceFile(file) {
        const [durationSeconds, signal] = await Promise.all([
            getAudioDuration(file).catch(() => null),
            analyzeAudioSignal(file),
        ]);

        return {
            file,
            previewUrl: null,
            deviceMeta: {
                mime_type: file.type,
                size_bytes: file.size,
                duration_seconds: durationSeconds,
                silence_ratio: signal.silence_ratio,
                peak_level: signal.peak_level,
            },
        };
    }

    function determineUploadPolicy(precheck, prefs) {
        if (prefs.privacyMode !== 'local_first') {
            return 'full';
        }
        if (!window.navigator.onLine) {
            return 'local_only';
        }
        if ((precheck?.risk_level || 'none') === 'high') {
            return 'local_only';
        }
        if ((precheck?.pii_summary?.total_hits || 0) > 0) {
            return 'redacted_only';
        }
        return 'full';
    }

    class ClientAIService {
        constructor() {
            this.available = false;
            this.worker = null;
            this._seq = 0;
            this._pending = new Map();
        }

        _disableWorker(message = 'worker_unavailable') {
            const error = new Error(message);
            for (const [, pending] of this._pending.entries()) {
                pending.reject(error);
            }
            this._pending.clear();
            if (this.worker) {
                try {
                    this.worker.terminate();
                } catch (terminateError) {
                    // Ignore terminate failures while falling back to cloud mode.
                }
            }
            this.worker = null;
            this.available = false;
        }

        async init() {
            if (this.worker || typeof window.Worker === 'undefined') {
                this.available = Boolean(this.worker);
                return this.available;
            }

            try {
                const workerUrl = new URL('js-compat/client-ai-worker.js?v=20260325c', window.location.href);
                this.worker = new window.Worker(workerUrl, { name: 'qj-client-ai' });
                this.worker.onmessage = (event) => {
                    const { id, ok, result, error } = event.data || {};
                    const pending = this._pending.get(id);
                    if (!pending) return;
                    this._pending.delete(id);
                    if (ok) {
                        pending.resolve(result);
                    } else {
                        pending.reject(new Error(error || 'worker_failed'));
                    }
                };
                this.worker.onerror = () => {
                    this._disableWorker('worker_runtime_failed');
                };
                this.worker.onmessageerror = () => {
                    this._disableWorker('worker_message_failed');
                };
                this.available = true;
                await Promise.race([
                    this.call('ping', {}),
                    new Promise((_, reject) => {
                        window.setTimeout(() => {
                            reject(new Error('worker_init_timeout'));
                        }, WORKER_INIT_TIMEOUT_MS);
                    }),
                ]);
                return true;
            } catch (error) {
                this._disableWorker(error?.message || 'worker_init_failed');
                return false;
            }
        }

        call(type, payload) {
            if (!this.worker) {
                return Promise.reject(new Error('worker_unavailable'));
            }
            this._seq += 1;
            const id = `msg-${this._seq}`;
            return new Promise((resolve, reject) => {
                this._pending.set(id, { resolve, reject });
                this.worker.postMessage({ id, type, payload });
            });
        }

        async precheckText(text, options = {}) {
            if (!this.worker && !(await this.init())) {
                return {
                    source_type: options.source_type || 'text',
                    intent: 'daily',
                    risk_level: 'none',
                    risk_hits: [],
                    pii_summary: { total_hits: 0, categories: {} },
                    privacy_mode: options.privacy_mode === 'local_first' ? 'local_first' : 'cloud',
                    upload_policy: 'full',
                    redacted_text: text,
                    client_tags: ['cloud_fallback'],
                    device_meta: options.device_meta || null,
                    ai_assist_enabled: options.ai_assist_enabled !== false,
                    degraded: true,
                };
            }
            return this.call('precheck-text', {
                text,
                source_type: options.source_type || 'text',
                privacy_mode: options.privacy_mode,
                ai_assist_enabled: options.ai_assist_enabled,
                device_meta: options.device_meta || null,
            });
        }

        async describeAttachmentMeta(sourceType, deviceMeta, options = {}) {
            if (!this.worker && !(await this.init())) {
                return {
                    source_type: sourceType,
                    intent: 'daily',
                    risk_level: 'none',
                    risk_hits: [],
                    pii_summary: { total_hits: 0, categories: {} },
                    privacy_mode: options.privacy_mode === 'local_first' ? 'local_first' : 'cloud',
                    upload_policy: 'full',
                    redacted_text: null,
                    client_tags: [],
                    device_meta: deviceMeta,
                    ai_assist_enabled: options.ai_assist_enabled !== false,
                    degraded: true,
                };
            }
            return this.call('describe-attachment-meta', {
                source_type: sourceType,
                device_meta: deviceMeta,
                privacy_mode: options.privacy_mode,
                ai_assist_enabled: options.ai_assist_enabled,
            });
        }

        async prepareImage(file) {
            return compressImageFile(file);
        }

        async inspectVoice(file) {
            return inspectVoiceFile(file);
        }

        async saveDraft(record) {
            if (!supportsIndexedDb()) {
                throw new Error('indexeddb_unavailable');
            }

            const draft = {
                ...record,
                id: record.id || (window.crypto?.randomUUID?.() || `draft-${Date.now()}`),
                updatedAt: new Date().toISOString(),
            };

            await withStore('readwrite', (store) => {
                store.put(draft);
            });
            return draft;
        }

        async updateDraft(record) {
            return this.saveDraft(record);
        }

        async deleteDraft(id) {
            if (!supportsIndexedDb()) return;
            await withStore('readwrite', (store) => {
                store.delete(id);
            });
        }

        async listDrafts() {
            if (!supportsIndexedDb()) return [];
            const db = await openDraftDb();
            return new Promise((resolve, reject) => {
                const tx = db.transaction(DRAFT_STORE, 'readonly');
                const store = tx.objectStore(DRAFT_STORE);
                const request = store.getAll();
                request.onsuccess = () => resolve(request.result || []);
                request.onerror = () => reject(request.error || new Error('indexeddb_read_failed'));
                tx.oncomplete = () => db.close();
                tx.onerror = () => {
                    db.close();
                    reject(tx.error || new Error('indexeddb_transaction_failed'));
                };
            });
        }

        async countPendingDrafts() {
            const drafts = await this.listDrafts();
            return drafts.filter((item) => item.status === 'pending').length;
        }
    }

    window.QJClientAI = {
        DEFAULT_PREFS,
        normalizePrefs,
        determineUploadPolicy,
        createService() {
            return new ClientAIService();
        },
    };
})();
