let userCache = {};
let sampleCache = {};
let searchSelector = {};

let fromClass = "run";
let currentPage = -1;
let currentXhr = null;

let getUserInfo = (uuid) => {
    return new Promise((resolve, reject) => {
        if (!userCache.hasOwnProperty(uuid)) {
            userCache[uuid] = new Promise((resolveInner, rejectInner) => {
                let xhr = new XMLHttpRequest();
                xhr.open("GET", "/api/v1/users/" + uuid);
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
        "p": currentPage,
        "s": searchSelector
    }
    window.location.hash = base64URLencode(JSON.stringify(content));
}

let fragmentMoveHandler = () => {
    let content = {}
    try {
        content = JSON.parse(base64URLdecode(window.location.hash.replace(/#/g, "")));
    } catch (e) {
        updateFragment()
    }
    if (content.hasOwnProperty("p")) {
        currentPage = content["p"]
    }
    if (content.hasOwnProperty("s")) {
        searchSelector = content["s"]
    }
    if (currentPage < 0) {
        currentPage = 0
    }
    loadPage(fromClass, searchSelector, {}, currentPage);
}

let renderPage = (docs, docClass, listView, page) => {
    const spinnerContainer = document.getElementById("page_spinner");
    if (docs.length == 0) {
        if (page > 0) { // We only want to do this if we're past page one- otherwise we could loop over an empty page!
            setPage(page); // The setPage function is one indexed, so this is actually going to the previous page
        } else {
            let alertCol = document.createElement("div");
            alertCol.classList.add("col");
            alertCol.classList.add("col-12");
            alertCol.classList.add("mr-3");
            listView.appendChild(alertCol)

            let alert = document.createElement("div");
            alert.classList.add("alert");
            alert.classList.add("alert-warning");
            alert.innerText = "No matching data found!";
            alertCol.appendChild(alert)
        }
    }
    for (let i = 0; i < docs.length; i ++) {
        let docInfo = docs[i];
        console.log(docInfo);
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

        switch (docClass) {
            case "run":
            case "project":
            case "collection":
            default:
                let cardImage = document.createElement("img");
                cardImage.classList.add("card-img-top");
                if (docClass == "run") {
                    cardImage.src = "/api/v1/samples/" + docInfo["samples"]["0"] + "/thumbnail";
                }
                card.appendChild(cardImage);

                let cardBody = document.createElement("div");
                cardBody.classList.add("card-body");
                card.appendChild(cardBody);
                let cardTitle = document.createElement("a");
                switch (docClass) {
                    default:
                        cardTitle.href = "/" + docClass + "s/" + docInfo["_id"];
                        break;
                }
                cardTitle.classList.add("card-title");
                cardTitle.classList.add("fs-3");
                cardTitle.innerText = docInfo["_id"];
                if (docInfo.hasOwnProperty("identifier")) {
                    cardTitle.innerText = docInfo["identifier"]
                }
                cardBody.appendChild(cardTitle);

                let cardText = document.createElement("p");
                cardText.classList.add("card-text");
                switch (docClass) {
                    case "project":
                        cardText.innerText = docInfo["description"];
                        break;
                    case "run":
                        let timestamp = new Date();
                        timestamp.setTime(docInfo["ingest_timestamp"] * 1000);
                        getUserInfo(docInfo["creator"]["uuid"]).then((userInfo) => {
                            cardText.innerText = "Uploaded by " + userInfo["name"] + "\n on " + timestamp.toLocaleString();
                        });
                        break;
                }
                cardBody.appendChild(cardText);

                switch (docClass) {
                    default:
                        let cardNote = document.createElement("p");
                        cardNote.classList.add("card-text");
                        cardBody.appendChild(cardNote);
                        let cardNoteInner = document.createElement("small");
                        cardNoteInner.classList.add("text-muted");
                        cardNoteInner.innerText = "{" + docInfo["_id"] + "}";
                        cardNote.appendChild(cardNoteInner);
                        break;
                }
                break;
        }

        listView.appendChild(cardCol);
    }
    spinnerContainer.style.display = "none";
    currentXhr = null;
}

let loadPage = (fromClass = "run", selector = {}, sort = {}, page = 0) => {
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
        switch (fromClass) {
            case "project":
                currentXhr.open("POST", "/api/v1/projects");
                break;
            default:
            case "run":
                currentXhr.open("POST", "/api/v1/runs");
                break;
        }
        currentXhr.addEventListener('loadend', () => {
            let listView = document.getElementById("list_view");
            listView.innerHTML = "";
            if (currentXhr.status === 200) {
                resolve();
                response = JSON.parse(currentXhr.responseText);
                let docs = response["docs"];
                renderPage(docs, fromClass, listView, page)
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

let fcElement = document.getElementById("class_of_browse_object");
if (typeof(fcElement) != 'undefined' && fcElement != null) {
    fromClass = fcElement.value;
}
window.addEventListener("hashchange", fragmentMoveHandler);
fragmentMoveHandler();
