/**
 * API Service Layer for AlterEcho
 * Combines local IndexedDB storage with backend API calls for AI processing
 */

import * as Storage from './storage';

const API_BASE = '/api';

// ============================================================================
// LOCAL STORAGE OPERATIONS (IndexedDB)
// ============================================================================

// --- Sessions ---
export async function getSessions() {
    const sessions = await Storage.getSessions();
    return { sessions };
}

export async function createSession(name) {
    return await Storage.createSession(name);
}

export async function deleteSession(sessionId) {
    return await Storage.deleteSession(sessionId);
}

export async function updateSession(sessionId, updates) {
    return await Storage.updateSession(sessionId, updates);
}

// --- Messages ---
export async function getMessages(sessionId) {
    const messages = await Storage.getMessages(sessionId);

    // Convert image IDs to blob URLs for display
    const messagesWithBlobUrls = await Promise.all(messages.map(async (msg) => {
        if (!msg.images || msg.images.length === 0) return msg;

        // Check if images are already blob URLs (temporary objects)
        if (msg.images[0] && msg.images[0].startsWith('blob:')) return msg;

        const blobUrls = [];
        for (const imageId of msg.images) {
            const imageRecord = await Storage.getImage(sessionId, imageId);
            if (imageRecord) {
                const blob = new Blob([imageRecord.data], { type: imageRecord.mime_type || 'image/png' });
                blobUrls.push(URL.createObjectURL(blob));
            }
        }
        return { ...msg, images: blobUrls };
    }));

    return { messages: messagesWithBlobUrls };
}

export async function clearChatHistory(sessionId) {
    await Storage.clearMessages(sessionId);
    return { status: 'ok', message: 'History cleared' };
}

// --- Files (Per Chat) ---
export async function uploadFile(sessionId, files, fileType) {
    const uploaded = [];
    const rejected = [];

    const fileList = files instanceof FileList ? Array.from(files) :
        Array.isArray(files) ? files : [files];

    for (const file of fileList) {
        if (!file.name) continue;

        const ext = file.name.toLowerCase().split('.').pop();

        // Validation for text files
        if (fileType === 'text' && !['txt', 'json', 'zip', 'html'].includes(ext)) {
            rejected.push({ name: file.name, reason: 'Invalid extension' });
            continue;
        }

        // Handle ZIP files - need backend processing
        if (fileType === 'text' && ext === 'zip') {
            try {
                const result = await processZipFile(sessionId, file);
                return result; // Return immediately for ZIP selection flow
            } catch (e) {
                rejected.push({ name: file.name, reason: `ZIP error: ${e.message}` });
                continue;
            }
        }

        // Detect file type and participants for text files
        let metadata = {};
        if (fileType === 'text') {
            try {
                metadata = await detectFileMetadata(file);
            } catch (e) {
                console.warn('Could not detect file metadata:', e);
            }
        }

        // Store in IndexedDB
        const upload = await Storage.addUpload(sessionId, fileType, file, metadata);

        uploaded.push({
            id: upload.file_id,
            original_name: upload.original_name,
            saved_as: upload.saved_as,
            file_type: fileType,
            detected_type: upload.detected_type,
            participants: upload.participants
        });
    }

    return {
        success: true,
        uploaded,
        rejected,
        uploaded_count: uploaded.length
    };
}

export async function listFiles(sessionId, fileType) {
    const uploads = await Storage.getUploads(sessionId, fileType);

    const files = uploads.map(u => ({
        id: u.file_id,
        original_name: u.original_name,
        saved_as: u.saved_as,
        file_type: u.type,
        detected_type: u.detected_type,
        participants: u.participants,
        subject: u.subject,
        size: u.size
    }));

    return { files, count: files.length };
}

export async function setSubject(sessionId, fileId, subject) {
    const updated = await Storage.updateUpload(sessionId, fileId, { subject });
    if (!updated) throw new Error('File not found');
    return { success: true, subject };
}

export async function deleteUploadedFile(sessionId, fileType, fileId) {
    return await Storage.deleteUpload(sessionId, fileType, fileId);
}

// --- Settings ---
export async function getSettings() {
    return await Storage.getSettings();
}

export async function updateSettings(settings) {
    return await Storage.saveSettings(settings);
}

// --- API Keys ---
export async function getGeminiKeyStatus() {
    const configured = await Storage.hasGeminiKey();
    return { configured };
}

export async function saveGeminiKey(apiKey) {
    await Storage.saveGeminiKey(apiKey);
    return { success: true };
}

export async function deleteGeminiKey() {
    await Storage.deleteSecret('gemini_api_key');
    return { success: true };
}

export async function getWaveSpeedKeyStatus() {
    const configured = await Storage.hasWaveSpeedKey();
    return { configured };
}

export async function saveWaveSpeedKey(apiKey) {
    await Storage.saveWaveSpeedKey(apiKey);
    return { success: true };
}

export async function deleteWaveSpeedKey() {
    await Storage.deleteSecret('wavespeed_api_key');
    return { success: true };
}

// ============================================================================
// BACKEND API CALLS (AI Processing)
// ============================================================================

// Track which sessions have been cached on server (to avoid sending large embeddings every time)
const cachedSessions = new Set();

// --- Chat (requires Gemini API) ---
export async function sendMessage(content, sessionId, file = null) {
    // Get preprocessed data to send with request
    const preprocessed = await Storage.getPreprocessed(sessionId);
    const session = await Storage.getSession(sessionId);
    const history = await Storage.getMessages(sessionId);
    const geminiKey = await Storage.getGeminiKey();
    const settings = await Storage.getSettings();

    // Only send full embeddings if session not yet cached on server
    const needsFullData = !cachedSessions.has(sessionId);

    let body;
    let headers = {};

    if (file) {
        const formData = new FormData();
        formData.append('content', content);
        formData.append('session_id', sessionId);
        formData.append('image', file);
        // Always send style_summary (small), only send embeddings if needed
        formData.append('style_summary', preprocessed?.style_summary || '');
        if (needsFullData) {
            formData.append('embeddings', JSON.stringify(preprocessed?.embeddings || {}));
        } else {
            formData.append('embeddings', '{}');
        }
        formData.append('history', JSON.stringify(history.slice(-20)));
        formData.append('gemini_key', geminiKey || '');
        formData.append('settings', JSON.stringify(settings));
        body = formData;
    } else {
        headers['Content-Type'] = 'application/json';
        const payload = {
            content,
            session_id: sessionId,
            style_summary: preprocessed?.style_summary || '',
            history: history.slice(-20),
            gemini_key: geminiKey || '',
            settings
        };
        // Only include embeddings if not cached
        if (needsFullData) {
            payload.embeddings = preprocessed?.embeddings || {};
        }
        body = JSON.stringify(payload);
    }

    const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers,
        body,
    });
    if (!response.ok) throw new Error('Failed to send message');

    // Mark session as cached after successful request
    cachedSessions.add(sessionId);

    const result = await response.json();

    // Track original image IDs before converting to blob URLs
    const originalUserImages = result.user_message?.images ? [...result.user_message.images] : [];
    const originalAiMessagesImages = result.ai_messages?.map(m => m.images ? [...m.images] : []) || [];
    const originalAiMessageImages = result.ai_message?.images ? [...result.ai_message.images] : [];

    // Store user-uploaded image with the ID from backend
    if (file && result.user_message?.images?.length > 0) {
        const userImageId = result.user_message.images[0];
        await Storage.saveImage(sessionId, userImageId, file, { source: 'user' });
    }

    // Store AI-generated images
    if (result.generated_images && result.generated_images.length > 0) {
        for (const imgData of result.generated_images) {
            await Storage.saveImage(sessionId, imgData.id, imgData.data, {
                mime_type: imgData.mime_type,
                source: 'ai'
            });
        }
    }

    // Convert image IDs to blob URLs for display
    const convertImageIds = async (message) => {
        if (!message.images || message.images.length === 0) return message;

        const blobUrls = [];
        for (const imageId of message.images) {
            const imageRecord = await Storage.getImage(sessionId, imageId);
            if (imageRecord) {
                const blob = new Blob([imageRecord.data], { type: imageRecord.mime_type || 'image/png' });
                blobUrls.push(URL.createObjectURL(blob));
            }
        }
        return { ...message, images: blobUrls };
    };

    // Convert image IDs to blob URLs in messages for UI display
    if (result.user_message) {
        result.user_message = await convertImageIds(result.user_message);
    }
    if (result.ai_messages) {
        result.ai_messages = await Promise.all(result.ai_messages.map(convertImageIds));
    }
    if (result.ai_message) {
        result.ai_message = await convertImageIds(result.ai_message);
    }

    // Store messages locally with original image IDs (not blob URLs)
    if (result.user_message) {
        const storageMsg = { ...result.user_message, images: originalUserImages };
        await Storage.addMessage(sessionId, storageMsg);
    }
    if (result.ai_messages) {
        for (let i = 0; i < result.ai_messages.length; i++) {
            const storageMsg = { ...result.ai_messages[i], images: originalAiMessagesImages[i] || [] };
            await Storage.addMessage(sessionId, storageMsg);
        }
    } else if (result.ai_message) {
        const storageMsg = { ...result.ai_message, images: originalAiMessageImages };
        await Storage.addMessage(sessionId, storageMsg);
    }

    // Update session preview
    const previewText = result.ai_message?.content || 'No preview';
    await Storage.updateSession(sessionId, {
        preview: previewText.slice(0, 50) + (previewText.length > 50 ? '...' : '')
    });

    return result;
}

// --- ZIP Handling (requires backend processing) ---
async function processZipFile(sessionId, file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const geminiKey = await Storage.getGeminiKey();
    formData.append('gemini_key', geminiKey || '');

    const response = await fetch(`${API_BASE}/chats/${sessionId}/files/text`, {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) throw new Error('Failed to process ZIP');
    return response.json();
}

export async function selectZipConversations(zipId, conversations) {
    const response = await fetch(`${API_BASE}/chats/zip/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zip_id: zipId, conversations }),
    });
    if (!response.ok) throw new Error('Failed to select ZIP conversations');

    const result = await response.json();

    // Store the selected conversation files locally
    // The backend returns merged JSON data for each conversation
    if (result.uploaded) {
        // Files are already stored in backend response, save metadata locally
        const sessionId = result.session_id;
        if (sessionId) {
            for (const upload of result.uploaded) {
                // Just track these in our local storage
                await Storage.updateUpload(sessionId, upload.id, {
                    detected_type: upload.detected_type,
                    original_name: upload.original_name
                });
            }
        }
    }

    return result;
}

// --- AI Refresh (requires Gemini API) ---
export async function checkRefreshReady(sessionId) {
    if (!sessionId) return { ready: false, reason: 'No session selected' };

    // Check locally if files have subjects set
    const uploads = await Storage.getUploads(sessionId, 'text');
    if (uploads.length === 0) {
        return { ready: false, reason: 'No files uploaded' };
    }

    const withoutSubject = uploads.filter(u => !u.subject);
    if (withoutSubject.length > 0) {
        return { ready: false, reason: 'Missing subjects' };
    }

    return { ready: true };
}

export async function refreshAIMemory({ sessionId, additionalContext, onProgress, onComplete, onError }) {
    try {
        // Get all uploaded text files
        const uploads = await Storage.getUploads(sessionId, 'text');
        const voiceUploads = await Storage.getUploads(sessionId, 'voice');
        const geminiKey = await Storage.getGeminiKey();
        const waveSpeedKey = await Storage.getWaveSpeedKey();
        const settings = await Storage.getSettings();

        // Prepare files to send to backend
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('additional_context', additionalContext || '');
        formData.append('gemini_key', geminiKey || '');
        formData.append('wavespeed_key', waveSpeedKey || '');
        formData.append('settings', JSON.stringify(settings));

        // Add text files with their subjects
        const filesMetadata = [];
        for (const upload of uploads) {
            const blob = new Blob([upload.data], { type: upload.mime_type || 'application/octet-stream' });
            const file = new File([blob], upload.original_name);
            formData.append('text_files', file);
            filesMetadata.push({
                file_id: upload.file_id,
                original_name: upload.original_name,
                subject: upload.subject,
                detected_type: upload.detected_type
            });
        }
        formData.append('files_metadata', JSON.stringify(filesMetadata));

        // Add voice file (most recent)
        if (voiceUploads.length > 0) {
            const voiceUpload = voiceUploads[voiceUploads.length - 1];
            const voiceBlob = new Blob([voiceUpload.data], { type: voiceUpload.mime_type });
            const voiceFile = new File([voiceBlob], voiceUpload.original_name);
            formData.append('voice_file', voiceFile);
        }

        const response = await fetch(`${API_BASE}/process`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to start processing');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6).trim());

                        if (data.step === 'complete') {
                            // Store preprocessed data locally
                            if (data.preprocessed) {
                                await Storage.savePreprocessed(sessionId, data.preprocessed);
                            }

                            // Update session with subject and voice info
                            const updates = {};
                            if (data.subject) updates.subject = data.subject;
                            if (data.voice_id) {
                                updates.wavespeed_voice_id = data.voice_id;
                                updates.voice_created_at = new Date().toISOString();
                            }
                            if (Object.keys(updates).length > 0) {
                                await Storage.updateSession(sessionId, updates);
                            }

                            if (onComplete) onComplete(data);
                        } else if (data.step === 'error' && onError) {
                            onError(data.message);
                        } else if (onProgress) {
                            onProgress(data);
                        }
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', line, e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Refresh AI memory error:', error);
        if (onError) onError(error.message);
    }
}

// --- Voice Call Streaming ---
export async function streamVoiceCall(content, sessionId, { onText, onAudio, onStatus, onDone, onError }) {
    try {
        const preprocessed = await Storage.getPreprocessed(sessionId);
        const session = await Storage.getSession(sessionId);
        const geminiKey = await Storage.getGeminiKey();
        const waveSpeedKey = await Storage.getWaveSpeedKey();
        const settings = await Storage.getSettings();

        // Only send full embeddings if session not yet cached on server
        const needsFullData = !cachedSessions.has(sessionId);

        const payload = {
            content,
            session_id: sessionId,
            style_summary: preprocessed?.style_summary || '',
            voice_id: session?.wavespeed_voice_id || 'Deep_Voice_Man',
            gemini_key: geminiKey || '',
            wavespeed_key: waveSpeedKey || '',
            settings
        };

        // Only include embeddings if not cached
        if (needsFullData) {
            payload.embeddings = preprocessed?.embeddings || {};
        }

        const response = await fetch(`${API_BASE}/call/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error('Failed to start voice call stream');
        }

        // Mark session as cached after successful request
        cachedSessions.add(sessionId);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const dataStr = line.slice(6).trim();
                        const data = JSON.parse(dataStr);

                        if (data.type === 'text' && onText) {
                            onText(data.content);
                        } else if (data.type === 'audio' && onAudio) {
                            onAudio(data.content, data.index);
                        } else if (data.type === 'status' && onStatus) {
                            onStatus(data.content);
                        } else if (data.type === 'done' && onDone) {
                            onDone(data.full_text);
                        } else if (data.type === 'error' && onError) {
                            onError(data.content);
                        }
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', line, e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Voice call stream error:', error);
        if (onError) onError(error.message);
    }
}

// --- Other Backend Calls ---
export async function listVoices() {
    const waveSpeedKey = await Storage.getWaveSpeedKey();
    const response = await fetch(`${API_BASE}/voices`, {
        headers: { 'X-WaveSpeed-Key': waveSpeedKey || '' }
    });
    if (!response.ok) throw new Error('Failed to list voices');
    return response.json();
}

export async function warmupModels() {
    try {
        const response = await fetch(`${API_BASE}/warmup`, { method: 'POST' });
        if (!response.ok) throw new Error('Failed to warmup');
        return response.json();
    } catch (e) {
        console.warn('Warmup failed:', e);
        return { status: 'error' };
    }
}

export async function cloneVoice(sessionId, audioFile) {
    const waveSpeedKey = await Storage.getWaveSpeedKey();

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('wavespeed_key', waveSpeedKey || '');

    const response = await fetch(`${API_BASE}/voice/clone/${sessionId}`, {
        method: 'POST',
        body: formData,
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Clone failed' }));
        throw new Error(error.detail || 'Failed to clone voice');
    }

    const result = await response.json();

    // Update session with voice ID
    if (result.voice_id) {
        await Storage.updateSession(sessionId, {
            wavespeed_voice_id: result.voice_id,
            voice_created_at: new Date().toISOString()
        });
    }

    return result;
}

export async function getVoiceStatus(sessionId) {
    const session = await Storage.getSession(sessionId);
    if (!session) {
        return { has_voice: false, voice_status: 'none', message: 'Session not found' };
    }

    const voiceId = session.wavespeed_voice_id;

    if (!voiceId) {
        return { has_voice: false, voice_status: 'none', message: 'No voice configured' };
    }

    const lastUsed = session.voice_last_used_at || session.voice_created_at;
    let status = 'active';
    let daysLeft = 7;
    let message = 'Voice active';

    if (lastUsed) {
        try {
            const lastDt = new Date(lastUsed);
            const elapsed = Math.floor((Date.now() - lastDt.getTime()) / (1000 * 60 * 60 * 24));
            daysLeft = Math.max(0, 7 - elapsed);

            if (daysLeft <= 0) {
                status = 'expired';
                message = 'Voice expired. Please re-upload.';
            } else if (daysLeft <= 2) {
                status = 'warning';
                message = `Expiring in ${daysLeft} days.`;
            }
        } catch { }
    }

    return {
        has_voice: true,
        voice_id: voiceId,
        voice_status: status,
        days_remaining: daysLeft,
        message
    };
}

export async function testWaveSpeedKey() {
    const waveSpeedKey = await Storage.getWaveSpeedKey();
    const response = await fetch(`${API_BASE}/settings/wavespeed-key/test`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-WaveSpeed-Key': waveSpeedKey || ''
        }
    });
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.error || 'API key test failed');
    }
    return data;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

async function detectFileMetadata(file) {
    // Try to detect file type and extract participants
    const text = await file.text();
    let detected_type = 'Unknown';
    let participants = [];

    try {
        // Check if JSON
        const data = JSON.parse(text);

        // Instagram format
        if (data.messages && Array.isArray(data.messages)) {
            detected_type = 'Instagram';
            const senders = new Set();
            for (const msg of data.messages.slice(0, 100)) {
                if (msg.sender_name) senders.add(msg.sender_name);
            }
            participants = Array.from(senders);
        }
        // Discord format
        else if (data.id && data.type && data.messages) {
            detected_type = 'Discord';
        }
    } catch {
        // Not JSON, try WhatsApp text format
        const lines = text.split('\n').slice(0, 50);
        const whatsappPattern = /^\d{1,2}\/\d{1,2}\/\d{2,4},\s\d{1,2}:\d{2}.*-\s(.*?):\s/;

        let matches = 0;
        const senders = new Set();
        for (const line of lines) {
            const match = line.match(whatsappPattern);
            if (match) {
                matches++;
                senders.add(match[1]);
            }
        }

        if (matches > 5) {
            detected_type = 'WhatsApp';
            participants = Array.from(senders);
        }
    }

    return { detected_type, participants };
}

// --- Voice File Preview ---
export async function getVoicePreviewUrl(sessionId, fileId) {
    const upload = await Storage.getUpload(sessionId, fileId);
    if (!upload) return null;

    const blob = new Blob([upload.data], { type: upload.mime_type || 'audio/mpeg' });
    return URL.createObjectURL(blob);
}

// Utility to get image from local storage or API
export async function getChatImageUrl(sessionId, filename) {
    // Check if we have it locally
    const imageId = filename.replace('ai_', '').replace('user_', '').replace('.png', '').replace('.jpg', '');
    const localUrl = await Storage.getImageUrl(sessionId, imageId);
    if (localUrl) return localUrl;

    // Fallback to API
    return `${API_BASE}/chat/${sessionId}/images/${filename}`;
}
