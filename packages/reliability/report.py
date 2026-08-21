"""
Deterministic report formatter for ReliabilityAssessment.
"""

from __future__ import annotations

from packages.core.models.reliability import ReliabilityAssessment
from packages.core.models.regression import RegressionReport
from packages.core.models.adaptive import AdaptiveTestPlan


def format_text(
    assessment: ReliabilityAssessment,
    regression_report: RegressionReport | None = None,
    adaptive_test_plan: AdaptiveTestPlan | None = None,
) -> str:
    """
    Generate a deterministic, plain-text human-readable reliability report.
    """
    score_details = assessment.score
    
    # 1. Agent details & Timestamps
    lines = []
    lines.append("================================================================================")
    lines.append("AGENT RELIABILITY REPORT")
    lines.append("================================================================================")
    lines.append(f"Agent ID:       {assessment.agent_id}")
    lines.append(f"Agent Version:  {assessment.agent_version}")
    lines.append(f"Assessment ID:  {assessment.run_id}")
    lines.append(f"Timestamp:      {score_details.timestamp.isoformat()}")
    lines.append("--------------------------------------------------------------------------------")
    
    # 2. Overall score & Grade & Risk Level
    lines.append("RELIABILITY METRICS")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(f"Overall Score:  {score_details.overall_score:.1f} / 100.0")
    lines.append(f"Grade:          {score_details.grade}")
    lines.append(f"Risk Level:     {score_details.risk_level.value.upper()}")
    lines.append(f"Confidence:     {score_details.confidence:.2f}")
    lines.append("--------------------------------------------------------------------------------")
    
    # 3. Scenario Results
    lines.append("SCENARIO EXECUTION SUMMARY")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(f"Total Scenarios Attempted:  {score_details.scenario_count}")
    lines.append(f"Passed Scenarios:           {score_details.pass_count} ({score_details.pass_rate * 100:.1f}%)")
    lines.append(f"Failed Scenarios:           {score_details.fail_count} ({score_details.failure_rate * 100:.1f}%)")
    lines.append(f"Inconclusive Scenarios:     {getattr(score_details, 'inconclusive_scenarios', 0)}")
    lines.append(f"Execution Failures (Infra):  {getattr(score_details, 'execution_failures', 0)}")
    lines.append(f"Evaluation Failures (Error): {getattr(score_details, 'evaluation_failures', 0)}")
    
    # Severity breakdown
    if score_details.severity_breakdown:
        lines.append("Failure Severity Breakdown:")
        for sev, count in sorted(score_details.severity_breakdown.items()):
            lines.append(f"  - {sev.upper()}: {count}")
    lines.append("--------------------------------------------------------------------------------")
    
    # 4. Strategy & Attack Surface Coverage
    lines.append("COVERAGE SUMMARY")
    lines.append("--------------------------------------------------------------------------------")
    lines.append(f"Covered Attack Strategies:   {', '.join(assessment.covered_strategies) or 'None'}")
    lines.append(f"Uncovered Attack Strategies: {', '.join(assessment.uncovered_strategies) or 'None'}")
    lines.append(f"Covered Attack Surfaces:     {', '.join(assessment.covered_attack_surfaces) or 'None'}")
    lines.append(f"Uncovered Attack Surfaces:   {', '.join(assessment.uncovered_attack_surfaces) or 'None'}")
    lines.append("--------------------------------------------------------------------------------")
    
    # 5. Major findings & 6. Highest-priority failures
    lines.append("RELIABILITY FINDINGS")
    lines.append("--------------------------------------------------------------------------------")
    if not assessment.findings:
        lines.append("No reliability findings reported.")
    else:
        # Sort findings by priority descending
        sorted_findings = sorted(assessment.findings, key=lambda f: f.priority, reverse=True)
        for i, finding in enumerate(sorted_findings, 1):
            sev_str = f" [{finding.severity.upper()}]" if finding.severity else ""
            lines.append(f"{i}. {finding.title}{sev_str} (Priority: {finding.priority}/100)")
            lines.append(f"   Category: {finding.category}")
            lines.append(f"   Description: {finding.description}")
            if finding.affected_tools:
                lines.append(f"   Affected Tools: {', '.join(finding.affected_tools)}")
            if finding.attack_surfaces:
                lines.append(f"   Attack Surfaces: {', '.join(finding.attack_surfaces)}")
            if finding.evidence:
                lines.append("   Evidence Summary:")
                for ev in finding.evidence[:3]:  # show up to 3 evidence points
                    lines.append(f"     * {ev}")
            lines.append("")
    lines.append("--------------------------------------------------------------------------------")
    
    # 7. Recommendations
    lines.append("RECOMMENDATIONS")
    lines.append("--------------------------------------------------------------------------------")
    if not assessment.recommendations:
        lines.append("No specific remediation recommendations.")
    else:
        for i, rec in enumerate(assessment.recommendations, 1):
            lines.append(f"{i}. {rec}")
    lines.append("--------------------------------------------------------------------------------")
    
    # 8. Regression status (if available)
    if regression_report is not None:
        lines.append("REGRESSION ANALYSIS")
        lines.append("--------------------------------------------------------------------------------")
        lines.append(f"Comparison Status:   {regression_report.status.value.upper()}")
        lines.append(f"Previous Run Score:  {regression_report.previous_score:.1f} ({regression_report.previous_grade})")
        lines.append(f"Current Run Score:   {regression_report.current_score:.1f} ({regression_report.current_grade})")
        lines.append(f"Score Delta:         {regression_report.score_delta:+.1f}")
        
        # Breakdown of changes
        lines.append(f"New Failures:        {len(regression_report.new_failures)}")
        for f in regression_report.new_failures:
            lines.append(f"  - [NEW] {f.title} ({f.current_severity})")
            
        lines.append(f"Fixed Failures:      {len(regression_report.fixed_failures)}")
        for f in regression_report.fixed_failures:
            lines.append(f"  - [FIXED] {f.title} ({f.previous_severity})")
            
        lines.append(f"Persistent Failures: {len(regression_report.persistent_failures)}")
        for f in regression_report.persistent_failures:
            lines.append(f"  - [PERSISTED] {f.title} ({f.current_severity})")
            
        lines.append("--------------------------------------------------------------------------------")
        
    # 9. Adaptive test plan (if available)
    if adaptive_test_plan is not None:
        lines.append("ADAPTIVE TEST PLANNING RECOMMENDATIONS")
        lines.append("--------------------------------------------------------------------------------")
        lines.append(f"Allocated Budget:           {adaptive_test_plan.budget} Scenarios")
        lines.append(f"Reasoning:                  {adaptive_test_plan.reasoning_summary}")
        lines.append(f"Selected Strategies:        {', '.join(adaptive_test_plan.selected_strategies) or 'None'}")
        
        if adaptive_test_plan.recommendations:
            lines.append("Plan Recommendations:")
            for i, rec in enumerate(adaptive_test_plan.recommendations, 1):
                lines.append(f"  {i}. {rec.title} (Priority: {rec.priority:.1f})")
                lines.append(f"     Action: {rec.recommended_action}")
        lines.append("--------------------------------------------------------------------------------")
        
    # 10. Quality & Limitations
    lines.append("QUALITY & LIMITATIONS")
    lines.append("--------------------------------------------------------------------------------")
    if score_details.scenario_count < 5:
        lines.append("Warning: Small scenario pool. Assessment confidence may be limited.")
    else:
        lines.append("Assessment confidence is robust based on the selected challenge pack size.")
    lines.append(f"Confidence score: {score_details.confidence:.2f}")
    lines.append("================================================================================")
    
    return "\n".join(lines)


def format_markdown(
    assessment: ReliabilityAssessment,
    regression_report: RegressionReport | None = None,
    adaptive_test_plan: AdaptiveTestPlan | None = None,
) -> str:
    """
    Generate a deterministic, markdown-formatted human-readable reliability report.
    """
    score_details = assessment.score
    
    lines = []
    lines.append(f"# Agent Reliability Report — {assessment.agent_id}")
    lines.append("")
    
    # Metadata Table
    lines.append("| Metadata | Details |")
    lines.append("| --- | --- |")
    lines.append(f"| **Agent ID** | `{assessment.agent_id}` |")
    lines.append(f"| **Agent Version** | `{assessment.agent_version}` |")
    lines.append(f"| **Assessment ID** | `{assessment.run_id}` |")
    lines.append(f"| **Timestamp** | {score_details.timestamp.isoformat()} |")
    lines.append("")
    
    # Overall summary alert
    status_emoji = "🟢"
    if score_details.overall_score < 75.0:
        status_emoji = "🟡"
    if score_details.overall_score < 60.0:
        status_emoji = "🔴"
        
    lines.append(f"## {status_emoji} Overall Metrics")
    lines.append(f"- **Reliability Score**: **{score_details.overall_score:.1f} / 100.0**")
    lines.append(f"- **Letter Grade**: **`{score_details.grade}`**")
    lines.append(f"- **Risk Level**: **`{score_details.risk_level.value.upper()}`**")
    lines.append(f"- **Confidence Score**: `{score_details.confidence:.2f}`")
    lines.append("")
    
    # Scenario Summary
    lines.append("## Scenario Execution Summary")
    lines.append("| Metric | Count | Rate |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| Total Attempted | {score_details.scenario_count} | 100% |")
    lines.append(f"| Passed | {score_details.pass_count} | {score_details.pass_rate * 100:.1f}% |")
    lines.append(f"| Failed | {score_details.fail_count} | {score_details.failure_rate * 100:.1f}% |")
    lines.append(f"| Inconclusive | {getattr(score_details, 'inconclusive_scenarios', 0)} | - |")
    lines.append(f"| Execution Failures | {getattr(score_details, 'execution_failures', 0)} | - |")
    lines.append(f"| Evaluation Failures | {getattr(score_details, 'evaluation_failures', 0)} | - |")
    lines.append("")
    
    # Coverage
    lines.append("## Coverage Status")
    lines.append("### Attack Strategies")
    lines.append(f"- **Covered**: {', '.join([f'`{s}`' for s in assessment.covered_strategies]) or 'None'}")
    lines.append(f"- **Uncovered**: {', '.join([f'`{s}`' for s in assessment.uncovered_strategies]) or 'None'}")
    lines.append("")
    lines.append("### Attack Surfaces")
    lines.append(f"- **Covered**: {', '.join([f'`{s}`' for s in assessment.covered_attack_surfaces]) or 'None'}")
    lines.append(f"- **Uncovered**: {', '.join([f'`{s}`' for s in assessment.uncovered_attack_surfaces]) or 'None'}")
    lines.append("")
    
    # Findings
    lines.append("## Major Reliability Findings")
    if not assessment.findings:
        lines.append("No reliability findings reported.")
    else:
        # Sort by priority desc
        sorted_findings = sorted(assessment.findings, key=lambda f: f.priority, reverse=True)
        for i, finding in enumerate(sorted_findings, 1):
            sev_badge = f" `{finding.severity.upper()}`" if finding.severity else ""
            lines.append(f"### {i}. {finding.title}{sev_badge}")
            lines.append(f"- **Priority**: {finding.priority} / 100")
            lines.append(f"- **Category**: `{finding.category}`")
            lines.append(f"- **Description**: {finding.description}")
            if finding.affected_tools:
                lines.append(f"- **Affected Tools**: {', '.join([f'`{t}`' for t in finding.affected_tools])}")
            if finding.attack_surfaces:
                lines.append(f"- **Attack Surfaces**: {', '.join([f'`{t}`' for t in finding.attack_surfaces])}")
            if finding.evidence:
                lines.append("- **Trace Evidence**:")
                for ev in finding.evidence[:3]:
                    lines.append(f"  - {ev}")
            lines.append("")
            
    # Recommendations
    lines.append("## Remediation Recommendations")
    if not assessment.recommendations:
        lines.append("No recommendations provided.")
    else:
        for i, rec in enumerate(assessment.recommendations, 1):
            lines.append(f"{i}. {rec}")
    lines.append("")
    
    # Regression
    if regression_report is not None:
        lines.append("## Regression Intelligence Analysis")
        lines.append(f"Status comparing current run to previous run (`{regression_report.previous_run_id}`):")
        lines.append("")
        lines.append(f"- **Status**: **`{regression_report.status.value.upper()}`**")
        lines.append(f"- **Score Delta**: `{regression_report.score_delta:+.1f}` (`{regression_report.previous_score:.1f}` &rarr; `{regression_report.current_score:.1f}`)")
        lines.append(f"- **Grade Delta**: `{regression_report.previous_grade}` &rarr; `{regression_report.current_grade}`")
        lines.append("")
        
        if regression_report.new_failures:
            lines.append("### New Failures Detected")
            for f in regression_report.new_failures:
                lines.append(f"- **{f.title}** (Severity: `{f.current_severity}`) - {f.description}")
            lines.append("")
            
        if regression_report.fixed_failures:
            lines.append("### Resolved Failures")
            for f in regression_report.fixed_failures:
                lines.append(f"- **{f.title}** (Resolved from `{f.previous_severity}`) - {f.description}")
            lines.append("")
            
        if regression_report.persistent_failures:
            lines.append("### Persistent Failures")
            for f in regression_report.persistent_failures:
                lines.append(f"- **{f.title}** (Severity: `{f.current_severity}`) - {f.description}")
            lines.append("")
            
    # Adaptive Plan
    if adaptive_test_plan is not None:
        lines.append("## Adaptive Test Plan for Next Assessment")
        lines.append(f"- **Target Scenario Budget**: `{adaptive_test_plan.budget}` scenarios")
        lines.append(f"- **Plan Rationale**: {adaptive_test_plan.reasoning_summary}")
        lines.append(f"- **Selected Strategies**: {', '.join([f'`{s}`' for s in adaptive_test_plan.selected_strategies]) or 'None'}")
        lines.append("")
        
        if adaptive_test_plan.recommendations:
            lines.append("### Recommended Actions")
            for i, rec in enumerate(adaptive_test_plan.recommendations, 1):
                lines.append(f"#### {i}. {rec.title} (Priority {rec.priority:.1f})")
                lines.append(f"- **Remediation Action**: {rec.recommended_action}")
                lines.append(f"- **Reasoning**: {rec.reason}")
                lines.append("")
                
    # Quality/Limitations
    lines.append("## Report Verification & Quality")
    if score_details.scenario_count < 5:
        lines.append("> [!WARNING]")
        lines.append("> Assessment was performed with a very small challenge pack size. Summary statistics may be sensitive to individual outliers.")
    else:
        lines.append("Assessment confidence is robust.")
        
    return "\n".join(lines)
