import os

import git

import datetime

import moodle_dl.download_service.download_service as dl

class git_service:
    def __init__(self, courses, storage_path: str):
        self.storage_path = storage_path
        for course in courses:
            folder = dl.DownloadService.get_folder(course)
            try:
                repo = git.Repo(folder)
            except git.exc.InvalidGitRepositoryError:
                self.init_git(course)
                repo = git.Repo(folder)

    def startgit(self, courses, storage_path):
        self.storage_path = storage_path
        for course in courses:
            try:
                repo = git.Repo(course.fullname)
            except git.exc.InvalidGitRepositoryError:
                self.init_git(self, course)
                repo = git.Repo(course.fullname)
    @staticmethod
    def init_git(course):
        folder = dl.DownloadService.get_folder(course)
        git.Repo.init(folder, mkdir=True)
    def add_all_files_to_git(self, courses):
        for course in courses:
            folder = dl.DownloadService.get_folder(course)
            repo = git.Repo(folder)
            repo.index.add(repo.untracked_files)
    @staticmethod
    def add_file_to_git(course, path, file=None):
        folder = dl.DownloadService.get_folder(course)
        try:
            repo = git.Repo(folder)
        except git.exc.InvalidGitRepositoryError:
            git_service.init_git(course)
            repo = git.Repo(folder)
        repo.index.add(path)

    def commit_all_changes(self, courses):
        for course in courses:
            repo = git.Repo(dl.DownloadService.get_folder(course))
            repo.index.commit(datetime.datetime.now().strftime("%c"))
