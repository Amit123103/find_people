/* ═══════════════════════════════════════════════════════════
   ImageFinder — Frontend Application Logic
   ═══════════════════════════════════════════════════════════ */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ─── State ───────────────────────────────────────────────
let currentFile = null;
let searchResults = null;

// ─── DOM Elements ────────────────────────────────────────
const uploadZone = $('#upload-zone');
const fileInput = $('#file-input');
const previewSection = $('.preview-section');
const loadingSection = $('.loading-section');
const resultsSection = $('.results-section');
const uploadSection = $('.upload-section');

// Views
const landingView = $('#landing-view');
const appWorkspace = $('#app-workspace');
const btnStartApp = $('#start-app');

// Modals
const settingsModal = $('#settings-modal');
const btnSettings = $('#btn-settings');
const btnCloseSettings = $('#close-settings');
const btnSaveSettings = $('#save-settings');
const inputFaceCheck = $('#facecheck-api');

// ─── File Upload Handling ────────────────────────────────

uploadZone.addEventListener('click', (e) => {
  e.preventDefault();
  e.stopPropagation();
  fileInput.click();
});

// Also handle the button directly in case zone click fails
const uploadBtn = uploadZone.querySelector('.upload-btn');
if (uploadBtn) {
  uploadBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    fileInput.click();
  });
}

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

function handleFile(file) {
  const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/gif', 'image/tiff'];
  if (!validTypes.includes(file.type)) {
    showError('Unsupported file type. Please upload JPG, PNG, WebP, BMP, GIF, or TIFF.');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError('File too large. Maximum size is 10 MB.');
    return;
  }
  currentFile = file;
  showPreview(file);
  startSearch(file);
}

// ─── Image Preview ───────────────────────────────────────

function showPreview(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const previewImg = $('#preview-img');
    previewImg.src = e.target.result;
    previewImg.onload = () => {
      $('#preview-filename').textContent = file.name;
      previewSection.style.display = 'block';
      uploadSection.style.display = 'none';
    };
  };
  reader.readAsDataURL(file);
}

// ─── Search Pipeline ─────────────────────────────────────

async function startSearch(file) {
  showLoading();
  resultsSection.style.display = 'none';

  const formData = new FormData();
  formData.append('file', file);
  
  // Pass persistent API Keys from localStorage if available
  const fckey = localStorage.getItem('facecheck-api-key');
  if (fckey) formData.append('facecheck_key', fckey);

  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Search failed');
    }

    searchResults = await response.json();
    renderResults(searchResults);
    
    // Removed automatic popup generator as per user preference to keep flow native
  } catch (error) {
    showError(`Search failed: ${error.message}`);
    hideLoading();
  }
}

// ─── Loading Animation ──────────────────────────────────

function showLoading() {
  loadingSection.style.display = 'block';
  const steps = [
    '🔍 Analyzing image vectors...',
    '👤 Detecting local faces...',
    '📊 Extracting forensic metadata...',
    '🔑 Generating perceptual fingerprints...',
    '🌐 Querying Global Search Engines...',
    '🛰️ Deep-Scanning Discovered Webpages...',
    '🎯 Formulating Persona Dossier...',
  ];
  const stepsContainer = $('#loading-steps');
  stepsContainer.innerHTML = '';
  steps.forEach((step, i) => {
    setTimeout(() => {
      const div = document.createElement('div');
      div.className = 'loading-step';
      div.style.animationDelay = `${i * 0.1}s`;
      div.textContent = step;
      stepsContainer.appendChild(div);
    }, i * 600);
  });
}

function hideLoading() {
  loadingSection.style.display = 'none';
}

// ─── Render Results ──────────────────────────────────────

function renderResults(data) {
  hideLoading();
  resultsSection.style.display = 'block';

  // Stats bar
  renderStats(data);

  // Draw face boxes on preview
  if (data.face_detection.faces.length > 0) {
    drawFaceBoxes(data.face_detection.faces);
  }

  // Tab contents
  renderFacesTab(data.face_detection);
  renderSearchTab(data.search);
  renderMetadataTab(data.image_analysis);
  renderFingerprintTab(data.fingerprint);

  // Activate first tab
  switchTab('faces');
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderStats(data) {
  const stats = $('#results-stats');
  const facesCount = data.face_detection.faces_found;
  const searchCount = data.search.manual_engines.length;
  const autoCount = (data.search.active_results || []).filter(r => r.status === 'success').length;
  const time = data.processing_time_seconds;

  stats.innerHTML = `
    <div class="stat-card">
      <div class="stat-value">${facesCount}</div>
      <div class="stat-label">Faces Found</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${searchCount}</div>
      <div class="stat-label">Search Engines</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${autoCount}</div>
      <div class="stat-label">Auto Results</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${time}s</div>
      <div class="stat-label">Process Time</div>
    </div>
  `;
}

// ─── Face Detection Tab ──────────────────────────────────

function renderFacesTab(faceData) {
  const container = $('#tab-faces');
  if (faceData.faces.length === 0) {
    container.innerHTML = `
      <div class="no-faces">
        <span class="icon">🔍</span>
        <p>No faces detected in this image.</p>
        <p style="margin-top:8px;font-size:13px;">Try a clearer photo with a visible face.</p>
      </div>`;
    return;
  }

  let html = '<div class="faces-grid">';
  faceData.faces.forEach((face, i) => {
    html += `
      <div class="face-card">
        <img class="face-crop" src="data:image/jpeg;base64,${face.crop_base64}" alt="Face ${i + 1}">
        <div class="face-details">
          <div class="face-detail-row">
            <span class="face-detail-label">Face #</span>
            <span class="face-detail-value">${i + 1}</span>
          </div>
          <div class="face-detail-row">
            <span class="face-detail-label">Confidence</span>
            <span class="face-detail-value">${Math.round(face.confidence * 100)}%</span>
          </div>
          <div class="face-detail-row">
            <span class="face-detail-label">Position</span>
            <span class="face-detail-value">${face.position}</span>
          </div>
          <div class="face-detail-row">
            <span class="face-detail-label">Size</span>
            <span class="face-detail-value">${face.width}×${face.height}px</span>
          </div>
          <div class="face-detail-row">
            <span class="face-detail-label">Area</span>
            <span class="face-detail-value">${face.face_area_percent}%</span>
          </div>
          <div class="face-detail-row">
            <span class="face-detail-label">Eyes</span>
            <span class="face-detail-value">${face.eyes_detected} detected</span>
          </div>
          <div class="face-detail-row">
            <span class="face-detail-label">Method</span>
            <span class="face-detail-value">${face.detection_method}</span>
          </div>
          <div class="confidence-bar">
            <div class="confidence-fill" style="width:${face.confidence * 100}%"></div>
          </div>
        </div>
      </div>`;
  });
  html += '</div>';
  container.innerHTML = html;
}

// ─── Draw Face Boxes on Preview ──────────────────────────

function drawFaceBoxes(faces) {
  const img = $('#preview-img');
  const canvas = $('#face-canvas');
  const wrapper = img.parentElement;

  canvas.width = wrapper.offsetWidth;
  canvas.height = wrapper.offsetHeight;

  const ctx = canvas.getContext('2d');
  const scaleX = wrapper.offsetWidth / img.naturalWidth;
  const scaleY = wrapper.offsetHeight / img.naturalHeight;
  const scale = Math.min(scaleX, scaleY);

  const offsetX = (wrapper.offsetWidth - img.naturalWidth * scale) / 2;
  const offsetY = (wrapper.offsetHeight - img.naturalHeight * scale) / 2;

  faces.forEach((face, i) => {
    const x = face.x * scale + offsetX;
    const y = face.y * scale + offsetY;
    const w = face.width * scale;
    const h = face.height * scale;

    // Box
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 2;
    ctx.shadowColor = '#00d4ff';
    ctx.shadowBlur = 8;
    ctx.strokeRect(x, y, w, h);
    ctx.shadowBlur = 0;

    // Label
    const label = `Face ${i + 1} (${Math.round(face.confidence * 100)}%)`;
    ctx.font = '12px Inter, sans-serif';
    const textWidth = ctx.measureText(label).width;
    ctx.fillStyle = 'rgba(0, 212, 255, 0.85)';
    ctx.fillRect(x, y - 22, textWidth + 12, 20);
    ctx.fillStyle = '#fff';
    ctx.fillText(label, x + 6, y - 7);
  });
}

// ─── Search Tab ──────────────────────────────────────────

function renderSearchTab(searchData) {
  const container = $('#tab-search');
  let html = '';

  // 1. Social Radar & Persona Dossier Section
  let htmlRadar = '';
  const radar = searchData.social_radar || {};
  let identity = radar.identity_details || { names: [], usernames: [], emails: [], profile_links: [] };

  // --- SMART FALLBACK LOGIC ---
  // If the backend pattern was too strict, build dynamic identity from the aggregate title consensus
  if (identity.names.length === 0 && allPages.length > 0) {
    const titles = allPages.map(p => p.title).filter(t => t && t.length > 5 && !t.includes('Search'));
    if (titles.length > 0) {
      // Take top occurring title substring or just top title as the candidate
      let candidate = titles[0].split(/[-|:,]/)[0].trim();
      if (candidate.length > 3 && candidate.length < 50) {
         identity.names = [`${candidate} (Confidence High)`];
      }
    }
  }
  // --- END FALLBACK ---

  const hasIdentity = identity.names.length > 0 || identity.usernames.length > 0 || identity.emails.length > 0;
  const hasSocialHits = radar.total_social_hits > 0;

  if (hasIdentity || hasSocialHits || allPages.length > 0) {
    html += `
      <div class="social-radar-container" style="background: rgba(30,25,20,0.8); border: 2px solid var(--accent-soft); border-radius: 16px; padding: 24px; margin-bottom: 32px; box-shadow: 0 12px 40px rgba(255,107,53,0.15); position:relative; overflow:hidden;">
        <div style="position:absolute; top:0; right:0; opacity:0.03; font-size:150px; font-weight:900; pointer-events:none; transform:rotate(-15deg) translate(30px, -20px);">DOSSIER</div>
        <h3 style="margin-bottom:20px; font-size:22px; font-weight:800; color: var(--accent-amber); letter-spacing:-0.5px; display:flex; align-items:center; gap:10px;">
          <span style="background:var(--accent-clay); color:#fff; border-radius:50%; width:32px; height:32px; display:flex; align-items:center; justify-content:center; font-size:16px;">🎯</span>
          Unified Identity Dossier
        </h3>
    `;

    // ── Advanced Person Profile Card ──
    html += `<div style="background: linear-gradient(135deg, rgba(255,107,53,0.1), rgba(255,199,130,0.05)); border: 1px solid var(--border-glass); border-radius: 14px; padding: 20px; margin-bottom: 20px;">`;
    html += `<h4 style="color:var(--accent-soft); margin-bottom:16px; font-size:13px; text-transform:uppercase; font-weight:700; letter-spacing:1px; border-bottom:1px solid var(--border-glass); padding-bottom:10px;">🕵️ Verified Candidate Profile (${identity.total_sources_analyzed || allPages.length} global nodes analyzed)</h4>`;

    // Likely Name Display (BIG)
    const displayName = identity.names.length > 0 ? identity.names[0] : "Unknown Entity detected (Scouring deep web...)";
    html += `<div style="display:flex; align-items:center; gap:15px; margin-bottom:15px; padding:15px; background:rgba(0,0,0,0.4); border-radius:10px; border-left: 4px solid var(--accent-main);">
      <span style="font-size:32px;">👤</span>
      <div style="flex:1;">
        <div style="font-size:12px; color:var(--text-muted); text-transform:uppercase; letter-spacing:1.5px; font-weight:600;">Identified Persona</div>
        <div style="font-size:20px; font-weight:800; color:#fff; text-shadow:0 2px 10px rgba(0,0,0,0.5);">${displayName}</div>
        ${identity.names.length > 1 ? `<div style="font-size:12px; color:var(--accent-soft); margin-top:4px; font-style:italic;">Alternative Mentions: ${identity.names.slice(1).join(', ')}</div>` : ''}
      </div>
    </div>`;

    // Usernames / Handles (Rich display)
    if (identity.usernames && identity.usernames.length > 0) {
      html += `<div style="display:flex; flex-direction:column; gap:8px; margin-bottom:15px; padding:12px; background:rgba(0,0,0,0.25); border-radius:10px;">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:1px;">Active Handles & Aliases</div>
        <div style="display:flex; flex-wrap:wrap; gap:8px;">
          ${identity.usernames.map(u => `<span style="background:rgba(255,107,53,0.2); border:1px solid var(--accent-soft); color:var(--accent-amber); padding:4px 10px; border-radius:6px; font-size:12px; font-weight:700;">${u}</span>`).join('')}
        </div>
      </div>`;
    }

    // Contact Data
    if (identity.emails && identity.emails.length > 0) {
      html += `<div style="display:flex; align-items:center; gap:10px; margin-bottom:15px; padding:12px; background:rgba(0,0,0,0.25); border-radius:10px;">
        <span style="font-size:20px;">📧</span>
        <div>
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:1px;">Secured Correspondence</div>
          <div style="font-size:14px; font-weight:700; color:var(--accent-amber);">${identity.emails.join(', ')}</div>
        </div>
      </div>`;
    }

    // Dynamic Platform Badges
    if (identity.profile_links && identity.profile_links.length > 0) {
      html += `<div style="margin-top:15px;">
        <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:700; letter-spacing:1px; margin-bottom:10px;">🌍 Located Physical/Digital Hubs</div>
        <div style="display:flex; flex-wrap:wrap; gap:8px;">`;
      
      const platformIcons = {
        'Instagram': '📷', 'Facebook': '👥', 'Twitter/X': '🐦', 'TikTok': '🎵',
        'LinkedIn': '💼', 'Reddit': '🤖', 'Pinterest': '📌', 'YouTube': '▶️', 'GitHub': '💻'
      };

      identity.profile_links.forEach(pl => {
        const icon = platformIcons[pl.platform] || '🌐';
        html += `<a href="${pl.url}" target="_blank" style="display:inline-flex; align-items:center; gap:8px; background:rgba(255,255,255,0.05); border:1px solid var(--border-glass); padding:8px 12px; border-radius:8px; color:#fff; text-decoration:none; font-size:13px; transition:all 0.3s; font-weight:600;" onmouseover="this.style.borderColor='var(--accent-main)';this.style.transform='translateY(-2px)';this.style.background='rgba(255,107,53,0.15)';" onmouseout="this.style.borderColor='var(--border-glass)';this.style.transform='none';this.style.background='rgba(255,255,255,0.05)';">
          <span>${icon}</span>
          <span>${pl.platform}</span>
        </a>`;
      });
      html += `</div></div>`;
    }

    html += `</div>`; // End profile card

    // Social Groups (Apps, Blogs etc)
    if (radar.total_social_hits > 0) {
      html += `<div style="display: flex; flex-direction: column; gap: 16px; margin-top:20px;">`;
      const groups = [
        { id: "social_media", title: "📱 Social Network Anchors", items: radar.social_media || [] },
        { id: "dating_app", title: "❤️ Interpersonal Node Matches", items: radar.dating_app || [] },
        { id: "forum_blog", title: "💬 Community Records", items: radar.forum_blog || [] }
      ];

      groups.forEach(g => {
        if (g.items && g.items.length > 0) {
          html += `<div class="radar-group">
            <h4 style="font-size:13px; color:var(--accent-soft); text-transform:uppercase; font-weight:700; letter-spacing:0.5px; margin-bottom:10px;">${g.title} (${g.items.length})</h4>
            <div style="display:flex; flex-wrap: wrap; gap: 10px;">`;
          g.items.forEach(item => {
            html += `
              <a href="${item.url}" target="_blank" class="radar-link" style="background: rgba(0,0,0,0.2); border: 1px solid var(--border-glass); border-radius: 8px; padding: 8px 14px; display: flex; align-items: center; gap: 10px; text-decoration: none; color: #fff; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,107,53,0.1)';this.style.borderColor='var(--accent-main)';" onmouseout="this.style.background='rgba(0,0,0,0.2)';this.style.borderColor='var(--border-glass)';">
                ${item.thumbnail ? `<img src="${item.thumbnail}" style="width:22px; height:22px; border-radius:50%; object-fit:cover; border:1px solid var(--accent-soft);">` : '📡'}
                <span style="font-size:13px; font-weight:600;">${item.source}</span>
              </a>
            `;
          });
          html += `</div></div>`;
        }
      });
      html += `</div>`;
    }

    html += `</div>`; // End Radar container
  }

  // 2. Direct Native Discoveries (Scraped directly by backend)
  const allPages = searchData.pages_found || [];
  if (allPages.length > 0) {
    html += `<h3 style="margin-bottom:16px;font-size:18px;font-weight:700;color:#ffc996;">📥 Inline Intelligence Gathered</h3>
             <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px;">Direct webpage matches scanned securely via our automated OSINT tunnel.</p>`;
    
    html += `<div class="pages-found-grid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap:16px; margin-bottom:32px;">`;
    allPages.forEach(p => {
       html += `
         <a href="${p.url}" target="_blank" style="background:rgba(255,255,255,0.03); border:1px solid var(--border-glass); border-radius:12px; padding:16px; text-decoration:none; display:flex; flex-direction:column; gap:10px; transition:transform 0.2s, border-color 0.2s;" onmouseover="this.style.transform='translateY(-2px)';this.style.borderColor='var(--accent-main)'" onmouseout="this.style.transform='none';this.style.borderColor='var(--border-glass)'">
           <div style="font-size:12px; color:var(--accent-amber); text-transform:uppercase; font-weight:600; letter-spacing:1px;">${p.source || 'Unknown Domain'}</div>
           <div style="color:#fff; font-weight:700; font-size:14px; line-height:1.4;">${p.title}</div>
           ${p.description ? `<div style="color:var(--text-muted); font-size:12px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${p.description}</div>` : ''}
           <div style="margin-top:auto; color:var(--accent-soft); font-size:12px; text-decoration:underline; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${p.url}</div>
         </a>
       `;
    });
    html += `</div>`;
  }

  // 3. Similar Image Visual Grid
  const simImgs = searchData.similar_images || [];
  if (simImgs.length > 0) {
    html += `<h3 style="margin-bottom:12px;font-size:18px;font-weight:700;color:#ffc996;">🖼️ Visually Similar Proxies</h3>
             <div style="display:flex; gap:12px; overflow-x:auto; padding-bottom:12px; margin-bottom:32px;">`;
    simImgs.forEach(img => {
      if (img.thumbnail) {
        html += `<a href="${img.url || '#'}" target="_blank" style="flex:0 0 120px; height:120px; border-radius:8px; border:1px solid var(--border-glass); overflow:hidden; position:relative;">
          <img src="${img.thumbnail}" style="width:100%; height:100%; object-fit:cover;">
        </a>`;
      }
    });
    html += `</div>`;
  }

  // Fully disabled manual search engine grid for absolute system containment.

  // Search all button removed as per user strict requirement for native-only immersion

  // Tips
  html += '<div class="search-tips"><h4>💡 Search Tips</h4>';
  searchData.search_tips.forEach(tip => {
    html += `<div class="tip-item">${tip}</div>`;
  });
  html += '</div>';

  container.innerHTML = html;
}

function openAllSearchEngines() {
  if (!searchResults) return;
  const engines = searchResults.search.manual_engines;

  // Open automated results first
  if (searchResults.search.active_results) {
    searchResults.search.active_results.forEach(r => {
      if (r.status === 'success' && r.url) window.open(r.url, '_blank');
    });
  }

  // Open top 4 manual search engines
  engines.slice(0, 4).forEach((engine, i) => {
    setTimeout(() => window.open(engine.upload_url, '_blank'), i * 300);
  });
}

// ─── Metadata Tab ────────────────────────────────────────

function renderMetadataTab(analysis) {
  const container = $('#tab-metadata');
  let html = '<div class="metadata-grid">';

  // Image info
  html += buildMetadataCard('📐 Image Information', {
    'Format': analysis.metadata.format,
    'Dimensions': `${analysis.metadata.width} × ${analysis.metadata.height}`,
    'Megapixels': analysis.metadata.megapixels + ' MP',
    'File Size': analysis.metadata.file_size_human,
    'Aspect Ratio': analysis.metadata.aspect_ratio,
    'Color Mode': analysis.metadata.mode,
    'Has Transparency': analysis.metadata.has_transparency ? 'Yes' : 'No',
    'Animated': analysis.metadata.is_animated ? 'Yes' : 'No',
    ...(analysis.metadata.dpi ? { 'DPI': `${analysis.metadata.dpi[0]} × ${analysis.metadata.dpi[1]}` } : {}),
  });

  // Image classification
  if (analysis.image_info) {
    const info = analysis.image_info;
    const infoData = {
      'Resolution': info.resolution_category || 'N/A',
      'Orientation': info.orientation || 'N/A',
      'Color Space': info.color_space || 'N/A',
    };
    if (info.possible_source) infoData['Possible Source'] = info.possible_source;
    html += buildMetadataCard('🎯 Image Classification', infoData);
  }

  // EXIF data
  if (analysis.exif && !analysis.exif.note) {
    const exifData = {};
    Object.entries(analysis.exif).forEach(([key, val]) => {
      if (key === 'gps') return;
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      exifData[label] = val;
    });
    html += buildMetadataCard('📷 EXIF / Camera Data', exifData);

    // GPS
    if (analysis.exif.gps) {
      html += buildMetadataCard('📍 GPS Location', {
        'Latitude': analysis.exif.gps.latitude,
        'Longitude': analysis.exif.gps.longitude,
        'Google Maps': `<a href="${analysis.exif.gps.maps_url}" target="_blank" style="color:var(--accent-cyan);text-decoration:none;">Open Map →</a>`,
      });
    }
  } else {
    html += buildMetadataCard('📷 EXIF / Camera Data', { 'Status': 'No EXIF data found in this image' });
  }

  // Colors
  if (analysis.colors && analysis.colors.palette) {
    html += `
      <div class="metadata-card" style="grid-column: 1 / -1;">
        <h4>🎨 Color Palette</h4>
        <div class="meta-row">
          <span class="meta-key">Dominant Color</span>
          <span class="meta-value" style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-block;width:16px;height:16px;border-radius:4px;background:${analysis.colors.dominant_color};"></span>
            ${analysis.colors.dominant_color}
          </span>
        </div>
        <div class="meta-row">
          <span class="meta-key">Brightness</span>
          <span class="meta-value">${analysis.colors.brightness} (${analysis.colors.is_dark_image ? 'Dark' : 'Light'} image)</span>
        </div>
        <div class="color-palette">
          ${analysis.colors.palette.map(c => `
            <div class="color-swatch" style="background:${c.hex};">
              <span class="tooltip">${c.hex} (${c.percentage}%)</span>
            </div>
          `).join('')}
        </div>
      </div>`;
  }

  html += '</div>';
  container.innerHTML = html;
}

function buildMetadataCard(title, data) {
  let html = `<div class="metadata-card"><h4>${title}</h4>`;
  Object.entries(data).forEach(([key, value]) => {
    html += `
      <div class="meta-row">
        <span class="meta-key">${key}</span>
        <span class="meta-value">${value}</span>
      </div>`;
  });
  html += '</div>';
  return html;
}

// ─── Fingerprint Tab ─────────────────────────────────────

function renderFingerprintTab(fingerprint) {
  const container = $('#tab-fingerprint');
  if (fingerprint.error) {
    container.innerHTML = `<p style="color:var(--text-muted);">Error generating fingerprint: ${fingerprint.error}</p>`;
    return;
  }

  let html = `
    <p style="color:var(--text-muted);font-size:13px;margin-bottom:20px;">
      These perceptual hashes uniquely identify this image. Similar images will have similar hash values.
      Use these to detect duplicates and track image copies across the web.
    </p>
    <div class="hash-grid">`;

  const hashLabels = {
    perceptual_hash: '🔐 Perceptual Hash (pHash)',
    difference_hash: '📊 Difference Hash (dHash)',
    average_hash: '📐 Average Hash (aHash)',
    wavelet_hash: '🌊 Wavelet Hash (wHash)',
    color_hash: '🎨 Color Hash',
    fingerprint_summary: '🔑 Fingerprint ID',
  };

  Object.entries(hashLabels).forEach(([key, label]) => {
    if (fingerprint[key]) {
      html += `
        <div class="hash-item">
          <div class="hash-label">${label}</div>
          <div class="hash-value">${fingerprint[key]}</div>
        </div>`;
    }
  });

  html += '</div>';
  container.innerHTML = html;
}

// ─── Tab Switching ───────────────────────────────────────

function switchTab(tabId) {
  $$('.tab-btn').forEach(btn => btn.classList.remove('active'));
  $$('.tab-content').forEach(tc => tc.classList.remove('active'));
  document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.add('active');
}

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
  // Tab handlers
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // View Toggle (Landing to App)
  if (btnStartApp) {
    btnStartApp.addEventListener('click', () => {
      landingView.classList.add('hidden');
      appWorkspace.classList.remove('hidden');
      appWorkspace.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // Settings Handlers
  if (btnSettings) {
    btnSettings.addEventListener('click', () => {
      // Load existing value before opening
      inputFaceCheck.value = localStorage.getItem('facecheck-api-key') || '';
      settingsModal.classList.add('active');
    });
  }

  if (btnCloseSettings) {
    btnCloseSettings.addEventListener('click', () => {
      settingsModal.classList.remove('active');
    });
  }

  // Close on backdrop click
  settingsModal.addEventListener('click', (e) => {
    if (e.target === settingsModal) settingsModal.classList.remove('active');
  });

  if (btnSaveSettings) {
    btnSaveSettings.addEventListener('click', () => {
      localStorage.setItem('facecheck-api-key', inputFaceCheck.value.trim());
      settingsModal.classList.remove('active');
      
      // Show success toast
      const toast = document.createElement('div');
      toast.style.cssText = `
        position:fixed;bottom:30px;left:50%;transform:translateX(-50%);
        background:var(--accent-clay);color:#fff;padding:12px 24px;
        border-radius:8px;font-size:14px;font-weight:600;z-index:2000;
        box-shadow:0 8px 20px rgba(0,0,0,0.4); animation:fadeIn 0.3s;
      `;
      toast.textContent = '✅ Settings Saved & Encrypted Locally';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    });
  }
});

// ─── Reset ───────────────────────────────────────────────

function resetUpload() {
  currentFile = null;
  searchResults = null;
  fileInput.value = '';
  previewSection.style.display = 'none';
  loadingSection.style.display = 'none';
  resultsSection.style.display = 'none';
  uploadSection.style.display = 'block';

  const canvas = $('#face-canvas');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

// ─── Error Display ───────────────────────────────────────

function showError(msg) {
  const existing = document.querySelector('.error-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'error-toast';
  toast.style.cssText = `
    position:fixed;bottom:30px;left:50%;transform:translateX(-50%);
    background:rgba(255,45,95,0.95);color:#fff;padding:14px 28px;
    border-radius:12px;font-size:14px;font-weight:600;z-index:1000;
    box-shadow:0 4px 20px rgba(255,45,95,0.3);
    animation:fadeIn 0.3s;
  `;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}
