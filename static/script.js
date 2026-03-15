/* ═══════════════════════════════════════════════════════════
   YouTube Downloader — Frontend Logic (Direct Streaming)
   No server-side storage — streams directly to browser
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── DOM refs ────────────────────────────────────────────
    const form = document.getElementById('download-form');
    const urlInput = document.getElementById('url-input');
    const btnDownload = document.getElementById('btn-download');
    const extractingSection = document.getElementById('extracting-section');
    const resultSection = document.getElementById('result-section');
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoTitle = document.getElementById('video-title');
    const videoDuration = document.getElementById('video-duration');
    const btnSave = document.getElementById('btn-save');
    const btnAnother = document.getElementById('btn-another');
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    const btnRetry = document.getElementById('btn-retry');
    const qualityOptions = document.querySelectorAll('.quality-option');

    // ── Quality radio buttons ───────────────────────────────
    qualityOptions.forEach(opt => {
        opt.addEventListener('click', () => {
            qualityOptions.forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            opt.querySelector('input[type="radio"]').checked = true;
        });
    });

    // ── Reset UI helper ─────────────────────────────────────
    function resetUI() {
        form.style.display = '';
        extractingSection.classList.remove('active');
        resultSection.classList.remove('active');
        errorSection.classList.remove('active');
        btnDownload.classList.remove('loading');
    }

    // ── "Download Another" / "Try Again" buttons ────────────
    btnAnother.addEventListener('click', () => {
        resetUI();
        urlInput.value = '';
        urlInput.focus();
    });

    btnRetry.addEventListener('click', () => {
        resetUI();
        urlInput.focus();
    });

    // ── Format duration ─────────────────────────────────────
    function formatDuration(seconds) {
        if (!seconds) return '';
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    // ── Form submit ─────────────────────────────────────────
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        const quality = document.querySelector('input[name="quality"]:checked').value;

        // Show extracting state
        form.style.display = 'none';
        extractingSection.classList.add('active');
        resultSection.classList.remove('active');
        errorSection.classList.remove('active');

        try {
            // 1. Extract video info (no download yet)
            const resp = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, quality }),
            });

            let data;
            try {
                data = await resp.json();
            } catch (jsonErr) {
                throw new Error(`Server returned a non-JSON response (Status: ${resp.status}). Check server logs.`);
            }

            if (!resp.ok) {
                throw new Error(data.error || `Failed to extract video info (Status: ${resp.status})`);
            }

            // 2. Show video preview + download link
            extractingSection.classList.remove('active');

            videoTitle.textContent = data.title || 'Video';
            videoDuration.textContent = data.duration ? `Duration: ${formatDuration(data.duration)}` : '';

            if (data.thumbnail) {
                videoThumbnail.src = data.thumbnail;
                videoThumbnail.style.display = 'block';
            } else {
                videoThumbnail.style.display = 'none';
            }

            // Direct URL from Google's servers — clicking this triggers browser native download
            btnSave.href = data.direct_url;
            // Native HTML5 download attribute to force download instead of watching in-browser
            btnSave.setAttribute('download', '');
            
            resultSection.classList.add('active');

        } catch (err) {
            extractingSection.classList.remove('active');
            showError(err.message);
        }
    });

    // ── Show error ──────────────────────────────────────────
    function showError(msg) {
        form.style.display = 'none';
        errorMessage.textContent = msg;
        errorSection.classList.add('active');
    }
})();
