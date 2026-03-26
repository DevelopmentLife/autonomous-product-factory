import pytest
from apf_orchestrator.core.dag import PipelineDAG, STAGE_DEPS


def test_prd_stage_has_no_deps():
    assert STAGE_DEPS['prd'] == []


def test_architect_requires_prd():
    assert 'prd' in STAGE_DEPS['architect']


def test_engineering_requires_three_stages():
    deps = STAGE_DEPS['engineering']
    assert 'architect' in deps and 'market' in deps and 'ux' in deps


def test_get_ready_stages_returns_prd_on_empty():
    dag = PipelineDAG()
    ready = dag.get_ready_stages(set(), set(), set())
    assert 'prd' in ready


def test_get_ready_stages_after_prd_done():
    dag = PipelineDAG()
    ready = dag.get_ready_stages({'prd'}, set(), set())
    assert 'architect' in ready and 'market' in ready and 'ux' in ready
    assert 'prd' not in ready


def test_get_ready_stages_returns_engineering_when_all_prereqs_done():
    dag = PipelineDAG()
    ready = dag.get_ready_stages({'prd', 'architect', 'market', 'ux'}, set(), set())
    assert 'engineering' in ready


def test_get_ready_stages_excludes_running():
    dag = PipelineDAG()
    ready = dag.get_ready_stages(set(), {'prd'}, set())
    assert 'prd' not in ready


def test_qa_gate_passes_no_bugs():
    dag = PipelineDAG()
    result = dag.validate_qa_gate({'critical_bug_count': 0, 'high_bug_count': 0})
    assert result.passed is True


def test_qa_gate_fails_critical_bug():
    dag = PipelineDAG()
    result = dag.validate_qa_gate({'critical_bug_count': 1, 'high_bug_count': 0})
    assert result.passed is False
    assert 'critical' in result.reason


def test_qa_gate_fails_high_bug():
    dag = PipelineDAG()
    result = dag.validate_qa_gate({'critical_bug_count': 0, 'high_bug_count': 2})
    assert result.passed is False


def test_needs_regression_true_with_bugs():
    dag = PipelineDAG()
    assert dag.needs_regression({'bugs': [{'id': 'BUG-1'}]}) is True


def test_needs_regression_false_no_bugs():
    dag = PipelineDAG()
    assert dag.needs_regression({'bugs': []}) is False
