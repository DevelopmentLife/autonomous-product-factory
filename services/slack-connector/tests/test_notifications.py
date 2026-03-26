import pytest
from apf_slack.notifications import (
    stage_started_blocks, stage_complete_blocks,
    pipeline_complete_blocks, approval_required_blocks,
)


def test_stage_started_blocks_contains_stage_name():
    blocks = stage_started_blocks('pipe-abc-123', 'prd')
    text = str(blocks)
    assert 'prd' in text


def test_stage_complete_blocks_not_empty():
    blocks = stage_complete_blocks('pipe-1', 'architect')
    assert len(blocks) > 0


def test_pipeline_complete_includes_pr_url():
    blocks = pipeline_complete_blocks('pipe-1', pr_url='https://github.com/org/repo/pull/1')
    text = str(blocks)
    assert 'github.com' in text


def test_pipeline_complete_without_pr_url():
    blocks = pipeline_complete_blocks('pipe-1')
    assert len(blocks) > 0


def test_approval_required_has_two_buttons():
    blocks = approval_required_blocks('pipe-1', 'review')
    action_block = next((b for b in blocks if b['type'] == 'actions'), None)
    assert action_block is not None
    assert len(action_block['elements']) == 2


def test_approval_buttons_embed_pipeline_id():
    blocks = approval_required_blocks('pipe-1', 'review')
    action_block = next(b for b in blocks if b['type'] == 'actions')
    values = [e['value'] for e in action_block['elements']]
    assert all('pipe-1' in v for v in values)
