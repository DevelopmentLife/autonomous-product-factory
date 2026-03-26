from __future__ import annotations
import httpx


async def post_message(token: str, channel: str, text: str, blocks: list | None = None) -> dict:
    payload = {'channel': channel, 'text': text}
    if blocks:
        payload['blocks'] = blocks
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {token}'},
            json=payload,
        )
        return resp.json()


def stage_started_blocks(pipeline_id: str, stage_name: str) -> list:
    return [{'type': 'section', 'text': {'type': 'mrkdwn',
             'text': f':rocket: *Stage Started:* {stage_name} | Pipeline: {pipeline_id[:8]}'}}]


def stage_complete_blocks(pipeline_id: str, stage_name: str) -> list:
    return [{'type': 'section', 'text': {'type': 'mrkdwn',
             'text': f':white_check_mark: *Stage Complete:* {stage_name} | Pipeline: {pipeline_id[:8]}'}}]


def pipeline_complete_blocks(pipeline_id: str, pr_url: str = '') -> list:
    text = f':tada: *Pipeline Complete!* | {pipeline_id[:8]}'
    if pr_url:
        text += f' | <{pr_url}|View PR>'
    return [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}]


def approval_required_blocks(pipeline_id: str, stage_name: str) -> list:
    return [
        {'type': 'section', 'text': {'type': 'mrkdwn',
          'text': f':hourglass: *Approval Required:* {stage_name} | {pipeline_id[:8]}'}},
        {'type': 'actions', 'elements': [
            {'type': 'button', 'text': {'type': 'plain_text', 'text': 'Approve'},
             'style': 'primary', 'action_id': 'approve_stage',
             'value': f'{pipeline_id}:{stage_name}'},
            {'type': 'button', 'text': {'type': 'plain_text', 'text': 'Reject'},
             'style': 'danger', 'action_id': 'reject_stage',
             'value': f'{pipeline_id}:{stage_name}'},
        ]},
    ]
