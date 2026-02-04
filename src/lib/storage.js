/**
 * Client-side Storage Layer for AlterEcho
 * Uses IndexedDB via Dexie.js for persistent browser storage
 */

import Dexie from 'dexie';

// Create database instance
// Using AlterEchoDBv2 as a fresh database to avoid migration issues
const db = new Dexie('AlterEchoDBv2');

// Define schema
// Note: First field is primary key. '&' means unique index
db.version(1).stores({
    settings: '++id',                              // Single row for user settings
    sessions: 'id, name, created_at',              // Session metadata (id is primary key)
    messages: '&session_id',                       // Message history per session (unique session_id as key)
    uploads: '++id, session_id, type, file_id',    // Uploaded files (text/voice)
    preprocessed: '&session_id',                   // Processed AI data per session (unique session_id as key)
    images: '++id, session_id, image_id',          // Chat images
    tempZips: 'zip_id',                            // Temporary ZIP extraction
    secrets: 'key'                                 // API keys (stored unencrypted in IndexedDB)
});

// Open database immediately
db.open().catch(err => {
    console.error('Failed to open database:', err);
});

// Default settings - must match the options in SettingsModal.jsx
const DEFAULT_SETTINGS = {
    chatbot_model: "gemini-flash-latest",
    training_model: "gemini-3-flash-preview",
    embedding_model: "gemini-embedding-001",
    image_model: "gemini-2.5-flash-image"
};

// --- Settings ---
export async function getSettings() {
    const row = await db.settings.get(1);
    return row ? row.data : { ...DEFAULT_SETTINGS };
}

export async function saveSettings(newSettings) {
    const current = await getSettings();
    const merged = { ...current, ...newSettings };
    await db.settings.put({ id: 1, data: merged });
    return merged;
}

// --- Sessions ---
export async function getSessions() {
    const sessions = await db.sessions.toArray();
    // Sort by created_at desc
    sessions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return sessions;
}

export async function getSession(sessionId) {
    return await db.sessions.get(sessionId);
}

export async function createSession(name = "New Echo") {
    const sessionId = generateId(8);
    const now = new Date().toISOString();

    const session = {
        id: sessionId,
        name,
        created_at: now,
        preview: "No messages yet.",
        subject: null,
        wavespeed_voice_id: null,
        voice_created_at: null,
        voice_last_used_at: null
    };

    await db.sessions.add(session);

    // Initialize empty messages for this session
    await db.messages.put({ session_id: sessionId, messages: [] });

    return session;
}

export async function updateSession(sessionId, updates) {
    const session = await db.sessions.get(sessionId);
    if (!session) return null;

    const updated = { ...session, ...updates };
    await db.sessions.put(updated);
    return updated;
}

export async function deleteSession(sessionId) {
    // Delete session and all related data
    await db.sessions.delete(sessionId);
    await db.messages.delete(sessionId);
    await db.preprocessed.delete(sessionId);
    await db.uploads.where('session_id').equals(sessionId).delete();
    await db.images.where('session_id').equals(sessionId).delete();
    return { success: true };
}

// --- Messages ---
export async function getMessages(sessionId) {
    const row = await db.messages.get(sessionId);
    return row ? row.messages : [];
}

export async function saveMessages(sessionId, messages) {
    await db.messages.put({ session_id: sessionId, messages });
    return messages;
}

export async function addMessage(sessionId, message) {
    const messages = await getMessages(sessionId);
    // Ensure message has an ID
    if (!message.id) {
        message.id = generateId(8);
    }
    messages.push(message);
    await saveMessages(sessionId, messages);
    return message;
}

export async function clearMessages(sessionId) {
    await db.messages.put({ session_id: sessionId, messages: [] });
    return { success: true };
}

// --- Uploads (text/voice files) ---
export async function getUploads(sessionId, fileType = null) {
    let query = db.uploads.where('session_id').equals(sessionId);
    const uploads = await query.toArray();

    if (fileType) {
        return uploads.filter(u => u.type === fileType);
    }
    return uploads;
}

export async function addUpload(sessionId, fileType, file, metadata = {}) {
    const fileId = generateId(12);

    // Read file as ArrayBuffer for storage
    const arrayBuffer = await file.arrayBuffer();

    const upload = {
        session_id: sessionId,
        type: fileType,
        file_id: fileId,
        original_name: file.name,
        saved_as: `${fileId}${getExtension(file.name)}`,
        detected_type: metadata.detected_type || null,
        participants: metadata.participants || [],
        subject: metadata.subject || null,
        data: arrayBuffer,
        mime_type: file.type,
        size: file.size,
        created_at: new Date().toISOString()
    };

    await db.uploads.add(upload);
    return upload;
}

export async function getUpload(sessionId, fileId) {
    const uploads = await db.uploads
        .where('session_id').equals(sessionId)
        .and(u => u.file_id === fileId)
        .toArray();
    return uploads[0] || null;
}

export async function updateUpload(sessionId, fileId, updates) {
    const upload = await getUpload(sessionId, fileId);
    if (!upload) return null;

    const updated = { ...upload, ...updates };
    await db.uploads.put(updated);
    return updated;
}

export async function deleteUpload(sessionId, fileType, fileId) {
    await db.uploads
        .where('session_id').equals(sessionId)
        .and(u => u.file_id === fileId)
        .delete();
    return { success: true };
}

// Get upload as Blob (for sending to backend)
export async function getUploadBlob(sessionId, fileId) {
    const upload = await getUpload(sessionId, fileId);
    if (!upload) return null;

    return new Blob([upload.data], { type: upload.mime_type });
}

// Get upload as File (for sending to backend)
export async function getUploadFile(sessionId, fileId) {
    const upload = await getUpload(sessionId, fileId);
    if (!upload) return null;

    return new File([upload.data], upload.original_name, { type: upload.mime_type });
}

// --- Preprocessed Data ---
export async function getPreprocessed(sessionId) {
    return await db.preprocessed.get(sessionId);
}

export async function savePreprocessed(sessionId, data) {
    const record = {
        session_id: sessionId,
        ...data,
        updated_at: new Date().toISOString()
    };
    await db.preprocessed.put(record);
    return record;
}

export async function deletePreprocessed(sessionId) {
    await db.preprocessed.delete(sessionId);
    return { success: true };
}

// --- Images ---
export async function getImage(sessionId, imageId) {
    const images = await db.images
        .where('session_id').equals(sessionId)
        .and(i => i.image_id === imageId)
        .toArray();
    return images[0] || null;
}

export async function saveImage(sessionId, imageId, imageData, metadata = {}) {
    // imageData can be Blob, ArrayBuffer, or base64 string
    let arrayBuffer;
    let mimeType = metadata.mime_type || 'image/png';

    if (imageData instanceof Blob) {
        arrayBuffer = await imageData.arrayBuffer();
        mimeType = imageData.type || mimeType;
    } else if (imageData instanceof ArrayBuffer) {
        arrayBuffer = imageData;
    } else if (typeof imageData === 'string') {
        // Base64 string
        const binary = atob(imageData);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        arrayBuffer = bytes.buffer;
    } else {
        throw new Error('Invalid image data type');
    }

    const image = {
        session_id: sessionId,
        image_id: imageId,
        data: arrayBuffer,
        mime_type: mimeType,
        source: metadata.source || 'unknown',
        created_at: new Date().toISOString()
    };

    // Check if image exists and update, otherwise add
    const existing = await getImage(sessionId, imageId);
    if (existing) {
        image.id = existing.id;
        await db.images.put(image);
    } else {
        await db.images.add(image);
    }

    return image;
}

export async function getImageUrl(sessionId, imageId) {
    const image = await getImage(sessionId, imageId);
    if (!image) return null;

    const blob = new Blob([image.data], { type: image.mime_type });
    return URL.createObjectURL(blob);
}

export async function deleteImage(sessionId, imageId) {
    await db.images
        .where('session_id').equals(sessionId)
        .and(i => i.image_id === imageId)
        .delete();
    return { success: true };
}

// --- Temp ZIPs ---
export async function saveTempZip(zipId, data) {
    const record = {
        zip_id: zipId,
        ...data,
        created_at: new Date().toISOString()
    };
    await db.tempZips.put(record);
    return record;
}

export async function getTempZip(zipId) {
    return await db.tempZips.get(zipId);
}

export async function deleteTempZip(zipId) {
    await db.tempZips.delete(zipId);
    return { success: true };
}

// --- Secrets (API Keys) ---
export async function getSecret(key) {
    const record = await db.secrets.get(key);
    return record ? record.value : null;
}

export async function saveSecret(key, value) {
    await db.secrets.put({ key, value });
    return { success: true };
}

export async function deleteSecret(key) {
    await db.secrets.delete(key);
    return { success: true };
}

export async function hasSecret(key) {
    const record = await db.secrets.get(key);
    return !!record;
}

// Convenience functions for specific keys
export async function getGeminiKey() {
    return await getSecret('gemini_api_key');
}

export async function saveGeminiKey(apiKey) {
    return await saveSecret('gemini_api_key', apiKey);
}

export async function hasGeminiKey() {
    return await hasSecret('gemini_api_key');
}

export async function getWaveSpeedKey() {
    return await getSecret('wavespeed_api_key');
}

export async function saveWaveSpeedKey(apiKey) {
    return await saveSecret('wavespeed_api_key', apiKey);
}

export async function hasWaveSpeedKey() {
    return await hasSecret('wavespeed_api_key');
}

// --- Utility Functions ---
function generateId(length = 8) {
    const chars = 'abcdef0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

function getExtension(filename) {
    const lastDot = filename.lastIndexOf('.');
    return lastDot !== -1 ? filename.substring(lastDot) : '';
}

// Export database for advanced usage
export { db };
