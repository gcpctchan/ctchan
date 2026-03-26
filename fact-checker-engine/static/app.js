document.addEventListener('DOMContentLoaded', () => {
    const editor = document.getElementById('editor');
    const verifyBtn = document.getElementById('verify-btn');
    const analysisContent = document.getElementById('analysis-content');
    const logOutput = document.getElementById('log-output');
    const statsView = document.getElementById('stats-view');
    const fileLabel = document.getElementById('file-label');
    const uploadTrigger = document.getElementById('upload-trigger');
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const wordCount = document.getElementById('word-count');
    const annotatedEditor = document.getElementById('annotated-editor');
    const exportPdfBtn = document.getElementById('export-pdf-btn');

    const landingScreen = document.getElementById('landing-screen');
    const modeDrafter = document.getElementById('mode-drafter');
    const modeAuditor = document.getElementById('mode-auditor');
    const settingsBox = document.querySelector('.settings-box');
    const exitBtn = document.getElementById('exit-btn');

    let activeWorkflow = 'drafter'; // 'drafter' or 'auditor'
    let currentAnnotations = [];

    // --- Switch between Landing and Dashboard ---
    function enterWorkspace(wf) {
        activeWorkflow = wf;
        landingScreen.classList.add('hidden');
        dropZone.classList.remove('hidden');
        
        if (wf === 'auditor') {
             // Change visual labels for Auditor
             document.querySelector('.breadcrumbs strong').innerText = 'Citation Auditor';
             document.getElementById('editor').placeholder = 'Paste publication text here containing URLs or parenthetical citations...';
             document.querySelector('.document-panel h2').innerText = 'Citation Source';
             verifyBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Verify Citations';
             settingsBox.classList.add('hidden'); 
             addLog("Initiated Citation Auditor workspace. Scanning existing links.");
        } else {
             document.querySelector('.breadcrumbs strong').innerText = 'Workbench (Drafter)';
             document.getElementById('editor').placeholder = 'Type your draft here or drop a file to begin...';
             document.querySelector('.document-panel h2').innerText = 'Speech Draft';
             verifyBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Verify Claims';
             settingsBox.classList.remove('hidden');
             addLog("Initiated Speech Drafter workspace. Generating new citations.");
        }
    }

    modeDrafter.addEventListener('click', () => enterWorkspace('drafter'));
    modeAuditor.addEventListener('click', () => enterWorkspace('auditor'));

    exitBtn.addEventListener('click', () => {
        const text = editor.value;
        if (text.trim()) {
            const confirmed = confirm("Are you sure you want to switch workspace? Any unsaved work will be lost. Ensure you have exported your citations.");
            if (!confirmed) return;
        }
        editor.value = '';
        wordCount.innerText = '0 Words';
        analysisContent.innerHTML = '<div class="empty-state"><i class="fa-solid fa-glasses"></i><p>No text analyzed yet.</p></div>';
        
        landingScreen.classList.remove('hidden');
        dropZone.classList.add('hidden');
        addLog("Returned to home screen. Workspace cleared.");
    });

    // -----------------------------------------------------------------------
    // Word Count Tracker
    // -----------------------------------------------------------------------
    editor.addEventListener('input', () => {
        const text = editor.value;
        const count = text.trim().split(/\s+/).filter(Boolean).length;
        wordCount.innerText = `${count} Words`;
        
        // Reset overlay if editing
        if (!annotatedEditor.classList.contains('hidden')) {
             annotatedEditor.classList.add('hidden');
             editor.classList.remove('hidden');
        }
    });

    // -----------------------------------------------------------------------
    // Logging Helper
    // -----------------------------------------------------------------------
    function addLog(message, type = 'info') {
        const item = document.createElement('div');
        item.className = `log-item ${type}`;
        item.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;
        logOutput.appendChild(item);
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    // -----------------------------------------------------------------------
    // UI Visual Indicators
    // -----------------------------------------------------------------------
    function setScanning(isLoading) {
        if (isLoading) {
            verifyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
            verifyBtn.disabled = true;
            addLog("Scanning text & verifying assertions...");
        } else {
            verifyBtn.innerHTML = activeWorkflow === 'auditor' ? '<i class="fa-solid fa-bolt"></i> Verify Citations' : '<i class="fa-solid fa-bolt"></i> Verify Claims';
            verifyBtn.disabled = false;
        }
    }

    // -----------------------------------------------------------------------
    // Post Text for Verification
    // -----------------------------------------------------------------------
    verifyBtn.addEventListener('click', async () => {
        const textToVerify = editor.value;
        let selectedMode = 'grounding';
        
        if (activeWorkflow === 'auditor') {
             selectedMode = 'auditor';
        } else {
             selectedMode = document.querySelector('input[name="mode"]:checked').value;
        }

        if (!textToVerify.trim()) {
             addLog("Warning: Input text area is empty.", "warning");
             alert("Please enter text to verify.");
             return;
        }

        setScanning(true);
        analysisContent.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Consulting sources...</p></div>';

        try {
            const response = await fetch('/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: textToVerify, mode: selectedMode })
            });

            if (!response.ok) throw new Error(`HTTP Error ${response.status}`);

            const data = await response.json();
            setScanning(false);
            addLog(`Analysis complete. Mode: ${selectedMode}.`);
            renderResults(data, selectedMode);

        } catch (error) {
            setScanning(false);
            addLog(`Error during verification: ${error.message}`, 'danger');
            analysisContent.innerHTML = `<div class="empty-state"><i class="fa-solid fa-circle-exclamation" style="color:var(--danger-color);"></i><p>Verification Failed</p><span>${error.message}</span></div>`;
        }
    });

    // -----------------------------------------------------------------------
    // Render Annotations / Cards
    // -----------------------------------------------------------------------
    function renderResults(data, mode) {
        analysisContent.innerHTML = ''; // Clear prior results
        let annotations = [];

        if (mode === 'grounding' && data.annotations) {
             annotations = data.annotations;
        } else if (mode === 'function_calling' && data.annotated_segments) {
             annotations = data.annotated_segments;
        } else if (typeof data === 'object' && data.annotated_segments) {
             // Handle structured response fallback
             annotations = data.annotated_segments;
        }

        if (annotations.length === 0) {
             analysisContent.innerHTML = '<div class="empty-state"><i class="fa-solid fa-check-circle" style="color:var(--success-color);"></i><p>No claims flagged.</p><span>Statements may be rhetoric or opinion.</span></div>';
             statsView.innerHTML = '<span class="badge badge-neutral">0 Claims flags</span>';
             return;
        }

        statsView.innerHTML = `
            <span class="badge badge-neutral">${annotations.length} ${activeWorkflow === 'auditor' ? 'Citation items' : 'Claim items'}</span>
            <button class="btn btn-secondary btn-sm" id="export-pdf-btn">
                <i class="fa-solid fa-file-pdf"></i> ${activeWorkflow === 'auditor' ? 'Export Audit Report' : 'Export Citations'}
            </button>
        `;
        
        // Re-bind click listener as we just replaced innerHTML
        document.getElementById('export-pdf-btn').addEventListener('click', () => exportCitations(annotations));

        // Generate Inline Highlights for Annotated View
        let originalText = data.original_text || editor.value;
        let highlightedText = originalText;

        annotations.forEach((claim, idx) => {
             if (claim.claimed_text) {
                  const highlightClass = `inline-highlight ${claim.status}`;
                  // Escape special characters for safe regex replacement & trim trailing spaces
                  const safeClaim = claim.claimed_text.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                  const regex = new RegExp(`(${safeClaim})`, 'gi');
                  
                  let occurrence = 0;
                  highlightedText = highlightedText.replace(regex, (match, p1) => {
                       occurrence++;
                       if (occurrence === 1) {
                            return `<span class="${highlightClass}" id="highlight-${idx}" title="${claim.source || 'Verified'}">${p1}</span>`;
                       }
                       return `<span class="${highlightClass}" title="${claim.source || 'Verified'}">${p1}</span>`;
                  });
             }
        });

        annotatedEditor.innerHTML = highlightedText;
        annotatedEditor.classList.remove('hidden');
        editor.classList.add('hidden');

        // Allow click-to-edit toggle
        annotatedEditor.title = "Double-click to edit text";
        annotatedEditor.addEventListener('dblclick', () => {
             annotatedEditor.classList.add('hidden');
             editor.classList.remove('hidden');
             editor.focus();
        });

        annotations.forEach((claim, index) => {
             const card = document.createElement('div');
             card.className = `verified-card ${claim.status}`;
             
             let statusIcon = '<i class="fa-solid fa-circle-check"></i>';
             let statusLabel = 'Verified';
             if (claim.status === 'conflicting') { statusIcon = '<i class="fa-solid fa-circle-xmark"></i>'; statusLabel = 'Conflicting Data'; }
             if (claim.status === 'unverified') { statusIcon = '<i class="fa-solid fa-circle-question"></i>'; statusLabel = 'Unverified Assertion'; }
             if (claim.status === 'opinion') { statusIcon = '<i class="fa-solid fa-comment-dots"></i>'; statusLabel = 'Opinion Element'; }

             card.innerHTML = `
                 <div class="card-title">
                     <span style="color: var(--${claim.status === 'conflicting' ? 'danger' : claim.status === 'unverified' ? 'warning' : 'success'}-color); margin-right: 0.5rem;">
                         ${statusIcon}
                     </span>
                     <strong>"${claim.claimed_text || "unspecified snippet"}"</strong>
                     <span style="font-size:0.75rem; color:var(--text-muted); float:right;">${statusLabel}</span>
                 </div>
                 <p class="card-detail">${claim.explanation || claim.detail || 'Context reference provided by background analysis.'}</p>
                 ${claim.suggested_correction ? `<p class="card-detail" style="border-top:1px dashed var(--border-color); padding-top:4px; color:var(--danger-color);">💡 Suggested Correction: ${claim.suggested_correction}</p>` : ''}
                 ${activeWorkflow === 'auditor' ? `
                    ${claim.source ? `
                       <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-top: 0.5rem;">
                           ${claim.url && claim.url !== '#' ? `<a href="${claim.url}" target="_blank" class="card-source"><i class="fa-solid fa-link"></i> Source: ${claim.source}</a>` : `<span class="card-source" style="cursor: default; color: var(--text-muted);"><i class="fa-solid fa-link-slash"></i> Source: ${claim.source} (${claim.url_status_error || "Unreachable"})</span>`}
                           ${claim.url && claim.url !== '#' ? '<span class="badge" style="background: rgba(16, 185, 129, 0.1); color: var(--success-color); border: 1px solid var(--success-color); padding: 0.2rem 0.5rem; font-size:0.7rem; border-radius:4px;">Link Verified</span>' : '<span class="badge" style="background: rgba(239, 68, 68, 0.1); color: var(--danger-color); border: 1px solid var(--danger-color); padding: 0.2rem 0.5rem; font-size:0.7rem; border-radius:4px;">Broken Link</span>'}
                       </div>
                    ` : ''}
                 ` : `
                    ${claim.source && claim.url ? `
                       <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-top: 0.5rem;">
                           <a href="${claim.url}" target="_blank" class="card-source"><i class="fa-solid fa-link"></i> Source: ${claim.source}</a>
                       </div>
                    ` : claim.source ? `
                       <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-top: 0.5rem;">
                           <span class="card-source" style="cursor: default; color: var(--text-muted);"><i class="fa-solid fa-link"></i> Source Found: ${claim.source}</span>
                       </div>
                    ` : ''}
                 `}
             `;
              card.style.cursor = 'pointer';
              card.addEventListener('click', () => {
                   const targetEl = document.getElementById(`highlight-${index}`);
                   if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        // Temporary flash effect
                        const originalStyle = targetEl.style.boxShadow;
                        targetEl.style.boxShadow = '0 0 0 3px var(--accent-color)';
                        targetEl.style.transition = 'box-shadow 0.3s ease';
                        setTimeout(() => {
                             targetEl.style.boxShadow = originalStyle;
                        }, 1500);
                   }
              });

             analysisContent.appendChild(card);
        });
    }

    // -----------------------------------------------------------------------
    // File Upload / Drag & Drop
    // -----------------------------------------------------------------------
    uploadTrigger.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
         dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

    ['dragenter', 'dragover'].forEach(eventName => {
         dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
         dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    dropZone.addEventListener('drop', (e) => {
         const files = e.dataTransfer.files;
         if (files.length > 0) {
              uploadFile(files[0]);
         }
    });

    async function uploadFile(file) {
         addLog(`Uploading file: ${file.name}`);
         fileLabel.innerText = `Preparing ${file.name}...`;

         const formData = new FormData();
         formData.append('file', file);

         try {
             const response = await fetch('/upload', { method: 'POST', body: formData });
             if (!response.ok) throw new Error("Upload Failed");

             const result = await response.json();
             editor.value = result.text;
             fileLabel.innerText = file.name;
             addLog(`Successfully extracted text from ${file.name}.`);
             
             // Trigger word count manually on update
             editor.dispatchEvent(new Event('input'));

         } catch (error) {
              addLog(`Upload error: ${error.message}`, "danger");
              fileLabel.innerText = "Upload Error";
         }
    }

    // -----------------------------------------------------------------------
    // Export Citations (PDF Trigger)
    // -----------------------------------------------------------------------
    function exportCitations(annotations) {
         addLog("Generating citation report PDF...");
         try {
             const form = document.createElement('form');
             form.method = 'POST';
             form.action = '/export_citations';
             // target="_blank" is safer for downloading buffers without navigation crashes
             form.target = '_blank'; 
             
             const input = document.createElement('input');
             input.type = 'hidden';
             input.name = 'annotations';
             input.value = JSON.stringify(annotations);
             form.appendChild(input);

             const modeInput = document.createElement('input');
             modeInput.type = 'hidden';
             modeInput.name = 'mode';
             modeInput.value = activeWorkflow;
             form.appendChild(modeInput);
             
             document.body.appendChild(form);
             form.submit();
             document.body.removeChild(form);
             
             addLog("Citation report trigger sent to browser downloads.");
         } catch (error) {
             addLog(`Export Error: ${error.message}`, 'danger');
         }
    }
});
