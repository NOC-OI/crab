let modalAlert = (title, msg) => {
    let modal = new bootstrap.Modal(document.getElementById("modal"));
    document.getElementById("modalLabel").innerText = title;
    document.getElementById("modalText").innerText = msg;
    modal.show();
};

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
            progressBar.style.width = 0;


            //form.before(note);
            spinnerContainer.style.display = "none";
            console.log(JSON.parse(xhr.responseText));
            then(form, JSON.parse(xhr.responseText));
        } else {
            onError(xhr.status);
            modalAlert("Configuration failed", "Please try again");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = 0;
            fieldset.disabled = false;
            spinnerContainer.style.display = "none";
        }
    });
    progressBar.aria_valuenow = 100;
    progressBar.style.width = "100%";
    progressBar.classList.add("bg-success");
    xhr.send(data);
};
