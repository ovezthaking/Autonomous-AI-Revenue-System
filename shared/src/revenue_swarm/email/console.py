import logging

log = logging.getLogger(__name__)


class ConsoleEmail:
    def send(self, to: str, subject: str, body: str) -> None:
        log.info("email to=%s subject=%s", to, subject)
        log.info("%s", body)
