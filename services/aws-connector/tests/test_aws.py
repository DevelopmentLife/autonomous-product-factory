import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture()
def settings():
    from apf_aws.config import Settings
    return Settings(
        AWS_ACCESS_KEY_ID='AKIATEST',
        AWS_SECRET_ACCESS_KEY='secret',
        AWS_DEFAULT_REGION='us-east-1',
        AWS_ECS_CLUSTER='apf-cluster',
        AWS_ECS_SERVICE='apf-service',
        AWS_ECS_TASK_DEFINITION='apf-task:1',
    )


@pytest.mark.asyncio
async def test_deploy_service(settings):
    from apf_aws.deployer import AWSDeployer
    deployer = AWSDeployer(settings)
    mock_ecs = MagicMock()
    mock_ecs.update_service.return_value = {
        'service': {
            'serviceArn': 'arn:aws:ecs:us-east-1:123:service/apf-service',
            'runningCount': 1,
            'desiredCount': 1,
            'status': 'ACTIVE',
        }
    }
    with patch.object(deployer, '_ecs', return_value=mock_ecs):
        result = await deployer.deploy_service()
    assert result['status'] == 'ACTIVE'
    assert result['running_count'] == 1


@pytest.mark.asyncio
async def test_get_deployment_status(settings):
    from apf_aws.deployer import AWSDeployer
    deployer = AWSDeployer(settings)
    mock_ecs = MagicMock()
    mock_ecs.describe_services.return_value = {
        'services': [{
            'status': 'ACTIVE',
            'runningCount': 2,
            'desiredCount': 2,
            'pendingCount': 0,
            'deployments': [{'status': 'PRIMARY', 'rolloutState': 'COMPLETED'}],
        }]
    }
    with patch.object(deployer, '_ecs', return_value=mock_ecs):
        result = await deployer.get_deployment_status()
    assert result['deployment_status'] == 'COMPLETED'


def test_health():
    from fastapi.testclient import TestClient
    from apf_aws.main import app
    client = TestClient(app)
    assert client.get('/healthz').json() == {'status': 'ok'}


def test_deploy_no_config():
    from fastapi.testclient import TestClient
    from apf_aws.config import Settings
    empty_settings = Settings(AWS_ECS_CLUSTER='')
    with patch('apf_aws.main.get_settings', return_value=empty_settings):
        from apf_aws.main import app
        client = TestClient(app)
        resp = client.post('/deploy', json={'pipeline_id': 'p1'})
    assert resp.status_code == 503
