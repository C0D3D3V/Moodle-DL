import git

class git_service:
    repoindex = []
    courses = []
    def __init__(self, courses):
        for course in courses:
            try:
                repo = git.Repo(course.fullname)
            except git.exc.InvalidGitRepositoryError:
                self.init_git(self, course)
                repo = git.Repo(course.fullname)
            self.repoindex.append(repo)
            self.courses.append(course)

    def init_git(self, course):
        git.Repo.init(course.fullname, mkdir=True)


    def add_file_to_git(course, path, file):

