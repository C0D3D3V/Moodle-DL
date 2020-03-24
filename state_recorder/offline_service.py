import os

from pathlib import Path
from state_recorder.state_recorder import StateRecorder


class OfflineService:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.state_recorder = StateRecorder(
            Path(storage_path) / 'moodle_state.db')

    def interactively_manage_database(self):
        stored_files = self.state_recorder.get_stored_files()

        for course in stored_files:
            for file in course.files:
                if(not os.path.exists(file.saved_to)):
                    print(file)
