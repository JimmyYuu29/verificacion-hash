/**
 * Hash Verification Application - Frontend JavaScript
 * Handles UI interactions and API communication
 */

// State management
let selectedFile = null;
let currentMetadata = null;

// Theme management
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Update theme icon
    const icon = document.querySelector('.theme-icon');
    icon.textContent = newTheme === 'dark' ? '\u2600' : '\u263E';
}

// Initialize theme from localStorage
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const icon = document.querySelector('.theme-icon');
    if (icon) {
        icon.textContent = savedTheme === 'dark' ? '\u2600' : '\u263E';
    }
}

// Loading overlay
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

// Hash verification
async function verifyHash() {
    const hashInput = document.getElementById('hashInput');
    const hashCode = hashInput.value.trim().toUpperCase();

    if (!hashCode) {
        showError('Por favor, introduzca un codigo hash / Please enter a hash code');
        return;
    }

    // Validate format - accept both full hash and short code
    const fullHashPattern = /^[A-Z]{2}-[A-Z0-9]{12}$/;
    const shortCodePattern = /^[A-Z0-9]{6}$/;

    if (!fullHashPattern.test(hashCode) && !shortCodePattern.test(hashCode)) {
        showError('Formato invalido. Use: XX-XXXXXXXXXXXX (completo) o XXXXXX (codigo corto) / Invalid format. Use: XX-XXXXXXXXXXXX (full) or XXXXXX (short code)');
        return;
    }

    showLoading();

    try {
        const response = await fetch(`/api/verify/${hashCode}`);
        const data = await response.json();

        if (response.ok && data.success) {
            currentMetadata = data.metadata;
            showResults(data.metadata);
        } else {
            showError(data.detail || 'Hash code not found');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error de conexion. Por favor, intente de nuevo. / Connection error. Please try again.');
    } finally {
        hideLoading();
    }
}

// File handling
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        if (file.type !== 'application/pdf') {
            showError('Por favor, seleccione un archivo PDF / Please select a PDF file');
            return;
        }

        selectedFile = file;

        const fileInfo = document.getElementById('selectedFile');
        fileInfo.style.display = 'flex';
        fileInfo.innerHTML = `
            <span class="file-name">${file.name}</span>
            <span class="file-size">${formatFileSize(file.size)}</span>
        `;

        document.getElementById('verifyIntegrityBtn').disabled = false;
    }
}

// Drag and drop
document.addEventListener('DOMContentLoaded', function() {
    initTheme();

    const uploadArea = document.getElementById('uploadArea');

    if (uploadArea) {
        uploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const file = files[0];
                if (file.type === 'application/pdf') {
                    selectedFile = file;
                    const fileInput = document.getElementById('fileInput');

                    // Create new FileList-like object
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    fileInput.files = dt.files;

                    handleFileSelect({ target: fileInput });
                } else {
                    showError('Por favor, seleccione un archivo PDF / Please select a PDF file');
                }
            }
        });
    }

    // Enter key support for hash input
    const hashInput = document.getElementById('hashInput');
    if (hashInput) {
        hashInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                verifyHash();
            }
        });
    }
});

// Integrity verification
async function verifyIntegrity() {
    const hashInput = document.getElementById('hashInput');
    const hashCode = hashInput.value.trim().toUpperCase();

    if (!hashCode) {
        showError('Por favor, introduzca el codigo hash primero / Please enter the hash code first');
        return;
    }

    if (!selectedFile) {
        showError('Por favor, seleccione un archivo PDF / Please select a PDF file');
        return;
    }

    showLoading();

    try {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const response = await fetch(`/api/verify/integrity?hash_code=${encodeURIComponent(hashCode)}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showIntegrityResult(data);
        } else {
            showError(data.detail || 'Error verifying integrity');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error de conexion. Por favor, intente de nuevo. / Connection error. Please try again.');
    } finally {
        hideLoading();
    }
}

// Display results
function showResults(metadata) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');

    const hashInfo = metadata.hash_info || {};
    const docInfo = metadata.document_info || {};
    const userInfo = metadata.user_info || {};
    const formData = metadata.form_data || {};

    let html = `
        <div class="result-header success">
            <span class="result-icon">&#10004;</span>
            <div>
                <div class="result-title">DOCUMENTO ENCONTRADO / DOCUMENT FOUND</div>
                <div class="result-subtitle">El documento ha sido verificado exitosamente / Document has been verified successfully</div>
            </div>
        </div>

        <div class="result-grid">
            <div class="result-card">
                <h4>Tipo de Documento / Document Type</h4>
                <div class="value">${escapeHtml(docInfo.type_display || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Codigo Hash Completo / Full Hash Code</h4>
                <div class="value mono">${escapeHtml(hashInfo.hash_code || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Codigo Corto / Short Code</h4>
                <div class="value mono">${escapeHtml(hashInfo.short_code || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Fecha de Creacion / Creation Date</h4>
                <div class="value">${escapeHtml(docInfo.creation_timestamp || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Usuario / User</h4>
                <div class="value">${escapeHtml(userInfo.user_id || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Cliente / Client</h4>
                <div class="value">${escapeHtml(userInfo.client_name || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Nombre de Archivo / File Name</h4>
                <div class="value">${escapeHtml(docInfo.file_name || 'N/A')}</div>
            </div>
        </div>

        <div class="result-card" style="margin-bottom: 20px;">
            <h4>Detalles del Hash / Hash Details</h4>
            <div style="display: grid; gap: 10px; margin-top: 10px;">
                <div>
                    <span style="color: var(--text-muted);">Algoritmo / Algorithm:</span>
                    <span class="mono">${escapeHtml(hashInfo.algorithm || 'SHA-256')}</span>
                </div>
                <div>
                    <span style="color: var(--text-muted);">Content Hash:</span>
                    <div class="value mono" style="font-size: 0.85rem; word-break: break-all;">${escapeHtml(hashInfo.content_hash || 'N/A')}</div>
                </div>
                <div>
                    <span style="color: var(--text-muted);">Combined Hash:</span>
                    <div class="value mono" style="font-size: 0.85rem; word-break: break-all;">${escapeHtml(hashInfo.combined_hash || 'N/A')}</div>
                </div>
            </div>
        </div>
    `;

    // Form data section
    if (Object.keys(formData).length > 0) {
        html += `
            <div class="form-data-section">
                <h4>Datos del Formulario / Form Data</h4>
                <div class="form-data-grid">
        `;

        for (const [key, value] of Object.entries(formData)) {
            html += `
                <div class="form-data-item">
                    <span class="label">${escapeHtml(formatFieldName(key))}</span>
                    <span class="value">${escapeHtml(String(value))}</span>
                </div>
            `;
        }

        html += `
                </div>
            </div>
        `;
    }

    // Export buttons
    html += `
        <div class="export-buttons">
            <button class="btn btn-outline" onclick="exportJSON()">
                Exportar JSON / Export JSON
            </button>
            <button class="btn btn-outline" onclick="printCertificate()">
                Imprimir Certificado / Print Certificate
            </button>
        </div>
    `;

    resultsContent.innerHTML = html;
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Show integrity result
function showIntegrityResult(data) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');

    const isValid = data.valid;
    const statusClass = isValid ? 'valid' : 'invalid';
    const icon = isValid ? '&#10004;' : '&#10008;';
    const title = isValid
        ? 'DOCUMENTO AUTENTICO / AUTHENTIC DOCUMENT'
        : 'DOCUMENTO MODIFICADO / MODIFIED DOCUMENT';

    let html = `
        <div class="integrity-result ${statusClass}">
            <h4>
                <span>${icon}</span>
                ${title}
            </h4>
            <p>${escapeHtml(data.message)}</p>
            <div style="margin-top: 15px; font-size: 0.9rem;">
                <p><strong>Hash Code:</strong> <span class="mono">${escapeHtml(data.hash_code)}</span></p>
                ${data.calculated_hash ? `<p><strong>Calculated Hash:</strong> <span class="mono" style="word-break: break-all;">${escapeHtml(data.calculated_hash)}</span></p>` : ''}
                ${data.stored_hash ? `<p><strong>Stored Hash:</strong> <span class="mono" style="word-break: break-all;">${escapeHtml(data.stored_hash)}</span></p>` : ''}
            </div>
        </div>
    `;

    // If we have current metadata, show it too
    if (currentMetadata) {
        html = showResultsHTML(currentMetadata) + html;
    }

    resultsContent.innerHTML = html;
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Generate results HTML (helper for integrity result)
function showResultsHTML(metadata) {
    const hashInfo = metadata.hash_info || {};
    const docInfo = metadata.document_info || {};
    const userInfo = metadata.user_info || {};

    return `
        <div class="result-header success">
            <span class="result-icon">&#10004;</span>
            <div>
                <div class="result-title">DOCUMENTO ENCONTRADO / DOCUMENT FOUND</div>
            </div>
        </div>

        <div class="result-grid" style="margin-bottom: 20px;">
            <div class="result-card">
                <h4>Tipo de Documento</h4>
                <div class="value">${escapeHtml(docInfo.type_display || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Codigo Hash</h4>
                <div class="value mono">${escapeHtml(hashInfo.hash_code || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Codigo Corto</h4>
                <div class="value mono">${escapeHtml(hashInfo.short_code || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Cliente</h4>
                <div class="value">${escapeHtml(userInfo.client_name || 'N/A')}</div>
            </div>
            <div class="result-card">
                <h4>Fecha de Creacion</h4>
                <div class="value">${escapeHtml(docInfo.creation_timestamp || 'N/A')}</div>
            </div>
        </div>
    `;
}

// Show error
function showError(message) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');

    resultsContent.innerHTML = `
        <div class="result-header error">
            <span class="result-icon">&#10008;</span>
            <div>
                <div class="result-title">ERROR</div>
                <div class="result-subtitle">${escapeHtml(message)}</div>
            </div>
        </div>
    `;

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Load statistics
async function loadStats() {
    showLoading();

    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        if (response.ok) {
            showStats(data);
        } else {
            showError('Error loading statistics');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error de conexion / Connection error');
    } finally {
        hideLoading();
    }
}

// Display statistics
function showStats(stats) {
    const statsContent = document.getElementById('statsContent');

    let html = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">${stats.total_documents}</div>
                <div class="label">Total Documentos</div>
            </div>
            <div class="stat-card">
                <div class="number">${Object.keys(stats.by_type).length}</div>
                <div class="label">Tipos</div>
            </div>
            <div class="stat-card">
                <div class="number">${Object.keys(stats.by_user).length}</div>
                <div class="label">Usuarios</div>
            </div>
        </div>
    `;

    // By type breakdown
    if (Object.keys(stats.by_type).length > 0) {
        html += `
            <div class="stats-breakdown">
                <h4>Por Tipo de Documento / By Document Type</h4>
                <ul class="stats-list">
        `;
        for (const [type, count] of Object.entries(stats.by_type)) {
            html += `<li><span>${escapeHtml(type)}</span><span>${count}</span></li>`;
        }
        html += `</ul></div>`;
    }

    // By user breakdown
    if (Object.keys(stats.by_user).length > 0) {
        html += `
            <div class="stats-breakdown">
                <h4>Por Usuario / By User</h4>
                <ul class="stats-list">
        `;
        for (const [user, count] of Object.entries(stats.by_user)) {
            html += `<li><span>${escapeHtml(user)}</span><span>${count}</span></li>`;
        }
        html += `</ul></div>`;
    }

    // Recent documents
    if (stats.recent_documents && stats.recent_documents.length > 0) {
        html += `
            <div class="stats-breakdown">
                <h4>Documentos Recientes / Recent Documents</h4>
                <ul class="stats-list">
        `;
        for (const doc of stats.recent_documents) {
            const shortCode = doc.short_code ? ` (${escapeHtml(doc.short_code)})` : '';
            html += `
                <li style="flex-direction: column; align-items: flex-start;">
                    <span class="mono">${escapeHtml(doc.hash_code)}${shortCode}</span>
                    <small style="color: var(--text-muted);">${escapeHtml(doc.document_type)} - ${escapeHtml(doc.client_name)}</small>
                </li>
            `;
        }
        html += `</ul></div>`;
    }

    statsContent.innerHTML = html;
    statsContent.style.display = 'block';
}

// Export functions
function exportJSON() {
    if (!currentMetadata) {
        showError('No hay datos para exportar / No data to export');
        return;
    }

    const dataStr = JSON.stringify(currentMetadata, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `verification_${currentMetadata.hash_info?.hash_code || 'document'}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function printCertificate() {
    if (!currentMetadata) {
        showError('No hay datos para imprimir / No data to print');
        return;
    }

    const hashInfo = currentMetadata.hash_info || {};
    const docInfo = currentMetadata.document_info || {};
    const userInfo = currentMetadata.user_info || {};

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verification Certificate</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 40px; max-width: 800px; margin: 0 auto; }
                h1 { text-align: center; color: #0056b3; border-bottom: 2px solid #0056b3; padding-bottom: 10px; }
                .section { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 8px; }
                .section h3 { margin-top: 0; color: #333; }
                .field { margin: 8px 0; }
                .field label { font-weight: bold; color: #666; }
                .field value { display: block; margin-top: 3px; }
                .hash { font-family: monospace; word-break: break-all; background: #eee; padding: 5px; border-radius: 4px; }
                .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
                @media print { body { padding: 20px; } }
            </style>
        </head>
        <body>
            <h1>FORVIS MAZARS<br>Document Verification Certificate</h1>

            <div class="section">
                <h3>Document Information</h3>
                <div class="field">
                    <label>Document Type:</label>
                    <value>${escapeHtml(docInfo.type_display || 'N/A')}</value>
                </div>
                <div class="field">
                    <label>Hash Code (Full):</label>
                    <value class="hash">${escapeHtml(hashInfo.hash_code || 'N/A')}</value>
                </div>
                <div class="field">
                    <label>Short Code (Codigo Corto):</label>
                    <value class="hash">${escapeHtml(hashInfo.short_code || 'N/A')}</value>
                </div>
                <div class="field">
                    <label>Creation Date:</label>
                    <value>${escapeHtml(docInfo.creation_timestamp || 'N/A')}</value>
                </div>
                <div class="field">
                    <label>File Name:</label>
                    <value>${escapeHtml(docInfo.file_name || 'N/A')}</value>
                </div>
            </div>

            <div class="section">
                <h3>User Information</h3>
                <div class="field">
                    <label>User:</label>
                    <value>${escapeHtml(userInfo.user_id || 'N/A')}</value>
                </div>
                <div class="field">
                    <label>Client:</label>
                    <value>${escapeHtml(userInfo.client_name || 'N/A')}</value>
                </div>
            </div>

            <div class="section">
                <h3>Hash Details</h3>
                <div class="field">
                    <label>Algorithm:</label>
                    <value>${escapeHtml(hashInfo.algorithm || 'SHA-256')}</value>
                </div>
                <div class="field">
                    <label>Content Hash:</label>
                    <value class="hash">${escapeHtml(hashInfo.content_hash || 'N/A')}</value>
                </div>
                <div class="field">
                    <label>Combined Hash:</label>
                    <value class="hash">${escapeHtml(hashInfo.combined_hash || 'N/A')}</value>
                </div>
            </div>

            <div class="footer">
                <p>This certificate was generated on ${new Date().toLocaleString()}</p>
                <p>FORVIS MAZARS - Document Hash Verification System</p>
            </div>
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.print();
}

// Utility functions
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatFieldName(name) {
    return name
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
}
