"""
    Progress.ProgressUtils.py

"""
import logging
import queue

class ProgressUnit:
    """    A unit of progress tracking.
    This class represents a single unit of progress that can be tracked.
    It allows for tracking the number of steps completed and provides methods to mark steps as done.
    Attributes:
        id_ (int): Unique identifier for the progress unit.
        num_steps (int): Total number of steps in this unit.
        num_done (int): Number of steps completed.
        queue_ (queue.Queue): Queue to send progress updates.
        logger (logging.Logger): Logger for logging progress updates.
    """
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

    def tell_error(self):
        """
        Returns the current progress as a tuple of (id, num_done, False).
        """
        self.queue_.put((self.id_, self.num_done, False))
class ProgressSet:
    """    A set of progress units to track the progress of multiple tasks.
    This class is used to manage multiple progress units and provide a unified interface for tracking their progress.
    It allows adding new units, checking their status, and iterating over them.
    Attributes:
        num_units (int): Total number of progress units.
        num_steps (int): Total number of steps across all units.
        unit_status (dict): Dictionary to track the status of each unit.
        completed_units (int): Number of completed units.
        queue_ (queue.Queue): Queue to manage progress updates.
    """
    def __init__(self, timeout=60):
        self.logger = logging.getLogger(__name__)
        self.num_units = 0
        self.num_steps = 0
        self.unit_status = {}
        self.completed_units = 0
        self.queue_ = queue.Queue()
        self.timeout = timeout
        self.logger.info('ProgressSet initialized with timeout=%s', self.timeout)
        
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
                ret = self.queue_.get(timeout=self.timeout)
                id_, step, done = ret
                if done:
                    self.unit_status[id_] = True
                    self.completed_units += 1
                    if self.completed_units == self.num_units:
                        break
                else:
                    # error in progress
                    self.logger.error(f"Progress unit {id_} reported error at step {step}.")
                    self.unit_status[id_] = False
                    break
                yield ret
            except queue.Empty:
                self.logger.error("Progress queue timeout!")
                break
