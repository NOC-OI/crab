
function via_cm_addon(via_inst) {
    this.via = via_inst;
    this.project_md = {};

    let remove_non_cm_buttons = () => {
        //document.getElementById("add_media_local").remove();
        //document.getElementById("add_media_bulk").remove();
        //document.getElementById("remove_media").remove();
        let buttons = this.via.control_panel_container.querySelectorAll(".svg_button");
        console.log(buttons);
        let buttons_to_remove = ["#micon_add_circle", "#micon_lib_add", "#micon_remove_circle", "#micon_download", "#micon_upload", "#micon_share", "#micon_import_export", "#micon_open"];
        buttons.forEach((button) => {
            let use = button.querySelector("use");
            if (buttons_to_remove.indexOf(use.href.baseVal) > -1) {
                button.remove()
            }
        });
        buttons.forEach((button) => {
            let use = button.querySelector("use");
            if (use.href.baseVal == "#micon_save") {
                console.log(button)
                //button.removeEventListener("click", )
                button.addEventListener("click", () => {
                    console.log("Click!")
                });
            }
        });
        //let svg = document.getElementById("micon_upload").parentNode.parentNode;
        //svg.remove()
        //document.getElementById("micon_download").parentNode.parentNode.remove()
        //console.log(this)
    };

    let from_b64 = (data) => {
        return atob(data.replace(/_/g, '/').replace(/-/g, '+'))
    }

    let load_from_hash = () => {
        if (window.location.hash) {
            this.project_md = JSON.parse(from_b64(window.location.hash.substring(1)))
            console.log(this.project_md)
            xhr = new XMLHttpRequest();
            xhr.open("GET", this.project_md["remote_project"]);
            xhr.addEventListener('loadend', () => {
                if (xhr.status === 200) {
                    response = JSON.parse(xhr.responseText);
                    project_load_on_remote_file_read(response);
                }
            });
            xhr.send();
        } else {
            console.err("NO HASH!")
        }
    };

    let project_load_on_remote_file_read = (project_data) => {
        this.via.d.project_load_json(project_data);
    };


    let remote_project_save = () => {
        console.log("Stub save to " + this.project_md["remote_project"])
    };

    remove_non_cm_buttons();
    load_from_hash();
}



function via_cm_addon_init() {
    console.log("VIA CM Addon Enabled");
    //this.remove_non_cm_buttons();
    //console.log(this)
    let addon = new via_cm_addon(this);
}


