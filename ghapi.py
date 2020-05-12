import requests
import concurrent.futures
from collections import defaultdict
from subprocess import run


def paths_base_url(user, repo):
    return f"https://api.github.com/repos/{user}/{repo}/traffic/popular/paths"


def views_base_url(user, repo):
    return f"https://api.github.com/repos/{user}/{repo}/traffic/views"


def clones_base_url(user, repo):
    return f"https://api.github.com/repos/{user}/{repo}/traffic/clones"


def extract_base_url(url):
    "extract repo name from *_base_url"
    t = url.rfind("traffic") - 1
    r = url.rfind("/", 0, t) + 1
    return url[r:t]


def load_url(url):
    r = requests.get(url, headers=headers)
    return r.json()


def clean_paths(data):
    result = "**paths** :open_file_folder:<br/>\n"
    for p in data:
        path = p["path"]
        result += (
            f"`github.com{path}`: all = {p['count']}, unique = {p['uniques']}<br/>\n"
        )
    return result


def clean_clones(data):
    result = ""
    if data["count"]:
        result += "**clones** :octocat: :octocat:<br/>\n"
        result += "| Day | all | unique |\n"
        result += "| --- | :---: | :---: |\n"
        for cl in data["clones"]:
            result += f"| `{cl['timestamp'][:10]}` | {cl['count']} |{cl['uniques']} |\n"
        result += f"| `total` | {data['count']} | {data['uniques']} |\n"
        result += "\n"

    return result


def clean_views(data):
    result = ""
    if data["count"]:
        result = "**views** :eyes:<br/>\n"
        result += "| Day | all | unique |\n"
        result += "| --- | :---: | :---: |\n"
        for v in data["views"]:
            result += f"| `{v['timestamp'][:10]}` | {v['count']} |{v['uniques']} |\n"
        result += f"| `total` | {data['count']} | {data['uniques']} |\n"
        result += "\n"

    return result


def update_dict(url, data):
    """populate dict, check if there is data"""
    current_repo = extract_base_url(url)
    if "paths" in url and data:
        checked_paths = clean_paths(data)
        if checked_paths:
            u_dict[current_repo]["paths"] = checked_paths
    if "clones" in url and data:
        checked_clones = clean_clones(data)
        if checked_clones:
            u_dict[current_repo]["clones"] = checked_clones
    if "views" in url and data:
        checked_views = clean_views(data)
        if checked_views:
            u_dict[current_repo]["views"] = checked_views


def get_stats(urls):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Start the load operations and mark each future with its URL
        future_to_url = {executor.submit(load_url, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
            except Exception as exc:
                print("%r generated an exception: %s" % (url, exc))
            else:
                update_dict(url, data)


def generate_md(u_dict):
    md_content = ""
    for repo, traffic in u_dict.items():
        md_content += f"# {repo} <br/>\n"
        for _, part in traffic.items():
            md_content += part
    return md_content


token = ""  # with repo scope
headers = {"Authorization": "token " + token}
u = ""  # username
repos_u = []  # repos
# d = "" # also works with organization
# repos_d = [] # org's repos
u_dict = defaultdict(dict)  # everything from get_stats will appear here
u_urls = []
for repo in repos_u:
    u_urls.append(paths_base_url(u, repo))
    u_urls.append(views_base_url(u, repo))
    u_urls.append(clones_base_url(u, repo))
# d_urls = []
# for repo in repos_d:
#    d_urls.append(paths_base_url(d, repo))
#    d_urls.append(views_base_url(d, repo))
#    d_urls.append(clones_base_url(d, repo))
# get_stats(urls=d_urls)
get_stats(urls=u_urls)

with open("traffic.md", "w") as f:
    f.write(generate_md(u_dict))
try:
    run("grip traffic.md -b") # open browser
except KeyboardInterrupt:
    pass
