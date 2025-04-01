let fileDragOverHandler = (e) => {
    e.preventDefault();
}

let fileDropHandler = (e) => {
    e.preventDefault();

    if (e.dataTransfer.items) {
        // Use DataTransferItemList interface to access the file(s)
        for (let i = 0; i < e.dataTransfer.items.length; i++) {
            // If dropped items aren't files, reject them
            if (e.dataTransfer.items[i].kind === 'file') {
                let file = e.dataTransfer.items[i].getAsFile();
                //console.log('dti file[' + i + '].name = ' + file.name);
                handleDroppedFile(file, e);
            }
        }
    } else {
        // Use DataTransfer interface to access the file(s)
        for (let i = 0; i < e.dataTransfer.files.length; i++) {
            //console.log('dtf file[' + i + '].name = ' + e.dataTransfer.files[i].name);
            handleDroppedFile(e.dataTransfer.files[i], e);
        }
    }
}

let workspaceUuid = document.getElementById("workspace_id").value;

let handleDroppedFile = (file, e) => {
    console.log(file.name);
    console.log(file);
    const fd = new FormData();
    fd.append("file", file, file.name)
    const xhr = new XMLHttpRequest();
    xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            console.log("Uploaded " + file.name);
        }
    };
    xhr.open("POST", "/api/v1/workspaces/" + workspaceUuid, true);
    xhr.send(fd);
}
