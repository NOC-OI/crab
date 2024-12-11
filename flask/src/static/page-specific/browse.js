let userCache = {};
let sampleCache = {};

let currentPage = 0;
let currentXhr = null;

let getUserInfo = (uuid) => {
    return new Promise((resolve, reject) => {
        if (!userCache.hasOwnProperty(uuid)) {
            userCache[uuid] = new Promise((resolveInner, rejectInner) => {
                let xhr = new XMLHttpRequest();
                xhr.open("GET", "/api/v1/get_user/" + uuid);
                xhr.addEventListener('loadend', () => {
                    if (xhr.status === 200) {
                        response = JSON.parse(xhr.responseText);
                        resolveInner(response);
                    }
                });
                xhr.send();
            });
        }
        userCache[uuid].then((response) => {
            resolve(response);
        });
    });
}

let getSampleInfo = (uuid) => {
    return new Promise((resolve, reject) => {
        if (!sampleCache.hasOwnProperty(uuid)) {
            sampleCache[uuid] = new Promise((resolveInner, rejectInner) => {
                let xhr = new XMLHttpRequest();
                xhr.open("GET", "/api/v1/get_sample_metadata/" + uuid);
                xhr.addEventListener('loadend', () => {
                    if (xhr.status === 200) {
                        response = JSON.parse(xhr.responseText);
                        resolveInner(response);
                    }
                });
                xhr.send();
            });
        }
        sampleCache[uuid].then((response) => {
            resolve(response);
        });
    });
}

let base64URLencode = (str) => {
    let base64Encoded = btoa(str);
    return base64Encoded.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

let base64URLdecode = (str) => {
    let base64Encoded = str.replace(/-/g, "+").replace(/_/g, "/");
    let padding = str.length % 4 === 0 ? "" : "=".repeat(4 - (str.length % 4));
    let base64WithPadding = base64Encoded + padding;
    return atob(base64WithPadding);
}

let updateFragment = () => {
    let content = {
        "p": currentPage
    }
    window.location.hash = base64URLencode(JSON.stringify(content));
}

let fragmentMoveHandler = () => {
    let content = {}
    try {
        content = JSON.parse(base64URLdecode(window.location.hash.replace(/#/g, "")));
    } catch (e) {
        window.location.hash = "#"
    }
    if (content.hasOwnProperty("p")) {
        currentPage = content["p"]
    }
    if (currentPage < 0) {
        currentPage = 0
    }
    loadPage({}, {}, currentPage);
}

let loadPage = (selector = {}, sort = {}, page = 0) => {
    document.getElementById("list_view").innerHTML = "";
    document.getElementById("page_number_top").value = page + 1;
    document.getElementById("page_number_bottom").value = page + 1;
    if (currentXhr != null) {
        currentXhr.abort();
    }
    return new Promise((resolve, reject) => {
        currentXhr = new XMLHttpRequest();
        const data = new FormData();
        const spinnerContainer = document.getElementById("page_spinner");
        spinnerContainer.style.display = "";
        data.append("page", page);
        currentXhr.open("POST", "/api/v1/get_runs");
        currentXhr.addEventListener('loadend', () => {
            let listView = document.getElementById("list_view");
            listView.innerHTML = "";
            if (currentXhr.status === 200) {
                resolve();
                response = JSON.parse(currentXhr.responseText);
                bookmark = response["docs"];
                for (let i = 0; i < response["docs"].length; i ++) {
                    let runInfo = response["docs"][i];
                    console.log(runInfo);
                    let cardCol = document.createElement("div");
                    cardCol.classList.add("mb-3");
                    cardCol.classList.add("mr-3");
                    cardCol.classList.add("col-lg-3");
                    cardCol.classList.add("col-md-4");
                    cardCol.classList.add("col-sm-12");
                    cardCol.classList.add("col-12");
                    cardCol.classList.add("col");


                    let card = document.createElement("div");
                    card.classList.add("card");
                    card.classList.add("bg-light");
                    cardCol.appendChild(card)

                    let cardImage = document.createElement("img");
                    cardImage.classList.add("card-img-top");
                    cardImage.src = "/api/v1/get_sample_thumbnail/" + runInfo["samples"]["0"];
                    card.appendChild(cardImage);

                    let cardBody = document.createElement("div");
                    cardBody.classList.add("card-body");
                    card.appendChild(cardBody);
                    let cardTitle = document.createElement("h5");
                    cardTitle.classList.add("card-title");
                    cardTitle.innerText = "TEST";
                    cardBody.appendChild(cardTitle);
                    let cardText = document.createElement("p");
                    cardText.classList.add("card-text");
                    let timestamp = new Date();
                    timestamp.setTime(runInfo["ingest_timestamp"] * 1000);
                    getUserInfo(runInfo["creator"]["uuid"]).then((userInfo) => {
                        cardText.innerText = "Uploaded by " + userInfo["name"] + "\n on " + timestamp.toLocaleString();
                    });
                    cardBody.appendChild(cardText);
                    let cardNote = document.createElement("p");
                    cardNote.classList.add("card-text");
                    cardBody.appendChild(cardNote);
                    let cardNoteInner = document.createElement("small");
                    cardNoteInner.classList.add("text-muted");
                    cardNoteInner.innerText = "Run " + runInfo["_id"];
                    cardNote.appendChild(cardNoteInner);

                    listView.appendChild(cardCol)
                }
                spinnerContainer.style.display = "none";
                currentXhr = null;
            }
        });
        currentXhr.send(data);
    });
}

let setPage = (page) => {
    currentPage = parseInt(page) - 1;
    if (currentPage < 0) {
        currentPage = 0
    }
    document.getElementById("page_number_top").value = currentPage + 1;
    document.getElementById("page_number_bottom").value = currentPage + 1;
    updateFragment();
}

let nextPage = () => {
    setPage(currentPage + 2);
}

let prevPage = () => {
    setPage(currentPage);
}

window.addEventListener("hashchange", fragmentMoveHandler);
fragmentMoveHandler();
