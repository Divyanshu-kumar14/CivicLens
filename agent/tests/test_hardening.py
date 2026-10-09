"""Tests for Task 3.1 additions: metrics publisher + TTL cache."""
from agent.services.cache import TTLCache, get_cache
from agent.services.metrics import MetricsPublisher


class FakeCW:
    def __init__(self):
        self.datapoints = []

    def put_metric_data(self, Namespace, MetricData):
        self.datapoints.extend(MetricData)


def test_metrics_publish_and_job_set():
    cw = FakeCW()
    m = MetricsPublisher(client=cw)
    m.publish("fps", 8.5, "Count/Second", {"ward": "ward-12-demo"})
    m.job_completed({"raw": 100, "clusters": 12, "filed": 8, "review": 3},
                    duration_min=4.2, fps=8.5)
    names = [d["MetricName"] for d in cw.datapoints]
    assert names == ["fps", "fps", "job_duration_min", "dedup_ratio",
                     "tickets_filed", "tickets_pending"]
    assert cw.datapoints[3]["Value"] == 100 / 12


def test_metrics_disabled_is_silent():
    m = MetricsPublisher(client=FakeCW(), enabled=False)
    m.publish("fps", 1.0)  # must not raise, must not emit


def test_metrics_backend_failure_swallowed():
    class Boom:
        def put_metric_data(self, **kw):
            raise RuntimeError("cloudwatch down")

    MetricsPublisher(client=Boom()).publish("fps", 1.0)  # no raise


def test_cache_hit_expiry_and_clear():
    c = TTLCache(default_ttl_s=100)
    assert c.get("k") is None
    c.set("k", [1, 2, 3])
    assert c.get("k") == [1, 2, 3]
    c.set("old", 1, ttl_s=-1)  # already expired
    assert c.get("old") is None
    c.clear()
    assert c.get("k") is None
    assert isinstance(get_cache(), TTLCache)


def test_query_tickets_projection_passed_through():
    import sys
    import types

    boto3_stub = types.ModuleType("boto3")
    dynamodb_stub = types.ModuleType("boto3.dynamodb")
    conditions_stub = types.ModuleType("boto3.dynamodb.conditions")

    class Key:
        def __init__(self, name):
            self.name = name

        def eq(self, value):
            return (self.name, value)

    conditions_stub.Key = Key
    dynamodb_stub.conditions = conditions_stub
    boto3_stub.dynamodb = dynamodb_stub
    sys.modules["boto3"] = boto3_stub
    sys.modules["boto3.dynamodb"] = dynamodb_stub
    sys.modules["boto3.dynamodb.conditions"] = conditions_stub
    try:
        seen = {}

        class FakeTable:
            def query(self, **kw):
                seen.update(kw)
                return {"Items": []}

            def scan(self, **kw):
                seen.update(kw)
                return {"Items": []}

        from agent.db.dynamo import DynamoClient

        client = DynamoClient.__new__(DynamoClient)  # no real boto3 needed
        client._dynamo = types.SimpleNamespace(Table=lambda name: FakeTable())
        client.t_tickets = "t"
        client.query_tickets(status="filed", projection="ticket_id,severity")
    finally:
        for mod in ("boto3", "boto3.dynamodb", "boto3.dynamodb.conditions"):
            sys.modules.pop(mod, None)
    assert seen.get("ProjectionExpression") == "ticket_id,severity"
    assert seen.get("IndexName") == "status-severity-index"
