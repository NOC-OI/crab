let modalAlert = (title, msg) => {
    let modal = new bootstrap.Modal(document.getElementById("uploadModal"));
    document.getElementById("uploadModalLabel").innerText = title;
    document.getElementById("uploadModalText").innerText = msg;
    modal.show();
}

let setSensorType = (type) => {
    event.preventDefault();
    document.getElementById("sensor_selector_raw_image").classList.remove("active");
    document.getElementById("sensor_selector_pre_classified").classList.remove("active");
    document.getElementById("sensor_selector_flowcam").classList.remove("active");
    document.getElementById("sensor_selector_ifcb").classList.remove("active");
    switch (type) {
        case "ifcb":
            document.getElementById("sensor_selector_hf").value = "ifcb"
            document.getElementById("sensor_selector_ifcb").classList.add("active");
            document.getElementById("sensor_selector_ifcb").style.display = "";
            break;
        case "flowcam":
            document.getElementById("sensor_selector_hf").value = "flowcam"
            document.getElementById("sensor_selector_flowcam").classList.add("active");
            document.getElementById("sensor_selector_flowcam").style.display = "";
            break;
        case "pre-classified":
            document.getElementById("sensor_selector_hf").value = "pre-classified"
            document.getElementById("sensor_selector_pre_classified").classList.add("active");
            break;
        default:
            document.getElementById("sensor_selector_hf").value = "raw-image"
            document.getElementById("sensor_selector_raw_image").classList.add("active");
    }
}

let analyseMetadata = (form, response) => {
    const progressBar = form.querySelector(".progress-bar");
    const spinnerContainer = form.querySelector(".spinner-container");
    spinnerContainer.style.display = "none";
    progressBar.aria_valuenow = 0;
    progressBar.style.width = 0;
    progressBar.classList.remove("bg-success");
    let note = document.createElement("div");
    note.classList.add("alert");
    note.role = "alert";
    let detectedType = null;
    let directoryStructure = response["directory_structure"];
    let fileList = response["file_list"];
    let cd = "";
    let definitiveDetection = false;
    document.getElementById("form_run_uuid").value = response["run_uuid"];

    // Traverse down single directories
    while (Object.keys(directoryStructure).length == 1) {
        let pcd = Object.keys(directoryStructure)[0];
        if (typeof directoryStructure[pcd] === 'string' || directoryStructure[pcd] instanceof String) {
            detectedType = "single-file";
            definitiveDetection = true; // Only a single file in the zip!
        } else {
            cd = pcd + "/";
            directoryStructure = directoryStructure[pcd];
        }
    }

    console.log("cd /" + cd)
    console.log(directoryStructure)

    for (let i = 0; i < fileList.length; i++) {
        if (fileList[i].endsWith(".adc")) {
            let basename = fileList[i].substring(0, fileList[i].length - 4);
            if (fileList.indexOf(basename + ".hdr") > -1) {
                if (fileList.indexOf(basename + ".roi") > -1) {
                    console.log("IFCB ROI COLLECTION " + basename);
                    detectedType = "ifcb";
                    definitiveDetection = true;
                }
            }
        }
    }

    if (detectedType == null) {
        detectedType = "raw-image";
    }
    

    document.getElementById("form_md_sample_time").value = response["timestamp"];
    //console.log(response);
    switch (detectedType) {
        case "ifcb":
            note.classList.add("alert-success");
            note.appendChild(document.createTextNode("Upload succeeded, IFCB data detected."));
            break;
        case "pre-classified":
            note.classList.add("alert-success");
            note.appendChild(document.createTextNode("Upload succeeded, detected pre-classified images, please verify extracted metadata."));
            break;
        case "raw-image":
        default:
            note.classList.add("alert-warning");
            note.appendChild(document.createTextNode("Upload succeeded, but could not auto-detect sensor type, please verify extracted metadata."));
    }
    setSensorType(detectedType);
    form.before(note);
    document.getElementById("metadata_form_container").style.display = "";
}

let uploadFile = (then = () => {}, onError = () => {}, uri = "/upload") => {
    event.preventDefault();
    const method = 'post';
    const xhr = new XMLHttpRequest();
    const form = event.target.form;
    const fieldset = form.querySelector("fieldset");
    const data = new FormData(form);
    const progressBar = form.querySelector(".progress-bar");
    const spinnerContainer = form.querySelector(".spinner-container");
    fieldset.disabled = true;
    spinnerContainer.style.display = "";
    xhr.open(method, uri);
    xhr.addEventListener('loadend', () => {
        if (xhr.status === 200) {

            //modalAlert("Upload succeeded", "You should now continue to add metadata. It's possible to do this later.");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = 0;


            //form.before(note);
            spinnerContainer.style.display = "none";
            then(form, JSON.parse(xhr.responseText));
        } else {
            onError(xhr.status);
            modalAlert("Upload failed", "Please try again");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = 0;
            fieldset.disabled = false;
            spinnerContainer.style.display = "none";
        }
    });
    xhr.upload.addEventListener("progress", event => {
        //console.log(event.loaded)
        let perc = (event.loaded / event.total) * 100;
        //console.log(perc)

        if (perc > 99) {
            const progressBar = form.querySelector(".progress-bar");
            const spinnerContainer = form.querySelector(".spinner-container");
            spinnerContainer.style.display = "";
            progressBar.aria_valuenow = 100;
            progressBar.style.width = "100%";
            progressBar.classList.add("bg-success");
            spinnerContainer.querySelector(".spinner-container-text").innerText = " Extracting metadata...";
        } else {
            progressBar.aria_valuenow = perc;
            progressBar.style.width = perc + "%";
        }
        //console.log(progressBar)
    });
    xhr.send(data);
}

let confirmMetadata = (then = () => {}, onError = () => {}, uri = "/applyMapping") => {
    event.preventDefault();
    const method = 'post';
    const xhr = new XMLHttpRequest();
    const form = event.target.form;
    const fieldset = form.querySelector("fieldset");
    form.querySelector("#form_run_uuid").disabled = false;
    const data = new FormData(form);
    const progressBar = form.querySelector(".progress-bar");
    const spinnerContainer = form.querySelector(".spinner-container");
    fieldset.disabled = true;
    spinnerContainer.style.display = "";
    xhr.open(method, uri);
    xhr.addEventListener('loadend', () => {
        if (xhr.status === 200) {

            modalAlert("Upload succeeded", "You can now close this page.");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = 0;
            progressBar.classList.remove("bg-success");
            //form.before(note);
            spinnerContainer.style.display = "none";
            then(form, JSON.parse(xhr.responseText));
        } else {
            onError(xhr.status);
            modalAlert("Unpacking archive failed", "Please try again");
            progressBar.aria_valuenow = 0;
            progressBar.style.width = 0;
            fieldset.disabled = false;
            spinnerContainer.style.display = "none";
        }
    });
    xhr.upload.addEventListener("progress", event => {
        //console.log(event.loaded)
        let perc = (event.loaded / event.total) * 100;
        //console.log(perc)

        if (perc > 99) {
            const progressBar = form.querySelector(".progress-bar");
            const spinnerContainer = form.querySelector(".spinner-container");
            spinnerContainer.style.display = "";
            progressBar.aria_valuenow = 100;
            progressBar.style.width = "100%";
            progressBar.classList.add("bg-success");
            spinnerContainer.querySelector(".spinner-container-text").innerText = " Extracting metadata...";
        } else {
            progressBar.aria_valuenow = perc;
            progressBar.style.width = perc + "%";
        }
        //console.log(progressBar)
    });
    xhr.send(data);
}
