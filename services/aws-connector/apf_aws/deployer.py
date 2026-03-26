import asyncio
import boto3
from typing import Any
from .config import Settings


class AWSDeployer:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            region_name=settings.AWS_DEFAULT_REGION,
        )

    def _ecs(self) -> Any:
        return self._session.client('ecs')

    def _ecr(self) -> Any:
        return self._session.client('ecr')

    async def deploy_service(
        self,
        task_definition: str | None = None,
        cluster: str | None = None,
        service: str | None = None,
    ) -> dict[str, Any]:
        td = task_definition or self._settings.AWS_ECS_TASK_DEFINITION
        cl = cluster or self._settings.AWS_ECS_CLUSTER
        svc = service or self._settings.AWS_ECS_SERVICE
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._ecs().update_service(
                cluster=cl,
                service=svc,
                taskDefinition=td,
                forceNewDeployment=True,
            ),
        )
        svc_info = response.get('service', {})
        return {
            'service_arn': svc_info.get('serviceArn', ''),
            'running_count': svc_info.get('runningCount', 0),
            'desired_count': svc_info.get('desiredCount', 0),
            'status': svc_info.get('status', 'UNKNOWN'),
        }

    async def get_deployment_status(
        self,
        cluster: str | None = None,
        service: str | None = None,
    ) -> dict[str, Any]:
        cl = cluster or self._settings.AWS_ECS_CLUSTER
        svc = service or self._settings.AWS_ECS_SERVICE
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._ecs().describe_services(cluster=cl, services=[svc]),
        )
        services = response.get('services', [])
        if not services:
            return {'status': 'NOT_FOUND'}
        s = services[0]
        deployments = s.get('deployments', [])
        primary = next((d for d in deployments if d.get('status') == 'PRIMARY'), {})
        return {
            'service_status': s.get('status', 'UNKNOWN'),
            'running_count': s.get('runningCount', 0),
            'desired_count': s.get('desiredCount', 0),
            'pending_count': s.get('pendingCount', 0),
            'deployment_status': primary.get('rolloutState', 'UNKNOWN'),
        }
