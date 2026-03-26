import pytest
from unittest.mock import AsyncMock
from apf_agent_runner.agents.base import PipelineContext, BaseArtifact


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value='{"executive_summary":"Mock","target_users":[],"core_features":[],"success_metrics":[],"out_of_scope":[],"risks":[],"competitors":[],"user_personas":[],"milestones":[],"phases":[],"test_strategy":"","coverage_targets":{},"approval":"approved","verdict":"approved","comments":[],"blockers":[],"infrastructure":[],"services":[],"deployment_steps":[],"summary":"Mock"}')
    return llm


@pytest.fixture
def pipeline_context():
    return PipelineContext(run_id='run-1', idea='Build a todo app')
