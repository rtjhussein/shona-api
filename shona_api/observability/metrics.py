import logging


logger = logging.getLogger(__name__)


def record_metric(name, value=1, tags=None):
    metric = {
        "name": name,
        "value": value,
        "tags": tags or {},
    }
    logger.debug("metric_recorded", extra={"metric": metric})
    return metric
