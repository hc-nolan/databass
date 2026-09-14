function handleDeleteButton(deleteButton) {
    let itemId = deleteButton.getAttribute('data-id');
    let itemType = deleteButton.getAttribute('data-type');
    const popup = document.createElement('div');
    popup.className = 'popup';
    popup.id = 'delete_popup';
    popup.innerHTML = `
    <h1>Are you sure?&nbsp;This cannot be undone.</h1>
    <div>
    <button id="confirm" class="delete pure-button">delete</button>
    <button id="cancel" class="delete pure-button">cancel</button>
    </div>
    `;
    document.body.appendChild(popup);
    // If 'yes' button is pressed, delete the release
    popup.querySelector('#confirm').addEventListener('click', function() {
        fetch('/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id: itemId, type: itemType })
        })
        .then(response => {
            window.location.href = response.url;
        })
    });
    popup.querySelector('#cancel').addEventListener('click', function() {
        document.body.removeChild(popup);
    });
}

function handleEditButton(editButton) {
    let releaseId = editButton.getAttribute('data-id');
    fetch('/release/' + releaseId + '/edit')
        .then(response => response.text())
        .then(html => {
            let popup = document.createElement('div');
            popup.id = 'edit_popup';
            popup.className = 'popup';
            popup.innerHTML = html;
            document.body.appendChild(popup);

            popup.querySelector('#edit_cancel').addEventListener('click', () => {
                document.body.removeChild(popup);
            });
        })
}

function loadHomeTable(page, append) {
    fetch('/home_release_table?page=' + page)
        .then(response => response.text())
        .then(html => {
            const container = document.getElementById('home_release_table');
            if (append) {
                container.insertAdjacentHTML('beforeend', html);
            } else {
                container.innerHTML = html;
            }
            const hasNext = document.getElementById('home-has-next');
            const loadMoreBtn = document.getElementById('load-earlier');
            if (loadMoreBtn) {
                loadMoreBtn.style.display = (hasNext && hasNext.value === '1') ? '' : 'none';
            }
        });
}

function initNewListenPage() {
    const releaseInput = document.querySelector('#release');
    const artistInput = document.querySelector('#artist');
    const labelInput = document.querySelector('#label');
    const searchBtn = document.querySelector('#search-btn');
    const manualToggle = document.querySelector('#manual-entry-toggle');
    const resultsContainer = document.querySelector('#search_results');
    const logForm = document.querySelector('#log-form');
    const logEmpty = document.querySelector('#log-panel-empty');
    const listenDateInput = document.querySelector('#lf-listen-date');
    const defaultListenDate = listenDateInput.value;
    const ratingWords = ["", "actively bad", "didn't work", "flat", "thin", "fine", "solid", "really good", "excellent", "near-perfect", "all-timer"];
    let subgenres = [];

    function runSearch() {
        const release = releaseInput.value.trim();
        const artist = artistInput.value.trim();
        const label = labelInput.value.trim();
        if (!release && !artist && !label) return;
        searchBtn.disabled = true;
        searchBtn.textContent = 'SEARCHING…';
        resultsContainer.innerHTML = '<div class="new-search__loading"><span class="spinner"></span>searching MusicBrainz…</div>';
        fetch('/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                release: release || null,
                artist: artist || null,
                label: label || null,
            }),
        })
            .then(response => response.text())
            .then(html => { resultsContainer.innerHTML = html; wireResultFilters(); })
            .catch(err => {
                console.error('Search failed:', err);
                resultsContainer.innerHTML = '<div class="new-search__loading">search failed, try again</div>';
            })
            .finally(() => {
                searchBtn.disabled = false;
                searchBtn.textContent = 'SEARCH';
            });
    }

    function loadManualEntry() {
        fetch('/search', { method: 'GET' })
            .then(response => response.text())
            .then(html => { resultsContainer.innerHTML = html; })
            .catch(err => console.error('Manual entry load failed:', err));
    }

    function wireResultFilters() {
        const titleInput = document.querySelector('#rf-title');
        const artistSelect = document.querySelector('#rf-artist');
        const yearSelect = document.querySelector('#rf-year');
        const formatSelect = document.querySelector('#rf-format');
        const countrySelect = document.querySelector('#rf-country');
        if (!titleInput) return;

        const rows = Array.from(document.querySelectorAll('#new-results-items .result-row'));
        const countLabel = document.querySelector('#new-results-count');
        const emptyMsg = document.querySelector('#new-results-empty');

        function applyFilters() {
            const title = titleInput.value.trim().toLowerCase();
            const artist = artistSelect.value;
            const year = yearSelect.value;
            const format = formatSelect.value;
            const country = countrySelect.value;

            let visibleCount = 0;
            rows.forEach(row => {
                let item;
                try {
                    item = JSON.parse(row.dataset.item);
                } catch (e) {
                    return;
                }
                const matches =
                    (!title || (item.release.name || '').toLowerCase().includes(title)) &&
                    (!artist || item.artist.name === artist) &&
                    (!year || String(item.date) === year) &&
                    (!format || item.format === format) &&
                    (!country || item.country === country);
                row.hidden = !matches;
                if (matches) visibleCount++;
            });

            if (countLabel) countLabel.textContent = visibleCount + ' result' + (visibleCount !== 1 ? 's' : '');
            if (emptyMsg) emptyMsg.hidden = visibleCount !== 0;
        }

        titleInput.addEventListener('input', applyFilters);
        [artistSelect, yearSelect, formatSelect, countrySelect].forEach(select => {
            select.addEventListener('change', applyFilters);
        });
    }

    function updateRatingUI(rating) {
        document.querySelectorAll('#lf-rating-segmented .segmented__item').forEach(btn => {
            btn.classList.toggle('is-active', parseInt(btn.dataset.rating, 10) <= rating);
        });
        document.querySelector('#lf-rating').value = rating * 10;
        document.querySelector('#lf-rating-label').textContent = rating.toFixed(1) + ' / 10';
        document.querySelector('#lf-rating-hint').textContent =
            ratingWords[rating] + ' · stored as ' + (rating * 10) + '%';
    }

    function syncGenreSuggestions() {
        document.querySelectorAll('#lf-genre-suggestions [data-genre-suggestion]').forEach(chip => {
            chip.classList.toggle('is-selected', subgenres.includes(chip.dataset.genreSuggestion));
        });
    }

    function renderSubgenreChips() {
        const container = document.querySelector('#lf-subgenre-chips');
        container.innerHTML = '';
        subgenres.forEach(name => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'chip is-selected';
            chip.textContent = name + ' ×';
            chip.addEventListener('click', () => {
                subgenres = subgenres.filter(g => g !== name);
                syncGenreSuggestions();
                renderSubgenreChips();
            });
            container.appendChild(chip);
        });
        document.querySelector('#lf-genres').value = subgenres.join(',');
    }

    function addSubgenre(name) {
        name = name.trim();
        if (!name || subgenres.includes(name)) return;
        subgenres.push(name);
        syncGenreSuggestions();
        renderSubgenreChips();
    }

    function selectResult(row) {
        let item;
        try {
            item = JSON.parse(row.dataset.item);
        } catch (e) {
            console.error('Failed to parse result data', e);
            return;
        }
        document.querySelectorAll('.result-row').forEach(r => r.classList.remove('is-selected'));
        row.classList.add('is-selected');

        document.querySelector('#lf-release_group_id').value = item.release_group_id || '';
        document.querySelector('#lf-release_name').value = item.release.name || '';
        document.querySelector('#lf-artist').value = item.artist.name || '';
        document.querySelector('#lf-label').value = item.label.name || '';
        document.querySelector('#lf-release_mbid').value = item.release.mbid || '';
        document.querySelector('#lf-artist_mbid').value = item.artist.mbid || '';
        document.querySelector('#lf-label_mbid').value = item.label.mbid || '';
        document.querySelector('#lf-track_count').value = item.track_count || 0;
        document.querySelector('#lf-country').value = item.country || '';
        document.querySelector('#lf-year').value = item.date || 0;

        document.querySelector('#lf-title-display').textContent = item.release.name || '';
        document.querySelector('#lf-artist-display').textContent = item.artist.name || '';
        document.querySelector('#lf-subline-display').textContent =
            [item.label.name, item.date, item.format, item.country].filter(Boolean).join(' · ');
        document.querySelector('#lf-tracks-display').value = item.track_count || '';

        logEmpty.hidden = true;
        logForm.hidden = false;
        document.querySelector('#lf-main-genre').focus();
    }

    searchBtn.addEventListener('click', runSearch);
    [releaseInput, artistInput, labelInput].forEach(input => {
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                runSearch();
            }
        });
    });
    manualToggle.addEventListener('click', loadManualEntry);

    resultsContainer.addEventListener('click', e => {
        const row = e.target.closest('.result-row');
        if (row) selectResult(row);
    });
    resultsContainer.addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        const row = e.target.closest('.result-row');
        if (row) selectResult(row);
    });

    document.querySelector('#lf-rating-segmented').addEventListener('click', e => {
        const btn = e.target.closest('[data-rating]');
        if (btn) updateRatingUI(parseInt(btn.dataset.rating, 10));
    });

    document.querySelector('#lf-genre-suggestions').addEventListener('click', e => {
        const chip = e.target.closest('[data-genre-suggestion]');
        if (!chip) return;
        const name = chip.dataset.genreSuggestion;
        if (subgenres.includes(name)) {
            subgenres = subgenres.filter(g => g !== name);
        } else {
            subgenres.push(name);
        }
        syncGenreSuggestions();
        renderSubgenreChips();
    });

    document.querySelector('#lf-subgenre-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addSubgenre(e.target.value);
            e.target.value = '';
        }
    });

    document.querySelector('#lf-clear').addEventListener('click', () => {
        updateRatingUI(7);
        subgenres = [];
        syncGenreSuggestions();
        renderSubgenreChips();
        document.querySelector('#lf-note').value = '';
        listenDateInput.value = defaultListenDate;
    });

    updateRatingUI(7);

    const initialQuery = document.querySelector('#new-q');
    if (initialQuery && initialQuery.value) {
        releaseInput.value = initialQuery.value;
        runSearch();
    }
}

function initBrowsePage() {
    const page = document.querySelector('#browse_page');
    const tab = page.dataset.tab;
    const resultsContainer = document.querySelector('#browse-results');
    const qInput = document.querySelector('#browse-q');
    const countryFacet = document.querySelector('#browse-country');
    const genreFacet = document.querySelector('#browse-genre');
    const yearFacet = document.querySelector('#browse-year-min');
    const typeFacet = document.querySelector('#browse-type');
    const releasesFacet = document.querySelector('#browse-releases-min');
    const ratingFacet = document.querySelector('#browse-rating-min');
    const sortBtns = Array.from(document.querySelectorAll('.browse-sort'));
    const viewBtns = Array.from(document.querySelectorAll('.browse-view-btn'));

    let sort = sortBtns.length ? sortBtns[0].dataset.sort : 'listened';
    let debounceTimer;

    function currentParams(page) {
        const params = new URLSearchParams();
        if (qInput.value.trim()) params.set('q', qInput.value.trim());
        if (countryFacet && countryFacet.value) params.set('country', countryFacet.value);
        if (genreFacet && genreFacet.value) params.set('genre', genreFacet.value);
        if (yearFacet && yearFacet.value) params.set('year_min', yearFacet.value);
        if (typeFacet && typeFacet.value) params.set('type', typeFacet.value);
        if (releasesFacet && releasesFacet.value) params.set('releases_min', releasesFacet.value);
        if (ratingFacet && ratingFacet.value) params.set('rating_min', ratingFacet.value);
        params.set('sort', sort);
        params.set('page', page);
        return params;
    }

    function loadResults(page) {
        const params = currentParams(page);
        fetch('/browse/' + tab + '/results?' + params.toString())
            .then(response => response.text())
            .then(html => { resultsContainer.innerHTML = html; })
            .catch(err => console.error('Browse results failed:', err));
    }

    qInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => loadResults(1), 300);
    });

    [countryFacet, genreFacet, yearFacet, typeFacet, releasesFacet, ratingFacet].forEach(el => {
        if (el) el.addEventListener('change', () => loadResults(1));
    });

    sortBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            sortBtns.forEach(b => b.classList.remove('is-active'));
            btn.classList.add('is-active');
            sort = btn.dataset.sort;
            loadResults(1);
        });
    });

    viewBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            viewBtns.forEach(b => b.classList.remove('is-active'));
            btn.classList.add('is-active');
            resultsContainer.classList.toggle('is-list', btn.dataset.view === 'list');
        });
    });

    resultsContainer.addEventListener('click', e => {
        const btn = e.target.closest('.browse-page-btn');
        if (!btn || btn.disabled) return;
        e.preventDefault();
        loadResults(parseInt(btn.dataset.page, 10));
    });

    loadResults(1);
}

function initStatsPage() {
    const periodBtns = Array.from(document.querySelectorAll('#stats-periods .segmented__item'));
    const periodContent = document.querySelector('#stats-period-content');
    const scopeBtns = Array.from(document.querySelectorAll('#stats-scope .segmented__item'));
    const leaderboards = document.querySelector('#stats_data');

    periodBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            periodBtns.forEach(b => b.classList.remove('is-active'));
            btn.classList.add('is-active');
            fetch('/stats/period/' + btn.dataset.period)
                .then(response => response.text())
                .then(html => { periodContent.innerHTML = html; })
                .catch(err => console.error('Stats period failed:', err));
        });
    });

    function loadLeaderboards(scope) {
        fetch('/stats/get/' + scope)
            .then(response => response.text())
            .then(html => { leaderboards.innerHTML = html; })
            .catch(err => console.error('Stats leaderboards failed:', err));
    }

    scopeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            scopeBtns.forEach(b => b.classList.remove('is-active', 'is-active--alt'));
            btn.classList.add('is-active', 'is-active--alt');
            loadLeaderboards(btn.id);
        });
    });

    loadLeaderboards('artists');
}

function initGoalsPage() {
    const section = document.querySelector('#goal-form-section');
    if (!section) return;

    const currentPace = parseFloat(section.dataset.currentPace) || 0;
    const today = section.dataset.today;
    const amountInput = document.querySelector('#goal-amount');
    const endInput = document.querySelector('#goal-end');
    const typeInput = document.querySelector('#goal-type');
    const typeBtns = Array.from(document.querySelectorAll('#goal-type-segmented .segmented__item'));
    const feasRate = document.querySelector('#goal-feas-rate');
    const feasText = document.querySelector('#goal-feas-text');
    const feasBox = document.querySelector('#goal-feasibility');

    const MSPERDAY = 86400000;

    function recompute() {
        const amount = parseInt(amountInput.value, 10) || 0;
        const endMs = Date.parse(endInput.value);
        const todayMs = Date.parse(today);
        if (Number.isNaN(endMs)) return;

        const formDays = Math.max(1, Math.round((endMs - todayMs) / MSPERDAY));
        const rate = amount / formDays;
        feasRate.textContent = rate.toFixed(2) + ' / day';

        if (currentPace <= 0) {
            feasBox.style.borderColor = 'var(--border)';
            feasRate.style.color = 'var(--ink)';
            feasText.textContent = 'Log a few releases to get a feasibility estimate based on your pace.';
            return;
        }

        const ratio = rate / currentPace;
        let color, borderColor, text;
        if (ratio <= 0.85) {
            color = 'var(--cyan)';
            borderColor = 'var(--cyan)';
            const hitDate = new Date(todayMs + (amount / currentPace) * MSPERDAY);
            text = 'Comfortable. That\'s below your ' + currentPace.toFixed(2) + ' / day average — you\'d hit it around ' +
                hitDate.toISOString().slice(0, 10) + ' at your current pace.';
        } else if (ratio <= 1.25) {
            color = 'var(--amber)';
            borderColor = 'var(--amber)';
            text = 'Realistic. Roughly your current pace of ' + currentPace.toFixed(2) + ' / day, sustained for ' + formDays + ' days.';
        } else {
            color = 'var(--red)';
            borderColor = 'var(--red)';
            text = 'Ambitious. That\'s ' + ratio.toFixed(1) + '× your current pace — you\'d need to log ' +
                Math.ceil(rate - currentPace) + ' more per day than you do now.';
        }
        feasBox.style.borderColor = borderColor;
        feasRate.style.color = color;
        feasText.textContent = text;
    }

    amountInput.addEventListener('input', recompute);
    endInput.addEventListener('change', recompute);

    typeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            typeBtns.forEach(b => b.classList.remove('is-active'));
            btn.classList.add('is-active');
            typeInput.value = btn.dataset.value;
        });
    });

    document.querySelectorAll('.goal-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            amountInput.value = btn.dataset.amount;
            endInput.value = btn.dataset.end;
            recompute();
        });
    });

    recompute();
}

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname === "/" || window.location.pathname === "/home") {
        loadHomeTable(1, false);
        const loadMoreBtn = document.getElementById('load-earlier');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', function() {
                const pageField = document.getElementById('home-page');
                const currentPage = pageField ? parseInt(pageField.value, 10) || 1 : 1;
                loadHomeTable(currentPage + 1, true);
            });
        }
    }

    if (window.location.pathname === "/new") {
        initNewListenPage();
    }

    if (window.location.pathname.startsWith("/browse")) {
        initBrowsePage();
    }

    if (window.location.pathname === "/stats") {
        initStatsPage();
    }

    if (window.location.pathname === "/goals") {
        initGoalsPage();
    }

    document.addEventListener('click', function(event) {
        if (event.target && event.target.classList.contains('delete-btn')) {
            let deleteBtn = document.querySelector("#delete-btn");
            handleDeleteButton(deleteBtn);
        }

        if (event.target && event.target.id === 'edit-btn') {
            let editButton = document.querySelector('#edit-btn');
            if (window.location.pathname.startsWith('/artist')) {
                editEntity(editButton, 'artist');
            }
            if (window.location.pathname.startsWith('/release')) {
                editEntity(editButton, 'release');
            }
            if (window.location.pathname.startsWith('/label')) {
                editEntity(editButton, 'label');
            }
        }

    });
});

function editEntity(editButton, entityType) {
    let entityId = editButton.getAttribute('data-id');
    fetch('/' + entityType + '/' + entityId + '/edit')
        .then(response => response.text())
        .then(html => {
            let popup = document.createElement('div');
            popup.id = 'edit_popup';
            popup.className = 'popup';
            popup.innerHTML = html;
            document.body.appendChild(popup);

            popup.querySelector('#edit_cancel').addEventListener('click', () => {
                document.body.removeChild(popup);
            });
        })
}


