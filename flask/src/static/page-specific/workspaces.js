

let deleteWorkspace = (wsUuid) => {
    return new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open("DELETE", "/api/v1/workspaces/" + wsUuid);
        xhr.addEventListener('loadend', () => {
            if (xhr.status === 200) {
                let response = JSON.parse(xhr.responseText);
                resolve(response);
            } else {
                try {
                    let response = JSON.parse(xhr.responseText);
                    reject(response);
                } catch {
                    reject(xhr.responseText);
                }
            }
        });
        xhr.send();
    });
}

let deleteWorkspaceButtonListener = null;

let deleteWorkspaceButton = (wsUuid, redirectToWorkspaces = false) => {
    let modal = new bootstrap.Modal(document.getElementById("deleteModal"));
    modal.show();
    if (deleteWorkspaceButtonListener != null) {
        document.getElementById("deleteModalConfirmButton").removeEventListener("click", deleteWorkspaceButtonListener);
    }
    deleteWorkspaceButtonListener = (e) => {
        document.getElementById("deleteModalWaiting").style.visibility = null;

        deleteWorkspace(wsUuid)
        .then(() => {
            if (redirectToWorkspaces) {
                window.location.replace("/workspaces");
            } else {
                window.location.reload();
            }
        })
        .finally(() => {
            modal.hide()
            document.getElementById("deleteModalWaiting").style.visibility = "hidden";
        });
    };
    document.getElementById("deleteModalConfirmButton").addEventListener("click", deleteWorkspaceButtonListener);
}
