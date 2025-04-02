let fileDragOverHandler = (e) => {
    e.preventDefault();
}

let fileDropHandler = (e) => {
    e.preventDefault();

    if (e.dataTransfer.items) {
        // Use DataTransferItemList interface to access the file(s)
        for (let i = 0; i < e.dataTransfer.items.length; i++) {
            // If dropped items aren't files, reject them

            /*
            if (e.dataTransfer.items[i].kind === 'file') {
                let file = e.dataTransfer.items[i].getAsFile();
                //console.log('dti file[' + i + '].name = ' + file.name);
                console.log(file)
                handleDroppedFile(file, e);
            }*/

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

let fileRecord = {}
let workspaceUuid = document.getElementById("workspace_id").value;
let fileArea = document.getElementById("file_area");
let noFilesMessage = document.getElementById("no_files_message");
let lastUploadInChain = new Promise((resolve,reject) => {resolve()});

let dispatchUpload = (file, filename) => {
    return new Promise((resolve, reject) => {
        let fileRecordEntry = fileRecord[filename]
        const fd = new FormData();
        fd.append("file", file, filename)
        const xhr = new XMLHttpRequest();
        fileRecordEntry["progress_bar"].classList.remove("bg-warning");
        fileRecordEntry["progress_bar"].classList.remove("progress-bar-striped");
        fileRecordEntry["progress_bar"].classList.remove("progress-bar-animated");
        fileRecordEntry["progress_bar"].classList.add("bg-success");
        fileRecordEntry["progress_bar"].style.width = 0;
        errorHandler = () => {
            resolve();
            fileRecordEntry["progress_bar"].classList.add("bg-danger");
            fileRecordEntry["dom"].querySelector("span").classList.add("text-danger");
            //delete fileRecord[filename];
            setTimeout(() => {
                fileRecordEntry["progress_bar"].classList.remove("bg-danger");
                fileRecordEntry["progress_bar"].classList.add("bg-warning");
                fileRecordEntry["progress_bar"].classList.add("progress-bar-striped");
                fileRecordEntry["progress_bar"].classList.add("progress-bar-animated");
                fileRecordEntry["progress_bar"].style.width = "100%";
                lastUploadInChain = lastUploadInChain.then(() => {
                    fileRecordEntry["dom"].querySelector("span").classList.remove("text-danger");
                    return dispatchUpload(file, filename);
                });
            }, 1000);
        }
        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                console.log("Uploaded " + filename);
                fileRecordEntry["dom"].querySelector("span").classList.remove("text-secondary");
                resolve();
                fileRecordEntry["progress_bar_container"].remove()
            } else {
                errorHandler();
            }
        };
        xhr.onerror = () => {
            errorHandler();
        };
        xhr.upload.onprogress = (e2) => {
            let prog = e2.loaded / e2.total;
            //console.log(prog);
            fileRecordEntry["progress_bar"].style.width = (prog * 100) + "%";
        }
        xhr.open("POST", "/api/v1/workspaces/" + workspaceUuid, true);
        xhr.send(fd);
    });
}

let sortView = () => {
    console.log(Object.keys(fileRecord).length)
    if (Object.keys(fileRecord).length > 0) {
        if (noFilesMessage != null) {
            noFilesMessage.remove();
            noFilesMessage = null;
        }
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
            for (const [path, fd] of Object.entries(wsd["files"])) {
                if (fileRecord.hasOwnProperty(path)) {
                    //console.log("skip!")
                } else {
                    let filename = path;
                    let fileDomEntry = document.createElement("div");
                    let fileIconDomEntry = document.createElement("i");
                    let filenameDomEntry = document.createElement("span");
                    fileDomEntry.appendChild(fileIconDomEntry);
                    fileDomEntry.appendChild(filenameDomEntry);
                    filenameDomEntry.innerText = " " + filename;
                    fileIconDomEntry.classList.add("bi");
                    fileIconDomEntry.classList.add("bi-file-earmark-fill");
                    fileDomEntry.classList.add("file-entry");
                    fileRecord[filename] = fd
                    fileRecord[filename]["dom"] = fileDomEntry;
                    fileArea.appendChild(fileDomEntry);
                }
            }
            sortView();
        }
    };
    xhr.open("GET", "/api/v1/workspaces/" + workspaceUuid, true);
    xhr.send(null);
}

setInterval(pollChanges, 3000);

let handleDroppedFile = (file, filename) => {
    //console.log(file);
    filename = filename.replace(/^\/+/g, "");
    let fileDomEntry = document.createElement("div");
    let fileIconDomEntry = document.createElement("i");
    let filenameDomEntry = document.createElement("span");
    let fileProgressContainer = document.createElement("div");
    let fileProgressBar = document.createElement("div");
    fileProgressContainer.appendChild(fileProgressBar);
    fileProgressContainer.classList.add("progress");
    fileProgressContainer.style.width = "10em";
    fileProgressContainer.style.float = "right";
    fileProgressBar.classList.add("progress-bar");
    fileProgressBar.classList.add("progress-bar-striped");
    fileProgressBar.classList.add("progress-bar-animated");
    fileProgressBar.classList.add("bg-warning");
    fileProgressBar.style.width = "100%";
    fileProgressBar.role = "progressbar";
    fileDomEntry.appendChild(fileIconDomEntry);
    fileDomEntry.appendChild(filenameDomEntry);
    fileDomEntry.appendChild(fileProgressContainer);
    filenameDomEntry.innerText = " " + filename;
    filenameDomEntry.classList.add("text-secondary");
    fileIconDomEntry.classList.add("bi");
    fileIconDomEntry.classList.add("bi-file-earmark-fill");
    fileDomEntry.classList.add("file-entry");
    fileRecord[filename] = {
        "dom": fileDomEntry,
        "progress_bar": fileProgressBar,
        "progress_bar_container": fileProgressContainer
    }
    fileArea.appendChild(fileDomEntry);
    lastUploadInChain = lastUploadInChain.then(() => {return dispatchUpload(file, filename);});
}

pollChanges();
