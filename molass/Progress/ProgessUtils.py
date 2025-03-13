"""
    Progress.ProgressUtils.py

"""
import logging
import queue

class ProgressUnit:
    def __init__(self, id_, num_steps, queue_, logger):
        self.id_ = id_
        self.num_steps = num_steps
        self.num_done = 0
        self.queue_ = queue_
        self.logger = logger

    def __len__(self):
        return self.num_steps

    def step_done(self):
        if self.num_done < self.num_steps:
            self.num_done += 1
            self.queue_.put((self.id_, self.num_done, self.num_done==self.num_steps))
        else:
            self.logger.warning("excessive step_done call!")

    def all_done(self):
        if self.num_done < self.num_steps:
            self.logger.warning("premature all_done call!")
        self.num_done = self.num_steps
        self.queue_.put((self.id_, self.num_done, self.num_done==self.num_steps))

class ProgressSet:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.num_units = 0
        self.num_steps = 0
        self.unit_status = {}
        self.completed_units = 0
        self.queue_ = queue.Queue()

    def add_unit(self, num_steps):
        self.num_steps += num_steps
        self.num_units += 1
        id_ = self.num_units
        self.unit_status[id_] = False
        return ProgressUnit(id_, num_steps, self.queue_, self.logger)
    
    def __len__(self):
        # this helps tqdm get the total number
        return self.num_steps

    def __iter__(self):
        while True:
            try:
                ret = self.queue_.get(timeout=60)
                id_, step, done = ret
                if done:
                    self.unit_status[id_] = True
                    self.completed_units += 1
                    if self.completed_units == self.num_units:
                        break
                yield ret
            except queue.Empty:
                self.logger.error("Progress queue timeout!")
                break
