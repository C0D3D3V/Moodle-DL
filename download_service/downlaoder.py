import threading

from queue import Queue

from utils.state_recorder import StateRecorder


class Downloader(threading.Thread):
    """
    Downlaoder processes the queue and puts an
    url target back into the queue if an error occurs.
    """

    def __init__(self, queue: Queue, report: [],
                 state_recorder: StateRecorder,
                 thread_id: int,
                 lock: threading.Lock):
        """
        Initiates a downloader thread.
        """
        threading.Thread.__init__(self)

        self.queue = queue
        self.report = report
        self.thread_id = thread_id
        self.lock = lock
        self.state_recorder = state_recorder

    def run(self):
        """
        Work the queue until it is empty.
        """
        while self.queue.empty() is False:
            try:
                # raise condition
                url_target = self.queue.get(False)
            except Queue.Empty:
                break

            response = url_target.download(self.thread_id)

            # All information is still saved in url_target

            # If a download fails but the maximum number of
            # attempts is not reached, the url target would
            # be returned to the queue
            if (response is False and
                    url_target.url_tried < url_target.url_tries):
                self.queue.put(url_target)

            # If a download fails but the maximum number of
            # attempts is exhausted, add it to the error report.
            elif (response is False and
                  url_target.url_tried == url_target.url_tries):
                self.report['failure'].append(url_target)

            # If a download was successful, store it in the database.
            elif (response):
                self.lock.acquire()
                self.state_recorder.save_file(
                    url_target.file, url_target.course.id,
                    url_target.course.fullname)
                self.lock.release()
                self.report['success'].append(url_target)

            self.queue.task_done()
