import os

import git

import datetime


class git_service:
    def __init__(self, courses, storage_path: str):
        self.storage_path = storage_path
        for course in courses:
            try:
                repo = git.Repo(course.fullname)
            except git.exc.InvalidGitRepositoryError:
                self.init_git(course)
                repo = git.Repo(course.fullname)

    def startgit(self, courses, storage_path):
        self.storage_path = storage_path
        for course in courses:
            try:
                repo = git.Repo(course.fullname)
            except git.exc.InvalidGitRepositoryError:
                self.init_git(self, course)
                repo = git.Repo(course.fullname)

    def init_git(self, course):
        git.Repo.init(course.fullname, mkdir=True)
    def add_all_files_to_git(self, courses):
        for course in courses:
            repo = git.Repo(course.fullname)
            repo.index.add(repo.untracked_files)
    def add_file_to_git(self, course, path, file=None):
        try:
            repo = git.Repo(course.fullname)
        except git.exc.InvalidGitRepositoryError:
            self.init_git(course)
            repo = git.Repo(course.fullname)
        repo.index.add(path)

    def commit_all_changes(self, courses):
        for course in courses:
            repo = git.Repo(course.fullname)
            repo.index.commit(datetime.datetime.now().strftime("%c"))
