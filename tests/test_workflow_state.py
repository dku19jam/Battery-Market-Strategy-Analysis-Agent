import unittest


class WorkflowStateTest(unittest.TestCase):
    def test_workflow_state_tracks_lane_and_reproducibility_data(self) -> None:
        from battery_agent.models.run_context import RunContext
        from battery_agent.pipeline.workflow_state import LaneState, WorkflowState

        state = WorkflowState(
            run_context=RunContext(run_id="run-001", topic="topic", output_dir="artifacts/run-001"),
            model_name="gpt-4o-mini",
            corpus_fingerprint="abc123",
            search_params={"web_search": False},
            lg_lane=LaneState(company="LG에너지솔루션"),
            catl_lane=LaneState(company="CATL"),
        )

        self.assertEqual(state.model_name, "gpt-4o-mini")
        self.assertEqual(state.corpus_fingerprint, "abc123")
        self.assertEqual(state.status, "initialized")
