let fileRecord = {}
let workspaceUuid = document.getElementById("workspace_id").value;
let fileArea = document.getElementById("file_area");
let noFilesMessage = document.getElementById("no_files_message");
let topTextBox = document.getElementById("top_text");
let topProgressBar = document.getElementById("top_progress");
let visibleFileElements = [];
let filesystemHierarchy = {};
let totalUploads = 0;
let totalUploadsDone = 0;
let totalUploadTime = 0;
let lastUploadInChain = new Promise((resolve,reject) => {resolve()});

let fileDragOverHandler = (e) => {
    e.preventDefault();
}

let fileDropHandler = (e) => {
    e.preventDefault();

    if (e.dataTransfer.items) {
        // Use DataTransferItemList interface to access the file(s)
        for (let i = 0; i < e.dataTransfer.items.length; i++) {
            let item = e.dataTransfer.items[i].webkitGetAsEntry();
            if (item) {
                scanDirectory(item, "/");
            }
        }
    } else {
        // Use DataTransfer interface to access the file(s)
        for (let i = 0; i < e.dataTransfer.files.length; i++) {
            //console.log('dtf file[' + i + '].name = ' + e.dataTransfer.files[i].name);
            handleDroppedFile(e.dataTransfer.files[i], "/" + e.dataTransfer.files[i].name.replaceAll("\\", "").replaceAll("/", ""));
        }
    }

    sortView();
}

let scanDirectory = (item, path) => {
    let filename = item.name.replaceAll("\\", "").replaceAll("/", "");
    if (item.isDirectory) {
        let directoryReader = item.createReader();
        directoryReader.readEntries((entries) => {
            entries.forEach((entry) => {
                scanDirectory(entry, path + filename + "/");
            });
        });
    } else {
        item.file((file) => {
            handleDroppedFile(file, path + filename);
        });
    }
}

let addToFH = (path, uploading = false) => {
    let pathArray = path.split("/")
    let lastDir = filesystemHierarchy;
    for (let i = 0; i < pathArray.length; i++) {
        if (pathArray[i].length > 0) {
            if (!(pathArray[i] in lastDir)) {
                lastDir[pathArray[i]] = {
                    "children": {},
                    "open": false,
                    "uploading": uploading,
                    "folder": ((pathArray.length - 1) > i),
                    "path": pathArray.slice(0, i + 1).join("/")
                }
            }
            lastDir = lastDir[pathArray[i]]["children"]
        }
    }
}

let setPropOnFH = (path, key, value) => {
    let pathArray = path.split("/")
    let lastDir = filesystemHierarchy;
    let lobj = null;
    for (let i = 0; i < pathArray.length; i++) {
        if (pathArray[i].length > 0) {
            lobj = lastDir[pathArray[i]];
            lastDir = lastDir[pathArray[i]]["children"]
        }
    }
    lobj[key] = value;
    updateFileElements();
}

let updateFileElements = () => {
    reflowFileElements();
    renderInView();
}

let reflowFileElements = () => {
    let newVFE = [];

    let stack = []
    let state = {
        "dir": filesystemHierarchy,
        "dir_keys": Object.keys(filesystemHierarchy),
        "cidx": 0,
        "ld": 0
    }
    stack.push(state);

    while (stack.length > 0) {
        state = stack.pop();
        let dirKeys = state["dir_keys"];
        let dir = state["dir"];
        while (state["cidx"] < dirKeys.length) {
            let dk = dirKeys[state["cidx"]];
            let record = {
                "name": dk,
                "path": dir[dk]["path"],
                "folder": dir[dk]["folder"],
                "open": dir[dk]["open"],
                "il": state["ld"]
            }
            state["cidx"]++;
            newVFE.push(record);
            if (dir[dk]["open"]) {
                stack.push(state);
                stack.push({
                    "dir": dir[dk]["children"],
                    "dir_keys": Object.keys(dir[dk]["children"]),
                    "cidx": 0,
                    "ld": state["ld"] + 1
                });
                break;
            }
        }
    }

    visibleFileElements = newVFE;
}

let renderInView = () => {
    let visibleFromY = - fileArea.getBoundingClientRect().top;
    let visibleToY = visibleFromY + window.innerHeight;
    let lineHeight = document.getElementById("pixel_scale_elem").getBoundingClientRect().height;
    let linesFrom = Math.floor(visibleFromY / lineHeight) + 1;
    let linesTo = Math.ceil(visibleToY / lineHeight) - 3;
    //console.log(visibleFromY)

    if (noFilesMessage != null) {
        noFilesMessage.remove();
        noFilesMessage = null;
    }

    fileArea.textContent = "";
    let fileSpacer = document.createElement("div");
    if (linesFrom < 0) {
        linesFrom = 0;
    }
    fileSpacer.style.height = (lineHeight * linesFrom) + "px";
    fileArea.appendChild(fileSpacer);
    for (let i = linesFrom; (i < visibleFileElements.length) && (i < linesTo); i++) {
        let filename = visibleFileElements[i]["name"];
        let fullpath = visibleFileElements[i]["path"];
        let fileDomEntry = document.createElement("div");
        let fileIconDomEntry = document.createElement("i");
        let filenameDomEntry = document.createElement("span");
        fileDomEntry.appendChild(fileIconDomEntry);
        fileDomEntry.appendChild(filenameDomEntry);
        fileDomEntry.style.marginLeft = (visibleFileElements[i]["il"] * 5) + "mm"
        filenameDomEntry.innerText = " " + filename;
        fileIconDomEntry.classList.add("bi");
        if (visibleFileElements[i]["folder"]) {
            let isOpen = visibleFileElements[i]["open"]
            if (isOpen) {
                fileIconDomEntry.classList.add("bi-folder2-open");
            } else {
                fileIconDomEntry.classList.add("bi-folder2");
            }
            fileDomEntry.addEventListener("click", () => {
                setPropOnFH(fullpath, "open", !isOpen);
            });
            fileDomEntry.style.cursor = "pointer";
        } else {
            fileIconDomEntry.classList.add("bi-file-earmark");
        }
        fileDomEntry.classList.add("file-entry");
        fileArea.appendChild(fileDomEntry);
    }
    if (linesTo < visibleFileElements.length) {
        let fileSpacerEnd = document.createElement("div");
        fileSpacerEnd.style.height = (lineHeight * (visibleFileElements.length - linesTo)) + "px";
        fileArea.appendChild(fileSpacerEnd);
    }
}

let dispatchUpload = (file, filename) => {
    return new Promise((resolve, reject) => {
        const fd = new FormData();
        fd.append("file", file, filename)
        const xhr = new XMLHttpRequest();
        errorHandler = () => {
            resolve();
            setTimeout(() => {
                lastUploadInChain = lastUploadInChain.then(() => {
                    return dispatchUpload(file, filename);
                });
            }, 1000);
        }
        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                console.log("Uploaded " + filename);
                resolve();
                totalUploadsDone++;
            } else {
                errorHandler();
            }
        };
        xhr.onerror = () => {
            errorHandler();
        };
        xhr.upload.onprogress = (e2) => {
            let prog = e2.loaded / e2.total;
        }
        xhr.open("POST", "/api/v1/workspaces/" + workspaceUuid, true);
        xhr.send(fd);
    });
}

let updateProgressBar = () => {
    if (totalUploads > 0) {
        topProgressBar.style.width = ((totalUploadsDone / totalUploads) * 100) + "%";
        if (totalUploadsDone < totalUploads) {
            let etime = 0
            if (totalUploadsDone > 2) {
                etime = (totalUploadTime / totalUploadsDone) * (totalUploads - totalUploadsDone);
            }
            let estime = "";
            if (etime > 0) {
                if (etime > 2) {
                    if (etime > 50) {
                        estime = "About " + Math.round(etime/60) + " minutes remaining.";
                    } else {
                        estime = "About " + Math.round(etime) + " seconds remaining.";
                    }
                } else {
                    estime = "Just a few seconds remaining...";
                }
            }
            estime = estime
            topTextBox.innerText = "Uploading file " + totalUploadsDone + " of " + totalUploads + ". " + estime;
            topProgressBar.classList.add("progress-bar-striped");
            topProgressBar.classList.add("progress-bar-animated");
            topProgressBar.classList.remove("bg-success");
            totalUploadTime++;
        } else {
            topTextBox.innerText = "Finished uploading " + totalUploadsDone + " files.";
            topProgressBar.style.width = "100%";
            topProgressBar.classList.add("bg-success");
            topProgressBar.classList.remove("progress-bar-striped");
            topProgressBar.classList.remove("progress-bar-animated");
            updateFileElements();
        }
    }
}

let sortView = () => {
    if (Object.keys(fileRecord).length > 0) {

        const list = document.getElementById("file_area");
        [...list.children]
            .sort((a, b) => a.innerText.localeCompare(b.innerText, navigator.languages[0] || navigator.language, {numeric: true, ignorePunctuation: true}))
            .forEach(node => list.appendChild(node));
    }
}

let pollChanges = () => {
    const xhr = new XMLHttpRequest();
    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            let wsd = JSON.parse(xhr.responseText);
            let updates = false;

            if ("identifier" in wsd) {
                if (wsd["identifier"] != null) {
                    document.getElementById("workspace_identifier_label").innerText = wsd["identifier"];
                }
            }

            for (const [path, fd] of Object.entries(wsd["files"])) {
                if (fileRecord.hasOwnProperty(path)) {
                    //console.log("skip!")
                } else {
                    let filename = path;
                    fileRecord[filename] = fd
                    addToFH(filename, false)
                    updates = true;
                }
            }
            if (updates) {
                updateFileElements();
                //sortView();
            }
        } else {
            document.getElementById("workspace_identifier_label").innerHTML = "<em>Workspace not found!</em>";
            document.getElementById("file_area").innerHTML = "<span id=\"no_files_message\"><strong>Error!</strong><br />Could not retrieve workspace information. Has the workspace been deleted?</span>";
        }
    };
    xhr.open("GET", "/api/v1/workspaces/" + workspaceUuid, true);
    xhr.send(null);
}

let handleDroppedFile = (file, filename) => {
    filename = filename.replace(/^\/+/g, "");
    fileRecord[filename] = {
    }
    addToFH(filename, true)
    totalUploads++;
    lastUploadInChain = lastUploadInChain.then(() => {return dispatchUpload(file, filename);});
}

let startDefinedJob = (jobType) => {
    const xhr = new XMLHttpRequest();
    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            let responseObject = JSON.parse(xhr.responseText);
            console.log(responseObject);

            window.open("/jobs/" + responseObject["job_id"], '_blank').focus();
        }
    };
    if (jobType == "PROCESS_DEPOSIT") {
        xhr.open("GET", "/api/v1/workspaces/" + workspaceUuid + "/deposit", true);
        xhr.send();
    } else {
        const formData = new FormData();
        formData.append("type", jobType);
        xhr.open("POST", "/api/v1/workspaces/" + workspaceUuid + "/process", true);
        xhr.send(formData);
    }
}

let editWorkspaceNameButton = () => {
    document.getElementById("workspace_identifier_label").style.display = "none";
    document.getElementById("workspace_identifier_input_group").style.display = null;
}

let saveWorkspaceNameButton = () => {
    document.getElementById("workspace_identifier_label").style.display = null;
    document.getElementById("workspace_identifier_input_group").style.display = "none";

    const xhr = new XMLHttpRequest();
    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            let responseObject = JSON.parse(xhr.responseText);
            console.log(responseObject);
        }
    };
    const formData = new FormData();
    formData.append("identifier", document.getElementById("workspace_identifier_input").value);
    xhr.open("POST", "/api/v1/workspaces/" + workspaceUuid + "/metadata", true);
    xhr.send(formData);
}

setInterval(updateProgressBar, 1000);
setInterval(pollChanges, 3000);
pollChanges();

document.addEventListener("scroll", (e) => {
    renderInView()
});

document.addEventListener("resize", (e) => {
    renderInView()
});
