let modalAlert = (title, msg) => {
    let modal = new bootstrap.Modal(document.getElementById("modal"));
    document.getElementById("modalLabel").innerText = title;
    document.getElementById("modalText").innerText = msg;
    modal.show();
};

let cJobCheck = null;

let checkJob = (jobId, then = () => {}, onError = () => {}) => {
    const method = 'get';
    const xhr = new XMLHttpRequest();
    const progressBar = document.body.querySelector(".progress-bar");
    const spinnerContainer = document.body.querySelector(".spinner-container");
    xhr.open(method, "/api/v1/jobs/" + jobId);
    xhr.addEventListener('loadend', () => {
        if (xhr.status === 200) {

            let response = JSON.parse(xhr.responseText);

            if (response["status"] == "COMPLETE") {
                modalAlert("Snapshot taken", "You can now close this page, the snapshot has been successfully published.");
                progressBar.aria_valuenow = 0;
                progressBar.style.width = "0";
                spinnerContainer.style.display = "none";
            } else {
                setTimeout(() => {
                    checkJob(jobId, then, onError);
                }, 1000);
            }

            //form.before(note);

            //console.log(JSON.parse(xhr.responseText));
            //then(form, JSON.parse(xhr.responseText));
        } else {
            onError(xhr.status);
            modalAlert("Configuration failed", "Please try again");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = "0";
            spinnerContainer.style.display = "none";
        }
    });
    progressBar.aria_valuenow = 100;
    progressBar.style.width = "100%";
    progressBar.classList.add("bg-success");
    xhr.send();
}

let takeSnapshot = (then = () => {}, onError = () => {}) => {
    event.preventDefault();
    const method = 'post';
    const xhr = new XMLHttpRequest();
    const form = event.target.form;
    const fieldset = form.querySelector("fieldset");
    const data = new FormData(form);
    const progressBar = form.querySelector(".progress-bar");
    const spinnerContainer = form.querySelector(".spinner-container");
    const collectionUuid = form.querySelector("#form_collection_uuid").value;
    fieldset.disabled = true;
    spinnerContainer.style.display = "";
    xhr.open(method, "/api/v1/collections/" + collectionUuid + "/snapshot");
    xhr.addEventListener('loadend', () => {
        if (xhr.status === 200) {

            //modalAlert("Upload succeeded", "You should now continue to add metadata. It's possible to do this later.");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = "0";

            progressBar.classList.remove("bg-warning");
            progressBar.classList.add("bg-success");

            let response = JSON.parse(xhr.responseText);
            console.log(response);

            checkJob(response["job_id"], then, onError)
        } else {
            onError(xhr.status);
            modalAlert("Configuration failed", "Please try again");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = "0";
            fieldset.disabled = false;
            spinnerContainer.style.display = "none";
        }
    });
    progressBar.aria_valuenow = 100;
    progressBar.style.width = "100%";
    progressBar.classList.add("bg-warning");
    xhr.send(data);
};
