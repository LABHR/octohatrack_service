import os
import time
from typing import List, Union

from flask import Flask, render_template, request, make_response
from github import Github
from github.GithubException import UnknownObjectException
from google.cloud import bigquery
from octohatrack.contributors_file import contributors_file as contrib_file
from octohatrack.helpers import progress_message

app = Flask(__name__)

# "*" for all, or use a YYYYMM format for limited results (e.g. 201810)
YEARMONTH = "*"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", None)
if GITHUB_TOKEN:
    app.logger.info("Service started with a valid GITHUB_TOKEN")
else:
    app.logger.warning("No GITHUB_TOKEN specified. Service may encounter rate limits. ")


def repo_split(repos):
    """From an input-populated querystring, split the result into a usable list"""
    return [x.strip() for x in repos.split(",")]


def unique_sort(users):
    """Sort case-insenstive"""
    return sorted(list(set(users)), key=str.casefold)


def api_contributors(repos: str) -> List[str]:
    """Get 'the' contributors"""
    contribs = []

    for repo in repo_split(repos):
        app.logger.info(f"API: {repo}")
        try:
            repo_obj = Github(GITHUB_TOKEN).get_repo(repo)
        except UnknownObjectException:
            return {"error": f"repo {repo} not found"}

        contr = repo_obj.get_contributors()
        uniq = unique_sort([c.login for c in contr])
        for c in uniq:
            contribs.append([repo, "api_contributor", c])
    return contribs


def pri_contributors(repos: str) -> List[str]:
    """Get all events associated to contribution.
    
    Notes: 
    * MemberEvent is adding collaborators, which is evidence of contribution, potentially outside repo.
    * JSON_EXTRACT is expensive, full table scan. 
    * Watching or Forking a repo isn't contributing.
    """
    client = bigquery.Client()

    repo_list = ",".join([f'"{r}"' for r in repo_split(repos)])

    query = f"""
    SELECT
        repo, type, login
    FROM (
        SELECT
            repo.name AS repo,
            type AS type,
            COALESCE(
                JSON_EXTRACT_SCALAR(payload, '$.member.login'),
                JSON_EXTRACT_SCALAR(payload, '$.member')
            ) AS login
        FROM
            `githubarchive.month.{YEARMONTH}`
        WHERE
            repo.name in ({repo_list})
            AND type = "MemberEvent" 
        GROUP BY
            repo, type, login
        UNION ALL
        SELECT
            repo.name as repo, type as type, actor.login AS login
        FROM
            `githubarchive.month.{YEARMONTH}`
        WHERE
            repo.name in ({repo_list})
            AND type NOT IN ("WatchEvent", "ForkEvent", "MemberEvent")
        GROUP BY
            repo, type, login
    )
    ORDER BY
    repo, type, LOWER(login) ASC
    """
    app.logger.info(f"PRI: {repo_list}, {YEARMONTH}")
    app.logger.info(query)
    query_job = client.query(query)  # Make an API request.

    contribs = []
    for row in query_job:
        contribs.append([row[0], row[1], row[2]])

    return contribs


def file_contributors(repos: str) -> List[str]:
    contribs = []
    for repo in repo_split(repos):
        app.logger.info(f"FIL: {repo}")
        contr = [c["user_name"] for c in contrib_file(repo)]
        uniq = unique_sort(contr)
        for c in uniq:
            contribs.append([repo, "file_contributor", c])
    return contribs


@app.route("/")
def main():

    start_time = time.time()
    repos = request.args.get("repos")

    if not repos:
        return render_template("base.html")

    api = api_contributors(repos)
    if type(api) == dict and "error" in api:
        return render_template("base.html", error=f"Exception occured: {api['error']}")

    pri = pri_contributors(repos)
    fil = file_contributors(repos)

    if request.args.get("raw"):
        app.logger.info("Returning raw data to user")
        contribs = api + pri + fil
        data = "\n".join([",".join(c) for c in contribs])
        response = make_response(data, 200)
        response.mimetype = "text/plain"
        return response

    # Reduce down to just list of contributors
    api = unique_sort([c[-1] for c in api])
    pri = unique_sort([c[-1] for c in pri])
    fil = unique_sort([c[-1] for c in fil])

    contribs = sorted(list(set(api + pri + fil)), key=str.casefold)

    data = {
        "contribs": contribs,
        "api": api,
        "pri": pri,
        "fil": fil,
        "new": set(pri) - set(api),
        "delta": len(contribs) - len(api),
        "nice_repos": ", ".join(
            repo_split(repos)[:-2] + [", and ".join(repo_split(repos)[-2:])]
        ),
        "time": f"{round(time.time() - start_time, 3)}s",
    }

    return render_template("base.html", data=data, repos=repos)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
