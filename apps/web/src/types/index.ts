// TypeScript models mapped directly from the AI Agent Reliability Engine Pydantic definitions.

export interface ReliabilityAssessmentArtifact {
  assessment_id: string;
  agent_id: string;
  agent_version: string;
  challenge_pack_id: string;
  execution_run_id: string;
  trace_ids: string[];
  evaluation_result: ChallengePackEvaluationResult;
  reliability_assessment: ReliabilityAssessment;
  regression_report: RegressionReport | null;
  adaptive_test_plan: AdaptiveTestPlan | null;
  created_at: string;
  completed_at: string;
  engine_config: Record<string, any>;
  warnings: string[];
  errors: string[];
  content_hash: string;
  metadata: Record<string, any>;
}

export interface ChallengePackEvaluationResult {
  pack_id: string;
  run_id: string;
  agent_id: string;
  scenario_results: ScenarioEvaluationResult[];
  total_scenarios: number;
  passed: number;
  failed: number;
  inconclusive: number;
  execution_failures: number;
  evaluation_failures: number;
  metadata: Record<string, any>;
}

export interface ScenarioEvaluationResult {
  scenario_id: string;
  trace_id: string;
  scenario_name: string;
  verdict: 'PASS' | 'FAIL' | 'INCONCLUSIVE';
  evaluation_status: 'EVALUATED' | 'NOT_EVALUATED' | 'EVALUATION_ERROR';
  severity: string; // 'low' | 'medium' | 'high' | 'critical'
  findings: EvaluationFinding[];
  violated_rules: string[];
  execution_status: 'success' | 'failure' | 'timeout' | 'error';
  source?: 'deterministic' | 'llm' | 'composite' | null;
  deterministic_verdict?: 'PASS' | 'FAIL' | 'INCONCLUSIVE' | null;
  llm_verdict?: 'PASS' | 'FAIL' | 'INCONCLUSIVE' | null;
  llm_confidence?: number | null;
  metadata: Record<string, any>;
}

export interface EvaluationFinding {
  requirement: string;
  verdict: 'PASS' | 'FAIL' | 'INCONCLUSIVE';
  evidence: EvidenceItem[];
  rule: string | null;
  category: string | null;
  validator: string;
}

export interface EvidenceItem {
  event_index: number | null;
  tool: string | null;
  content: string;
  reason: string;
  trace_backed: boolean;
}

export interface ReliabilityAssessment {
  agent_id: string;
  agent_version: string;
  challenge_pack_id: string;
  run_id: string;
  score: ReliabilityScore;
  findings: ReliabilityFinding[];
  covered_strategies: string[];
  uncovered_strategies: string[];
  covered_attack_surfaces: string[];
  uncovered_attack_surfaces: string[];
  recommendations: string[];
  metadata: Record<string, any>;
}

export interface ReliabilityScore {
  agent_id: string;
  version: string;
  run_id: string;
  overall_score: number;
  pass_rate: number;
  failure_rate: number;
  scenario_count: number;
  pass_count: number;
  fail_count: number;
  critical_failure_count: number;
  severity_breakdown: Record<string, number>;
  category_breakdown: Record<string, number>;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  recommendations: string[];
  timestamp: string;
  grade: string;
  scenario_score: number;
  severity_adjusted_score: number;
  coverage_score: number;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  inconclusive_scenarios: number;
  critical_failures: number;
  high_failures: number;
  medium_failures: number;
  low_failures: number;
  execution_failures: number;
  evaluation_failures: number;
  metadata: Record<string, any>;
}

export interface ReliabilityFinding {
  category: string;
  title: string;
  description: string;
  severity: string | null;
  affected_scenarios: string[];
  affected_tools: string[];
  attack_surfaces: string[];
  evidence: string[];
  priority: number;
}

export interface RegressionReport {
  agent_id: string;
  agent_version: string;
  previous_run_id: string;
  current_run_id: string;
  previous_score: number;
  current_score: number;
  score_delta: number;
  previous_grade: string;
  current_grade: string;
  status: 'improved' | 'regressed' | 'stable' | 'inconclusive';
  new_failures: RegressionFinding[];
  fixed_failures: RegressionFinding[];
  persistent_failures: RegressionFinding[];
  severity_changes: RegressionFinding[];
  new_attack_surfaces: string[];
  resolved_attack_surfaces: string[];
  new_strategies: string[];
  resolved_strategies: string[];
  recommendations: string[];
  metadata: Record<string, any>;
}

export interface RegressionFinding {
  change_type: 'new' | 'fixed' | 'persisted' | 'severity_increased' | 'severity_decreased';
  category: string;
  title: string;
  previous_severity: string | null;
  current_severity: string | null;
  previous_scenarios: string[];
  current_scenarios: string[];
  previous_tools: string[];
  current_tools: string[];
  attack_surfaces: string[];
  description: string;
  priority: number;
}

export interface AdaptiveTestPlan {
  agent_id: string;
  agent_version: string;
  source_run_id: string | null;
  prior_run_id: string | null;
  budget: number;
  selected_strategies: string[];
  strategy_priorities: AdaptivePriority[];
  recommendations: AdaptiveRecommendation[];
  coverage_gaps: string[];
  reasoning_summary: string;
  metadata: Record<string, any>;
}

export interface AdaptivePriority {
  strategy_id: string;
  priority_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  evidence: string[];
  recommended_scenario_count: number;
  metadata: Record<string, any>;
}

export interface AdaptiveRecommendation {
  id: string;
  strategy_id: string | null;
  target_tool: string | null;
  title: string;
  description: string;
  priority: number;
  reason: string;
  recommended_action: string;
  metadata: Record<string, any>;
}

export interface Trace {
  run_id: string;
  agent_id: string;
  agent_version: string;
  scenario_id: string;
  scenario_name: string;
  started_at: string;
  completed_at: string | null;
  events: TraceEvent[];
  status: 'success' | 'failure' | 'timeout' | 'error';
  error: string | null;
  metadata: Record<string, any>;
}

export interface TraceEvent {
  step_index: number;
  type: 'user_input' | 'model_call' | 'model_output' | 'tool_call' | 'tool_result' | 'environment_change' | 'final_response' | 'error';
  timestamp: string;
  duration_ms: number;
  input_data: Record<string, any>;
  output_data: Record<string, any>;
  metadata: Record<string, any>;
}

export interface ChallengePack {
  id: string;
  name: string;
  description: string;
  agent_id: string;
  agent_version: string;
  scenarios: Scenario[];
  resource_limits: ResourceLimits;
  version: string;
  strategy_coverage: Record<string, boolean>;
  risk_coverage: Record<string, boolean>;
  attack_surface_coverage: Record<string, boolean>;
  created_at: string;
  metadata: Record<string, any>;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  category: string;
  attack_type: string | null;
  target_risk: string | null;
  turns: ConversationTurn[];
  initial_message: string;
  expected_behavior: ExpectedBehavior;
  resource_limits: ResourceLimits;
  tags: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  metadata: Record<string, any>;
}

export interface ConversationTurn {
  role: string;
  content: string;
}

export interface ResourceLimits {
  max_turns: number;
  timeout_seconds: number;
  max_tool_calls: number;
}

export interface ExpectedBehavior {
  description: string;
  should_refuse: boolean;
  allowed_tools: string[];
  forbidden_tools: string[];
  required_tools: string[];
  validators: string[];
  rules: string[];
}

export interface ExecutionRun {
  run_id: string;
  challenge_pack_id: string;
  agent_id: string;
  agent_version: string;
  status: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  scenario_ids: string[];
  trace_references: Record<string, string>;
  stats: {
    total_scenarios: number;
    failed_scenarios: number;
    successful_scenarios: number;
  };
  metadata: Record<string, any>;
}
