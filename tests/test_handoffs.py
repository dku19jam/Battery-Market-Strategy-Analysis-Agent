import unittest


class HandoffTest(unittest.TestCase):
    def test_handoff_rules_choose_comparison_and_report_generation(self) -> None:
        from battery_agent.pipeline.handoffs import next_stage_after_lanes, next_stage_after_references
        from battery_agent.pipeline.workflow_state import LaneState

        lg_lane = LaneState(company="LG에너지솔루션", status="completed")
        catl_lane = LaneState(company="CATL", status="completed")

        self.assertEqual(next_stage_after_lanes(lg_lane, catl_lane), "comparison")
        self.assertEqual(next_stage_after_references(True), "report_generation")
