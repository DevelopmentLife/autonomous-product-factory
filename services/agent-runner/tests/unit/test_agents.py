import pytest
from apf_agent_runner.agents.prd import PRDAgent
from apf_agent_runner.agents.qa import QAAgent
from apf_agent_runner.agents.review import ReviewAgent
from apf_agent_runner.agents.base import PipelineContext


async def test_prd_agent_calls_llm(mock_llm, pipeline_context):
    agent = PRDAgent(mock_llm)
    result = await agent.execute(pipeline_context)
    mock_llm.complete.assert_called_once()
    assert result.raw_content != ''


async def test_prd_agent_returns_artifact(mock_llm, pipeline_context):
    agent = PRDAgent(mock_llm)
    result = await agent.execute(pipeline_context)
    assert result.agent_name == 'prd-agent'
    assert result.status == 'complete'


async def test_qa_agent_returns_artifact(mock_llm, pipeline_context):
    agent = QAAgent(mock_llm)
    result = await agent.execute(pipeline_context)
    assert result.agent_name == 'qa-agent'


async def test_review_agent_returns_artifact(mock_llm, pipeline_context):
    agent = ReviewAgent(mock_llm)
    result = await agent.execute(pipeline_context)
    assert result.agent_name == 'review-agent'


async def test_agent_uses_provided_model(mock_llm, pipeline_context):
    agent = PRDAgent(mock_llm, config={'model': 'gpt-4o'})
    await agent.execute(pipeline_context)
    call_kwargs = mock_llm.complete.call_args
    assert 'gpt-4o' in str(call_kwargs)


async def test_all_agents_can_execute(mock_llm, pipeline_context):
    from apf_agent_runner.agents.architect import ArchitectAgent
    from apf_agent_runner.agents.market import MarketAgent
    from apf_agent_runner.agents.ux import UXAgent
    from apf_agent_runner.agents.engineering import EngineeringAgent
    from apf_agent_runner.agents.developer import DeveloperAgent
    from apf_agent_runner.agents.regression import RegressionAgent
    from apf_agent_runner.agents.devops import DevOpsAgent
    from apf_agent_runner.agents.readme import ReadmeAgent

    for AgentClass in [ArchitectAgent, MarketAgent, UXAgent, EngineeringAgent,
                       DeveloperAgent, RegressionAgent, DevOpsAgent, ReadmeAgent]:
        mock_llm.complete.reset_mock()
        agent = AgentClass(mock_llm)
        result = await agent.execute(pipeline_context)
        assert result.status == 'complete'
