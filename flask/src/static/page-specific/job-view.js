let xhr = null;
let jobId = null;
let progressBar = null;
let jobOutput = null;
let spinnerContainer = null;
let spinnerText = null;

let updateJobInfo = () => {
    if (xhr != null) {
        xhr.abort();
    }
    xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/v1/jobs/" + jobId);
    xhr.addEventListener('loadend', () => {
        if (xhr.status === 200) {
            response = JSON.parse(xhr.responseText);
            switch (response["status"]) {
                case "ERROR":
                    progressBar.classList.remove("bg-warning");
                    progressBar.classList.remove("bg-success");
                    progressBar.classList.remove("progress-bar-striped");
                    progressBar.classList.add("bg-danger");
                    jobOutput.innerText = response["msg"] + "\n" + response.hasOwnProperty("trace") ? response["trace"] + "\n" : ""
                    spinnerContainer.style.display = "none";
                    break;
                case "COMPLETE":
                    progressBar.classList.remove("bg-warning");
                    progressBar.classList.remove("bg-danger");
                    progressBar.classList.add("bg-success");
                    progressBar.classList.remove("progress-bar-striped");
                    progressBar.style.width = "100%"
                    jobOutput.innerText = JSON.stringify(response["result"], null, 2);
                    spinnerContainer.style.display = "none";
                    break;
                default:
                    progressBar.classList.remove("bg-warning");
                    progressBar.classList.remove("bg-danger");
                    progressBar.classList.add("bg-success");
                    if (response.hasOwnProperty("progress")) {
                        progressBar.classList.remove("progress-bar-striped");
                        progressBar.style.width = (response["progress"] * 100) + "%"
                    } else {
                        progressBar.classList.add("progress-bar-striped");
                    }
                    spinnerText.innerText = " Working on it...";

            }
        }
    });
    xhr.send();
}

jobOutput = document.getElementById("job_output")
progressBar = document.querySelector(".progress-bar");
spinnerContainer = document.querySelector(".spinner-container");
spinnerText = document.querySelector(".spinner-container-text");
jobId = document.getElementById("job_id").value;
setInterval(updateJobInfo, 1000);
