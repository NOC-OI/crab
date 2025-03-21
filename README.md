![Centralised Repository for Annotations and BLOBs](flask/src/static/crab-logotext512.png)

## About

> [!NOTE]
> This repository is still in the testing phase. Some features may be broken or unstable.

CRAB is a FOSS stack for ML dataset management and annotation. It includes preconfigured profiles for importing IFCB and LISST-Holo data. If you have another data format you would like added, please open an issue on GitHub or send me an email. CRAB manages ingesting data, providing all files in a uniform TIFF format on an S3 compatible object store. Metadata is searchable using queries to the integrated CouchDB server, allowing you to easily access data stored on the platform.

## Prerequisites

CRAB requires Docker Compose to run, but otherwise comes with everything you need for a minimal install out of the box.

## Installation

- For a local install, run `build-all.sh` first.
- Then run `generate-env.sh` to auto-generate a `.env` file and the crab config file `config/crab.json`.
- If you're using externally managed S3 compatible storage, edit `.env` and `config/crab.json` now and skip running `init-db.sh`. You'll need to configure databases manually. Otherwise, run `init-db.sh` to prepare your databases automatically.
- Finally, run `launch.sh` to start your instance.
- CRAB should now be avaliable on `http://localhost:8080`.
- Keycloak configuration isn't handled automatically for now, so head to `http://localhost:8080/keycloak` to configure users for login.

## Documentation

For futher notes on [installation](./flask/src/docs/admin-guide.md), [using the software](./flask/src/docs/user-guide.md), and [connecting to the CRAB API](./flask/src/docs/api-reference.md), head to the [docs folder](./flask/src/docs/index.md). These markdown documents are also avaliable on an installed instance under the "Help" tab.

## License
CRAB is free software under the AGPL-3.0 license.
The CRAB Logo (© 2024, Alex Baldwin) is licensed under CC BY-SA 4.0.
