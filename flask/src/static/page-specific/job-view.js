let xhr = null;
let jobOutput = document.getElementById("job_output")
let progressBar = document.querySelector(".progress-bar");
let spinnerContainer = document.querySelector(".spinner-container");
let spinnerText = document.querySelector(".spinner-container-text");
let redirectCheckbox = document.getElementById("redirect_checkbox");
let checkboxContainer = document.getElementById("redirect_checkbox_container");
let redirectButtonContainer = document.getElementById("redirect_button_container");
let redirectButton = document.getElementById("redirect_button");
let jobId = document.getElementById("job_id").value;

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
                    jobOutput.innerText = "EXITED WITH ERROR" + "\n\n" + response["msg"] + "\n" + (response.hasOwnProperty("trace") ? response["trace"] + "\n" : "")
                    spinnerContainer.style.display = "none";
                    checkboxContainer.style.display = "none";
                    break;
                case "COMPLETE":
                    progressBar.classList.remove("bg-warning");
                    progressBar.classList.remove("bg-danger");
                    progressBar.classList.add("bg-success");
                    progressBar.classList.remove("progress-bar-striped");
                    progressBar.style.width = "100%"
                    jobOutput.innerText = JSON.stringify(response["result"], null, 2);
                    spinnerContainer.style.display = "none";
                    checkboxContainer.style.display = "none";

                    if (response["result"].hasOwnProperty("ui_redirect")) {
                        redir_uri = response["result"]["ui_redirect"];
                        if (redirectCheckbox.checked) {
                            window.location.href = redir_uri;
                        }
                        redirectButtonContainer.style.display = null;
                        redirectButton.href = redir_uri;
                    }
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

updateJobInfo();
setInterval(updateJobInfo, 1000);
