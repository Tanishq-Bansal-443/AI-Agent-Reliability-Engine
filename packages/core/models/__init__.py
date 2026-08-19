"""
Core models package.

Exports all canonical domain models for the AI Agent Reliability Engine.
"""

from packages.core.models.agent import (
    Tool,
    ToolParameter,
    Agent,
    AgentVersion,
    Capability,
    Constraint,
    RiskSurface,
    AgentProfile,
    AgentInput,
    AgentOutput,
    Message,
    ToolCallRecord,
    ToolCapability,
    AttackSurfaceEvidence,
    RiskIndicator,
    RiskProfile,
)
from packages.core.models.scenario import (
    AttackStrategy,
    AttackStrategyType,
    ScenarioCategory,
    RiskLevel,
    Risk,
    ExpectedBehavior,
    ConversationTurn,
    ResourceLimits,
    Scenario,
    ChallengePack,
)
from packages.core.models.trace import (
    StepType,
    ExecutionStatus,
    TraceEvent,
    Execution,
    Trace,
)
from packages.core.models.evaluation import (
    Severity,
    FailureCategory,
    Failure,
    EvaluationResult,
    # Phase 4A additions
    EvaluationVerdict,
    EvaluationStatus,
    EvidenceItem,
    EvaluationFinding,
    ScenarioEvaluationResult,
    ChallengePackEvaluationResult,
    # Phase 4B additions
    EvaluationSource,
    LLMJudgeResult,
)
from packages.core.models.reliability import (
    RegressionTest,
    ReliabilityScore,
    ReliabilityFinding,
    ReliabilityAssessment,
)
from packages.core.models.regression import (
    RegressionStatus,
    FailureChangeType,
    RegressionFinding,
    RegressionReport,
)
from packages.core.models.adaptive import (
    AdaptivePriority,
    AdaptiveRecommendation,
    AdaptiveTestPlan,
    AdaptiveScenarioAllocation,
    AdaptivePackMetadata,
)


__all__ = [
    # agent
    "Tool",
    "ToolParameter",
    "Agent",
    "AgentVersion",
    "Capability",
    "Constraint",
    "RiskSurface",
    "AgentProfile",
    "AgentInput",
    "AgentOutput",
    "Message",
    "ToolCallRecord",
    "ToolCapability",
    "AttackSurfaceEvidence",
    "RiskIndicator",
    "RiskProfile",
    # scenario
    "AttackStrategy",
    "AttackStrategyType",
    "ScenarioCategory",
    "RiskLevel",
    "Risk",
    "ExpectedBehavior",
    "ConversationTurn",
    "ResourceLimits",
    "Scenario",
    "ChallengePack",
    # trace
    "StepType",
    "ExecutionStatus",
    "TraceEvent",
    "Execution",
    "Trace",
    # evaluation (Phase 0 + Phase 4A + Phase 4B)
    "Severity",
    "FailureCategory",
    "Failure",
    "EvaluationResult",
    "EvaluationVerdict",
    "EvaluationStatus",
    "EvidenceItem",
    "EvaluationFinding",
    "ScenarioEvaluationResult",
    "ChallengePackEvaluationResult",
    "EvaluationSource",
    "LLMJudgeResult",
    # reliability
    "RegressionTest",
    "ReliabilityScore",
    "ReliabilityFinding",
    "ReliabilityAssessment",
    # regression
    "RegressionStatus",
    "FailureChangeType",
    "RegressionFinding",
    "RegressionReport",
    # adaptive
    "AdaptivePriority",
    "AdaptiveRecommendation",
    "AdaptiveTestPlan",
    "AdaptiveScenarioAllocation",
    "AdaptivePackMetadata",
]

