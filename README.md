# octohatrack, as a service

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

Use [GHArchive](https://www.gharchive.org/#bigquery) and the GitHub API to get all the contributors to a repo.

⚠️ This service will exceed the BigQuery free tier. See [pricing](https://cloud.google.com/bigquery/pricing) for details. 

## Limit permissions

The minimum permissions this service requires: 

 * Cloud Run Invoker
 * BigQuery Job User

Create a service account with these roles, and associate to the service, for limited permissions.

## Development and testing

For continuous deployment, [deploy the service with Cloud Buildpacks](https://cloud.google.com/run/docs/continuous-deployment-with-cloud-build).

For testing, change the `YEARMONTH` value in `app.py` to a shorter range (rather than process the entire archive.)