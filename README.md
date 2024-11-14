# C.R.A.B
A FOSS stack for ML dataset management and annotation

## Installation

For a local install, run `flask/build.sh` first.
Then run `generate-env.sh` to auto-generate a `.env` file.
If you're using externally managed S3 compatible storage, edit the `.env` file now and skip running `init-db.sh`. You'll need to configure databases manually.
Run `init-db.sh` to prepare your databases automatically.
Finally, run `docker compose up -d` to start your instance.
CRAB should now be avaliable on `http://localhost:8080`

### Prerequisites

You will need to pre-install Docker Compose and BIIGLE. Work is ongoing to integrate BIIGLE into this deployment, for now install [BIIGLE](https://biigle-admin-documentation.readthedocs.io/installation/) seperately.
