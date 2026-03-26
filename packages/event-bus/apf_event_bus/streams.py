"""Stream name constants for APF Redis Streams event bus."""


class Streams:
    STAGE_DISPATCH = "apf:stage:dispatch"          # orchestrator -> agent-runner
    STAGE_STARTED = "apf:stage:started"            # agent-runner -> orchestrator
    STAGE_COMPLETE = "apf:stage:complete"          # agent-runner -> orchestrator
    STAGE_FAILED = "apf:stage:failed"              # agent-runner -> orchestrator
    APPROVAL_REQUIRED = "apf:approval:required"   # orchestrator -> slack/dashboard
    APPROVAL_GRANTED = "apf:approval:granted"     # slack/dashboard -> orchestrator
    PIPELINE_COMPLETE = "apf:pipeline:complete"   # orchestrator -> all connectors
    PIPELINE_FAILED = "apf:pipeline:failed"       # orchestrator -> all connectors
    CONNECTOR_EVENT = "apf:connector:event"       # connectors -> orchestrator
