import threading
from queue import Queue
from utils.state_recorder import StateRecorder


class Downloader(threading.Thread):
    def __init__(self, queue: Queue, report: [],
                 state_recorder: StateRecorder,
                 thread_id: int,
                 lock: threading.Lock):
        threading.Thread.__init__(self)
        self.queue = queue
        self.report = report
        self.thread_id = thread_id
        self.lock = lock
        self.state_recorder = state_recorder

    def run(self):
        while self.queue.empty() is False:
            try:
                url_target = self.queue.get(False)
            except Queue.Empty:
                break

            response = url_target.download(self.thread_id)

            # information is still saved in url_target
            if (response is False and
                    url_target.url_tried < url_target.url_tries):
                self.queue.put(url_target)
            elif (response is False and
                  url_target.url_tried == url_target.url_tries):
                self.report['failure'].append(url_target)
            elif (response):
                self.lock.acquire()
                self.state_recorder.save_file(
                    url_target.file, url_target.course.id,
                    url_target.course.fullname)
                self.lock.release()
                self.report['success'].append(url_target)

            self.queue.task_done()
