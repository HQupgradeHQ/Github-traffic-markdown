from dataclasses import dataclass
from collections import defaultdict
from subprocess import run
import requests
import concurrent.futures


@dataclass
class GithubRepo:
    username: str
    repo: str

    @property
    def paths(self):
        return f"https://api.github.com/repos/{self.username}/{self.repo}/traffic/popular/paths"

    @property
    def views(self):
        return f"https://api.github.com/repos/{self.username}/{self.repo}/traffic/views"

    @property
    def clones(self):
        return (
            f"https://api.github.com/repos/{self.username}/{self.repo}/traffic/clones"
        )

    @staticmethod
    def extract_base_url(url):
        "extract repo name from *_base_url"
        t = url.rfind("traffic") - 1
        r = url.rfind("/", 0, t) + 1
        return url[r:t]


@dataclass
class GithubMarkdown:
    data: defaultdict

    def generate_paths_block(self, paths):
        if paths is None:
            return ""
        result = "**paths** <br/>\n"
        for p in paths:
            path = p["path"]
            result += f"`github.com{path}`: all = {p['count']}, unique = {p['uniques']}<br/>\n"
        return result

    def generate_clones_block(self, clones):
        if clones is None:
            return ""
        result = "**clones** <br/>\n"
        result += "| Day | all | unique |\n"
        result += "| --- | :---: | :---: |\n"
        for cl in clones["clones"]:
            result += f"| `{cl['timestamp'][:10]}` | {cl['count']} |{cl['uniques']} |\n"
        result += f"| `total` | {clones['count']} | {clones['uniques']} |\n"
        result += "\n"

        return result

    def generate_views_block(self, views):
        if views is None:
            return ""
        result = "**views** <br/>\n"
        result += "| Day | all | unique |\n"
        result += "| --- | :---: | :---: |\n"
        for v in views["views"]:
            result += f"| `{v['timestamp'][:10]}` | {v['count']} |{v['uniques']} |\n"
        result += f"| `total` | {views['count']} | {views['uniques']} |\n"
        result += "\n"

        return result

    def generate_page(self, order=[]):
        data = self.data.items()
        # rearrange order as it in target list https://stackoverflow.com/a/52044835
        if order:
            data = {k: self.data[k] for k in order}
            data = data.items()
        md_content = ""
        for repo, traffic in data:
            md_content += f"# {repo} <br/>\n" if traffic else ""
            views = self.generate_views_block(traffic.get("views", None))
            paths = self.generate_paths_block(traffic.get("paths", None))
            clones = self.generate_clones_block(traffic.get("clones", None))

            md_content += "".join([views, paths, clones])
        with open("traffic.md", "w") as f:
            f.write(md_content)


@dataclass
class Loader:
    api_key: str
    username: str
    repo_list: list

    def load_url(self, url):
        r = requests.get(url, headers={"Authorization": "token " + self.api_key})
        return r.json()

    def generate_urls(self):
        urls = []
        for r in self.repo_list:
            urls.append(GithubRepo(self.username, r).views)
            urls.append(GithubRepo(self.username, r).paths)
            urls.append(GithubRepo(self.username, r).clones)
        return urls

    def dispatch(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Start the load operations and mark each future with its URL
            future_to_url = {
                executor.submit(self.load_url, url): url for url in self.generate_urls()
            }
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                except Exception as exc:
                    print("%r generated an exception: %s" % (url, exc))
                else:
                    update_dict(url, data)


def update_dict(url, data):
    """populate dict, check if there is data"""
    current_repo = GithubRepo.extract_base_url(url)
    if "paths" in url and data:
        raw_dict[current_repo]["paths"] = data
    if "clones" in url and data["count"]:
        raw_dict[current_repo]["clones"] = data
    if "views" in url and data["count"]:
        raw_dict[current_repo]["views"] = data


raw_dict = defaultdict(dict)
token = "insert token here "  # with repo scope
u = "upgradeQ"
repos_u = [
    "osuplaylist",
    "Obscounter",
    "Daylight",
    "Awesome-keyboard-typing",
    "Github-traffic-markdown",
]
Loader(api_key=token, username=u, repo_list=repos_u).dispatch()
GithubMarkdown(raw_dict).generate_page(order=repos_u)
try:
    run("grip traffic.md -b")
except KeyboardInterrupt:
    pass
