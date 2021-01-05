# A shorter CLI for quick searching
# Pulls API data one at a time
# Pulls BigQuery data in bulk
# Ignores file data (saves time for a file that probably doesn't exist) 

import logging
import click
from app import api_contributors, pri_contributors, app


@click.command()
@click.option("--repo", help="A repo to search")
@click.option("--repo-list", help="A newline delimited list of repos to check")
@click.option("--debug", default=False, is_flag=True)
def cli(repo, repo_list, debug):
    if debug:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)

    if repo:
        search_list = repo
    if repo_list:
        with open(repo_list) as f:
            search_list = ",".join(list(filter(None, f.read().split("\n"))))

    api = api_contributors(search_list)
    pri = pri_contributors(search_list)

    contribs = api + pri
    data = "\n".join([",".join(c) for c in contribs])
    print(data)


if __name__ == "__main__":
    cli()
