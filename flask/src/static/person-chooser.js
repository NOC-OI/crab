
let personSearchRequest = null;

let searchForPerson = (inputString) => {
    personSearchRequest = new Promise((resolve, reject) => {
        let xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/v1/users/search");
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
        const formData = new FormData();
        formData.append("all", inputString);
        xhr.send(formData);
    });

    personSearchRequest.then(console.log)

    return personSearchRequest
}
