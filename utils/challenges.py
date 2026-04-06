class Challenge:
    """
    Base class for all challenges.
    """
    name = "Unnamed Challenge"
    description = "No description"

    def __init__(self, runner_id, runs):
        """
        runner_id: int
        runs: list of run dicts (or rows from DB)
        """
        self.runner_id = runner_id
        self.runs = runs

    def is_completed(self):
        """
        Returns True/False if the challenge is completed.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

class ClockChallenge(Challenge):
    name = "Clock Challenge"
    description = "Have a run for each second from 00 to 59"

    def is_completed(self):
        seconds_seen = set()
        for run in self.runs:
            # assuming run['time_seconds'] is an int
            seconds_seen.add(run['time_seconds'] % 60)
        return len(seconds_seen) == 60
