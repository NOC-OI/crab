# CRAB API Reference

## Authentication

CRAB uses bearer tokens to authenticate programmatic access. These tokens are usable on *all* endpoints, not only ones intended for machine readability. This is intentional functionality. Obtain a new access token from the web UI by going to the [access token page](/account/access-tokens). Use this token to access protected endpoints as your user account. This token will provide full access to your account on CRAB. If you want to limit access to that of a contibutor, you need to [create a service account](/docs/user-guide/create-service-account) and use that account instead.

An convenient way to test if your access token works is by using cURL and the dedicated [whoami](
/api/v1/whoami) endpoint:
```
$ curl -H "Authorization: Bearer c8cd079e-24d1-4250-aa4b-76deea231808.PUX7XcIE1id_YBWRZd3u3hg-ij4I0BMIjPQttwpAWsgWrkgUSlRCFscTWVMzIbXP" crab.noc.soton.ac.uk:8000
/api/v1/whoami

{
  "_id": "1be8cb35-77ce-4680-a4a8-f5f43607d5db",
  "_rev": "12-0f87d48d15ee9e943a914f72ac8737a9",
  "email": "alewin@noc.ac.uk",
  "name": "Alex Baldwin",
  "openid_sub": "607f3230-6127-44fe-966e-a7c05276d8ec",
  "short_name": "Alex"
}
```
NOTE: This API also works with a normal browser session.

## General API features

Many APIs in CRAB implement some common features for convenience. Outlined below are some common patterns across the API.

### Redirect

Set the GET parameter "redirect" to a URL-encoded URL in order to redirect a user after completion of an API request. This is intended for interactive browser applications, and will cause API endpoints to return HTML instead of JSON responses when errors occur. You can override this behaviour by adding the explicit "Accept: application/json" header to your request.

## Image runs

`/api/v1/runs`

Returns all runs. This is a paginated endpoint.

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| page | Int | Get | The desired page of the output |

`/api/v1/runs/<run_uuid>`

Returns metadata defining an image run.

`/api/v1/runs/<run_uuid>/as_zip`

Returns all metadata and image data for a run in a zip archive.

`/api/v1/apply_mapping`

Applies a sensor mapping to an uploaded staged run.

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| run_uuid | UUID | Post | The target upload ID to apply the mapping to |
| identifier | String | Post | The desired identifier for the image run |
| sensor | Enum ("ifcb", "raw-image") | Post | The sensor mapping to use in ingest |

## Samples

`/api/v1/samples/<sample_uuid>`

`/api/v1/samples/<sample_uuid>.tiff`

`/api/v1/samples/<sample_uuid>.tif`

Returns the lossless TIFF file, as stored in the database.

`/api/v1/samples/<sample_uuid>.png`

Returns a lossless* PNG file converted from the original TIFF file. Conversion is done for each request. May result in some downsampling. Use the original TIFF format if possible for data analysis.

`/api/v1/samples/<sample_uuid>.jpeg`

`/api/v1/samples/<sample_uuid>.jpg`

Returns a lossy JPEG file converted from the original TIFF file. Conversion is done for each request. Will result in downsampling. Use the original TIFF format if possible for data analysis. Intended for display over network connections only.

`/api/v1/samples/<sample_uuid>/metadata`

Returns metadata associated with the individual sample.

`/api/v1/samples/<sample_uuid>/thumbnail`

Returns a converted JPEG of the sample image. Uses a low quality (50) for fast network transfer. Not inteded for use other than as a thumbnail. Conversion is cached (TODO), so is prefereable to use for performance reasons.

## Projects

`/api/v1/projects`

Returns all projects. This is a paginated endpoint.

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| page | Int | Get | The desired page of the output |

`/api/v1/projects/<project_uuid>/new_collection`

Creates a new collection under a project.

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| name | String | Post | The name of the new collection |

`/api/v1/projects/<project_uuid>`

Returns metadata defining a project

## Collections

`/api/v1/collections`

Returns all collections. This is a paginated endpoint.

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| page | Int | Get | The desired page of the output |

`/api/v1/collections/<collection_uuid>`

Returns metadata defining a collection

`/api/v1/collections/<collection_uuid>/connect`

Adds a supported object to a collection.

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| to | UUID | Post | The objec to connect to the snapshot |
| type | Enum ("run") | Post | The type of object to connect |

`/api/v1/collections/<collection_uuid>/snapshot`

Takes a new snapshot of a collection. Returns a Job descriptor

| Parameter | Type | Method | Purpose |
| --- | --- | --- | --- |
| snapshot_name | String (optional) | Post | The desired identifier for the snapshot |
| public_visibility_switch | Enum ("true", "false") | Post | If the snapshot should override project settings and be visible globally |

## Snapshots

`/api/v1/snapshots/<snapshot_uuid>/delete`

Deletes a snapshot.

`/api/v1/snapshots/<snapshot_uuid>/makepkg/<package_type>`

Creates a vendor-specific image.

The only currently implemented `package_type` is `ifcb`.

`/api/v1/snapshots/<snapshot_uuid>/packages/<package_type>`

Downloads a vendor-specific package.

`/api/v1/snapshots/<snapshot_uuid>/as_zip`

Returns all snapshot metadata, sample metadata, and raw images as a zip file.

`/api/v1/snapshots/<snapshot_uuid>`

Returns metadata associated with the snapshot

`/api/v1/snapshots/<snapshot_uuid>/croissant`

Returns a [Croissant](https://docs.mlcommons.org/croissant/) JSON representation of the snapshot.

## Jobs

`/api/v1/jobs/<job_uuid>`

Returns the current status of a Job.

## Users and sessions

`/api/v1/users/<user_uuid>`

Returns basic user info, including name and email address.

`/api/v1/whoami`

Returns information about the currently logged in user.

`/api/v1/sessions/<session_or_token_uuid>/close`

Destroys an active session/API token.
