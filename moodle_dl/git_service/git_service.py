import git

class git_service:
    def __init__(self, courses, storage_path: str):
        self.storage_path = storage_path
        for course in courses:
            try:
                repo = git.Repo(course.fullname)
            except git.exc.InvalidGitRepositoryError:
                self.init_git(self, course)
                repo = git.Repo(course.fullname)


    def init_git(self, course):
        git.Repo.init(course.fullname, mkdir=True)


    def add_file_to_git(self, course, path, file):
        repo = git.Repo(course.fullname)
        repo.index.add(path)

    def commit_all_changes(self, courses):
        for course in courses:
            repo = git.Repo(course.fullname)
            repo.index.commit()
