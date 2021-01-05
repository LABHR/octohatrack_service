# octohatrack, as a service

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

Use [GHArchive](https://www.gharchive.org/#bigquery) and the GitHub API to get all the contributors to a repo.

⚠️ This service will exceed the BigQuery free tier. See [pricing](https://cloud.google.com/bigquery/pricing) for details. 

## Limit permissions

The minimum permissions this service requires: 

 * Cloud Run Invoker
 * BigQuery Job User

Create a service account with these roles, and associate to the service, for limited permissions.

## Raw Data

Add `?raw=true` to the URL to return the raw data from the result.

## CLI

The `cli.py` allows for file-based searching for larger searches, returning raw data to stdout

```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
python cli.py --repo-list list-of-repos.txt
```

## Limitations

If your repo has been renamed, provide both the new and old names. The new name will not appear in pre-rename gharchive data. Note that some duplication may occur in api/file records when using `raw`. 



## Development and testing

For continuous deployment, [deploy the service with Cloud Buildpacks](https://cloud.google.com/run/docs/continuous-deployment-with-cloud-build).

For testing, change the `YEARMONTH` value in `app.py` to a shorter range (rather than process the entire archive.)
