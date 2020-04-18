import os

from pathlib import Path
from utils import cutie
from state_recorder.state_recorder import StateRecorder


class OfflineService:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.state_recorder = StateRecorder(
            Path(storage_path) / 'moodle_state.db')

    def interactively_manage_database(self):
        RESET_SEQ = "\033[0m"
        COLOR_SEQ = "\033[1;%dm"

        BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

        stored_files = self.state_recorder.get_stored_files()

        choices = []
        caption_indices = []
        index = 0
        for course in stored_files:
            course_appended = False
            for file in course.files:
                if(not os.path.exists(file.saved_to)):
                    if(not course_appended):
                        choices.append(COLOR_SEQ %
                                       BLUE + course.fullname + RESET_SEQ)
                        caption_indices.append(index)
                        index += 1
                        course_appended = True

                    choices.append(COLOR_SEQ % MAGENTA + file.section_name + RESET_SEQ +
                                   "\t" + COLOR_SEQ % MAGENTA + file.content_filename + RESET_SEQ)
                    index += 1

        print('Which of the files should be removed form the database, so that they will be redownloaded?')
        print('[You can select with the space bar and confirm' +
              ' your selection with the enter key]')
        print('')
        selected_files = cutie.select_multiple(
            options=choices, caption_indices=caption_indices)

        print(selected_files)
