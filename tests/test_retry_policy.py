import unittest


class RetryPolicyTest(unittest.TestCase):
    def test_retry_policy_limits_attempts_and_partial_report_threshold(self) -> None:
        from battery_agent.pipeline.retry_policy import RetryPolicy

        policy = RetryPolicy(max_local_retries=2, max_query_rewrites=1, max_web_retries=1)

        self.assertTrue(policy.should_retry("local", 1))
        self.assertFalse(policy.should_retry("local", 2))
        self.assertTrue(policy.should_emit_partial_report(missing_core_inputs=True))
