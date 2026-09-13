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

function getTargetPage(direction) {
    let currentPage;
    try {
        currentPage = document.getElementById('current_page').value;
    } catch (e) {
        currentPage = "1";
    }
    let targetPage = currentPage;
    if (direction === 'prev') targetPage = parseInt(currentPage) - 1;
    if (direction === 'next') targetPage = parseInt(currentPage) + 1;
    return targetPage
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

function loadSearchTable(type, direction) {
    let formData;
    if (type === 'release') {
        formData = {
            name: document.querySelector("#name").value,
            artist: document.querySelector("#artist").value,
            label: document.querySelector("#label").value,
            country: document.querySelector("#country").value,
            rating_comparison: document.querySelector("#rating-filter").value,
            rating: document.querySelector("#rating").value,
            year_comparison: document.querySelector("#year-filter").value,
            year: document.querySelector("#year").value,
            main_genre: document.querySelector("#main_genre").value,
            // genres: [document.querySelector("#genres").value]
        };
        console.log(formData);
    }
    if (type === 'artist') {
        formData = {
            name: document.querySelector("#artist").value,
            country: document.querySelector("#country").value,
            begin_comparison: document.querySelector("#begin_filter").value,
            begin_date: document.querySelector("#begin").value,
            end_comparison: document.querySelector("#end_filter").value,
            end_date: document.querySelector("#end").value,
            type: document.querySelector("#type").value
        };
    }
    if (type === 'label') {
        formData = {
            name: document.querySelector("#label").value,
            country: document.querySelector("#country").value,
            begin_comparison: document.querySelector("#begin_filter").value,
            begin_date: document.querySelector("#begin").value,
            end_comparison: document.querySelector("#end_filter").value,
            end_date: document.querySelector("#end").value,
            type: document.querySelector("#type").value,
        }
    }
    let targetPage = getTargetPage(direction);
    fetch('/' + type + '_search?page=' + targetPage, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(formData)
    })
        .then(response => response.text())
        .then(html => {
            document.getElementById('search-results').innerHTML = html;
        })
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
            .then(html => { resultsContainer.innerHTML = html; })
            .catch(err => console.error('Search failed:', err));
    }

    function loadManualEntry() {
        fetch('/search', { method: 'GET' })
            .then(response => response.text())
            .then(html => { resultsContainer.innerHTML = html; })
            .catch(err => console.error('Manual entry load failed:', err));
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

    if (window.location.pathname === "/releases") {
        document.addEventListener('click', function (event) {
            if (event.target && event.target.id === 'release-search') {
                loadSearchTable('release');
            }
            if (event.target && event.target.classList.contains('pagination_button')) {
                if (event.target.classList.contains('prev_page')) {
                    loadSearchTable('release', 'prev')
                }
                if (event.target.classList.contains('next_page')) {
                    loadSearchTable('release', 'next')
                }
            }
        })
    }

    if (window.location.pathname === "/artists") {
        document.addEventListener('click', function (event) {
            if (event.target && event.target.id === 'artist-search') {
                loadSearchTable('artist');
            }
            if (event.target && event.target.classList.contains('pagination_button')) {
                if (event.target.classList.contains('prev_page')) {
                    loadSearchTable('artist', 'prev')
                }
                if (event.target.classList.contains('next_page')) {
                    loadSearchTable('artist', 'next')
                }
            }
        })
    }

    if (window.location.pathname === "/labels") {
        document.addEventListener('click', function (event) {
            if (event.target && event.target.id === 'label-search') {
                loadSearchTable('label');
            }
            if (event.target && event.target.classList.contains('pagination_button')) {
                if (event.target.classList.contains('prev_page')) {
                    loadSearchTable('label', 'prev')
                }
                if (event.target.classList.contains('next_page')) {
                    loadSearchTable('label', 'next')
                }
            }
        })
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


