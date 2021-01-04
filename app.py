import os
import time
from typing import List, Union

from flask import Flask, render_template, request
from github import Github
from github.GithubException import UnknownObjectException
from google.cloud import bigquery
from octohatrack.contributors_file import contributors_file as contrib_file
from octohatrack.helpers import progress_message

app = Flask(__name__)

# "*" for all, or use a YYYYMM format for limited results (e.g. 201810)
YEARMONTH = "*"


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
        print(f"API: {repo}")
        try:
            repo = Github().get_repo(repo)
        except UnknownObjectException:
            return {"error": f"repo {repo} not found"}

        contribs += repo.get_contributors()

    return unique_sort([c.login for c in contribs])


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
        login
    FROM (
        SELECT
            JSON_EXTRACT_SCALAR(payload, '$.member.login') AS login
        FROM
            `githubarchive.month.{YEARMONTH}`
        WHERE
            repo.name in ({repo_list})
            AND type = "MemberEvent" 
        GROUP BY
            login
        UNION ALL
        SELECT
            actor.login AS login
        FROM
            `githubarchive.month.{YEARMONTH}`
        WHERE
            repo.name in ({repo_list})
            AND type NOT IN ("WatchEvent", "ForkEvent", "MemberEvent")
        GROUP BY
            login )
    ORDER BY
    LOWER(login) ASC
    """
    print(f"PRI: {repo_list}, {YEARMONTH}")
    print(query)
    query_job = client.query(query)  # Make an API request.

    contribs = []
    for row in query_job:
        contribs.append(row[0])

    return contribs


def file_contributors(repos: str) -> List[str]:
    contribs = []
    for repo in repo_split(repos):
        print(f"FIL: {repo}")
        contribs += [c["user_name"] for c in contrib_file(repo)]
    return unique_sort(contribs)


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
