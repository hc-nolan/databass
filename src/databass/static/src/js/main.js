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

function formatDataString(data) {
    // Escape parts of response data that cause JSON.parse to error
    // Some of these are extremely case specific; ideally should be more generalized
    // i.e
    // .replace(/ "n/g, " 'n") = Drum "n' Bass -> Drum 'n' Bass
    // .replace(/ "n' /g, " 'n' ") = Neu! "75 -> Neu! '75
    // Both of the above cases are caused by the other more generic replacements
    // Way to avoid most of this altogether would be to just URLencode key/value pairs
    return data
        .replace(/None/g, 'null')
        .replace(/{'/g, '{"')
        .replace(/'}/g, '"}')
        .replace(/':/g, '":')
        .replace(/ '/g, ' "')
        .replace(/',/g, '",')
        .replace(/ "n' /g, " 'n' ")
        .replace(/\['/g, '\["')
        .replace(/'\]/g, '"\]')
        .replace(/! "75/g, "! '75'")
        .replace(/(12|10|7)" Vinyl/g, '$1\\" Vinyl');
}

function addPopupListeners(html) {
    document.getElementById("search_results").innerHTML = html;
    let tableRows = document.querySelectorAll(".row");
    tableRows.forEach((tableRow) => {
        tableRow.addEventListener("click", function() {
            let data = formatDataString(tableRow.dataset.item);
            let parsed_data = JSON.parse(data)
            fetch("/new_release", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(parsed_data)
            })
                .then(response => response.text())
                .then(html => {
                    let popup = document.createElement('div')
                    popup.className = 'popup';
                    popup.innerHTML = html;
                    document.body.appendChild(popup);
                    popup.querySelector('.close-btn').addEventListener('click', function() {
                        document.body.removeChild(popup);
                    });
                })
                .catch(err => { console.log(err) })
        });
    });
}

function handleSearchButton() {
    let page;
    try {
        page = document.querySelector('#current_page').value;
    } catch(e) {
        page = "1";
    }
    let referrer;
    try {
        referrer = document.querySelector("#referrer").value;
    } catch(e) {
        referrer = "search"
    }
    const data = {
        release: document.querySelector("#release").value,
        artist: document.querySelector("#artist").value,
        label: document.querySelector("#label").value,
        "referrer": referrer,
        "page": page
    };
    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.text())
    .then(html => {
        // add event listener to each table row
        addPopupListeners(html);
    })
    .catch(error => {
        console.error('Fetch error:', error);
    });
}

function loadSearchResults(direction) {
    let targetPage = getTargetPage(direction);
    let data = document.getElementById("data_full").innerHTML;
    let formattedData = formatDataString(data);
    let parsedData = JSON.parse(formattedData);
    fetch('/search_results?page=' + targetPage, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(parsedData)
    })
        .then(response => response.text())
        .then(html => {
            addPopupListeners(html);
            // document.getElementById('search_results').innerHTML = html;
        });
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

function loadHomeTable(direction) {
    let targetPage = getTargetPage(direction);
    fetch('/home_release_table?page=' + targetPage)
        .then(response => response.text())
        .then(html => {
            document.getElementById('home_release_table').innerHTML = html;
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

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname === "/" || window.location.pathname === "/home") {
        loadHomeTable();
        document.addEventListener('click', function(event) {
            if (event.target.classList.contains('prev_page')) {
                loadHomeTable('prev')
            }
            if (event.target.classList.contains('next_page')) {
                loadHomeTable('next')
            }
        });
    }

    if (window.location.pathname === "/new") {
        document.addEventListener('click', function(event) {
            if (event.target && event.target.classList.contains('manual_entry')) {
                event.preventDefault();
                fetch('/search', {
                    method: 'GET'
                })
                    .then(response => response.text())
                    .then(html => {
            document.getElementById('search_results').innerHTML = html;
                    })
                    .catch(error => {
                        console.error('Fetch error:', error);
                    });
            }
            if (event.target && event.target.classList.contains('new_search')) {
                handleSearchButton();
                document.addEventListener('click', function(event) {
                    if (event.target.classList.contains('prev_page')) {
                        loadSearchResults('prev')
                    }
                    if (event.target.classList.contains('next_page')) {
                        loadSearchResults('next')
                    }
                });
            }
        });
        document.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                handleSearchButton();
            }
        });
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


