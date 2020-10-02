import logging
import threading

from queue import Queue, Empty

from moodle_dl.state_recorder.state_recorder import StateRecorder


class Downloader(threading.Thread):
    """
    Downloader processes the queue and puts an
    URL target back into the queue if an error occurs.
    """

    def __init__(
        self,
        queue: Queue,
        report: [],
        state_recorder: StateRecorder,
        thread_id: int,
        db_lock: threading.Lock,
    ):
        """
        Initiates a downloader thread.
        """
        threading.Thread.__init__(self)
        self.daemon = True

        self.queue = queue
        self.report = report
        self.thread_id = thread_id
        self.db_lock = db_lock
        self.state_recorder = state_recorder

    def run(self):
        """
        Work the queue until it is empty.
        """
        logging.debug('T%s - Downloader thread was started', self.thread_id)
        while self.queue.empty() is False:
            try:
                # raise condition
                url_target = self.queue.get(False)
            except Empty:
                break

            response = url_target.download(self.thread_id)

            # All information is still saved in url_target

            # If a download fails, add it to the error report.
            if response is False:
                logging.debug('T%s - URLTarget reports failure!', self.thread_id)
                self.report['failure'].append(url_target)

            # If a download was successful, store it in the database.
            elif response is True:
                logging.debug('T%s - URLTarget reports success!', self.thread_id)
                self.db_lock.acquire()
                self.state_recorder.save_file(url_target.file, url_target.course.id, url_target.course.fullname)
                self.db_lock.release()
                self.report['success'].append(url_target)

            self.queue.task_done()

        logging.debug('T%s - Downloader thread is finished', self.thread_id)
