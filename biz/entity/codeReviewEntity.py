class MergeEntity:
    def __init__(self, project_name: str, author: str, source_branch: str, target_branch: str, updated_at: int,
                 commits: list, score: float, url: str, review_result: str, url_slug: str):
        self.project_name = project_name
        self.author = author
        self.source_branch = source_branch
        self.target_branch = target_branch
        self.updated_at = updated_at
        self.commits = commits
        self.score = score
        self.url = url
        self.review_result = review_result
        self.url_slug = url_slug

    @property
    def commit_messages(self):
        return "; ".join(commit["message"].strip() for commit in self.commits)


class PushEntity:
    def __init__(self, project_name: str, author: str, branch: str, updated_at: int, commits: list, score: float,
                 review_result: str, url_slug: str):
        self.project_name = project_name
        self.author = author
        self.branch = branch
        self.updated_at = updated_at
        self.commits = commits
        self.score = score
        self.review_result = review_result
        self.url_slug = url_slug

    @property
    def commit_messages(self):
        return "; ".join(commit["message"].strip() for commit in self.commits)

