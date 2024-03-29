import logging
import re

from prowjobsscraper import event, prowjob, step

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(
        self, event_store: event.EventStoreElastic, step_extractor: step.StepExtractor
    ):
        self._event_store = event_store
        self._step_extractor = step_extractor

    def execute(self, jobs: prowjob.ProwJobs):
        logger.info("%s jobs will be processed", len(jobs.items))

        # filter out non-assisted jobs
        jobs.items = [j for j in jobs.items if self._is_assisted_job(j)]

        # filter out jobs already stored
        known_build_ids = self._event_store.scan_build_ids()
        jobs.items = [j for j in jobs.items if j.status.build_id not in known_build_ids]

        # Retrieve executed for each jobs
        steps = self._step_extractor.parse_prow_jobs(jobs)

        # Store jobs and steps into their respective indices
        logger.info("%s jobs will be pushed to ES", len(jobs.items))
        self._event_store.index_prow_jobs(jobs.items)

        logger.info("%s steps will be pushed to ES", {len(steps)})
        self._event_store.index_job_steps(steps)

    @staticmethod
    def _is_assisted_job(j: prowjob.ProwJob) -> bool:
        if j.status.state not in ("success", "failure"):
            return False
        elif not re.search("e2e-.*-assisted", j.spec.job):
            return False
        elif j.status.description and "Overridden" in j.status.description:
            # exclude overridden builds
            # the url points to github instead of prow
            return False

        return True
