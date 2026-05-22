import pytest
from src.orchestrator.workflow import Workflow, WorkflowStep, WorkflowManager, StepStatus


class TestWorkflow:
    def test_add_step_case_insensitive_duplicate(self):
        wf = Workflow("test-wf")
        step1 = WorkflowStep("StepA", lambda: "A")
        wf.add_step(step1)

        # Registering exact duplicate
        step2 = WorkflowStep("StepA", lambda: "A2")
        with pytest.raises(ValueError) as exc:
            wf.add_step(step2)
        assert "already exists" in str(exc.value)

        # Registering case-insensitive duplicate
        step3 = WorkflowStep("stepa", lambda: "a")
        with pytest.raises(ValueError) as exc:
            wf.add_step(step3)
        assert "case-insensitive conflict" in str(exc.value)

    def test_exact_case_sensitive_dependency_match(self):
        wf = Workflow("test-wf")
        step_a = WorkflowStep("StepA", lambda: "A")
        step_b = WorkflowStep("StepB", lambda: "B", depends_on=["StepA"])
        wf.add_step(step_a).add_step(step_b)

        # Validation should succeed
        ordered = wf.validate()
        assert len(ordered) == 2
        assert ordered[0].name == "StepA"
        assert ordered[1].name == "StepB"

    def test_case_mismatch_dependency_raises(self):
        wf = Workflow("test-wf")
        step_a = WorkflowStep("StepA", lambda: "A")
        # StepB depends on "stepa" (lowercase), but registered step is "StepA"
        step_b = WorkflowStep("StepB", lambda: "B", depends_on=["stepa"])
        wf.add_step(step_a).add_step(step_b)

        with pytest.raises(ValueError) as exc:
            wf.validate()
        assert "has case mismatch with registered step" in str(exc.value)

    def test_missing_dependency_raises(self):
        wf = Workflow("test-wf")
        step_b = WorkflowStep("StepB", lambda: "B", depends_on=["Nonexistent"])
        wf.add_step(step_b)

        with pytest.raises(ValueError) as exc:
            wf.validate()
        assert "not found" in str(exc.value)

    def test_circular_dependency_raises(self):
        wf = Workflow("test-wf")
        step_a = WorkflowStep("StepA", lambda: "A", depends_on=["StepB"])
        step_b = WorkflowStep("StepB", lambda: "B", depends_on=["StepA"])
        wf.add_step(step_a).add_step(step_b)

        with pytest.raises(ValueError) as exc:
            wf.validate()
        assert "Circular dependency detected" in str(exc.value)

    def test_topological_execution_order(self):
        manager = WorkflowManager()
        wf = manager.create_workflow("test-wf")

        execution_order = []

        step_c = WorkflowStep("StepC", lambda: execution_order.append("C"), depends_on=["StepB"])
        step_b = WorkflowStep("StepB", lambda: execution_order.append("B"), depends_on=["StepA"])
        step_a = WorkflowStep("StepA", lambda: execution_order.append("A"))

        # Add them in reverse order C, B, A
        wf.add_step(step_c).add_step(step_b).add_step(step_a)

        success = manager.execute_workflow(wf.id)
        assert success
        assert wf.status == StepStatus.COMPLETED
        assert execution_order == ["A", "B", "C"]
