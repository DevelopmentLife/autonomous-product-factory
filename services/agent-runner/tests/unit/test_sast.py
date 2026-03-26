from apf_agent_runner.sast.secret_scan import scan_for_secrets


def test_finds_anthropic_key():
    content = 'key = sk-ant-api03-ABC123DEF456GHI789JKL012MNO345PQR678STU901'
    findings = scan_for_secrets(content)
    assert len(findings) > 0


def test_finds_aws_key():
    content = 'aws_access = AKIAIOSFODNN7EXAMPLE'
    findings = scan_for_secrets(content)
    assert len(findings) > 0


def test_no_findings_on_clean_code():
    content = "import os\ndef main():\n    print('hello world')\n"
    findings = scan_for_secrets(content)
    assert len(findings) == 0


def test_high_entropy_detection():
    content = 'token = aB3kX9mQ2nR8sT7uV1wY4zA5cD6eF0g'
    findings = scan_for_secrets(content)
    types = [f['type'] for f in findings]
    assert any(t in ('pattern_match', 'high_entropy') for t in types)
