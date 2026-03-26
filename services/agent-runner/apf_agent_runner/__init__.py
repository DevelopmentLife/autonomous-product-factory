"""apf_agent_runner — Worker process for the Autonomous Product Factory.

Dequeues StageDispatchEvent messages from Redis Streams, executes the
appropriate agent (LLM call), and publishes results back via the event bus.
"""

__version__ = "0.1.0"
