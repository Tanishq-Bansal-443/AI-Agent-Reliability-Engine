import { describe, it, expect } from 'vitest';
import { 
  getWorkspacePath, 
  validateIdentifier, 
  loadAssessment, 
  checkAssessmentIntegrity, 
  checkArtifactExistence,
  listAssessments
} from '../lib/api';

describe('api.ts Security & Path Traversal Checks', () => {
  it('rejects path traversal and absolute paths in validateIdentifier', () => {
    const invalidIds = [
      '../foo',
      '../../data',
      '/etc/passwd',
      'foo/bar',
      'foo\\bar',
      '',
      '.',
      '..',
      '../../../etc/passwd',
      'foo\0bar'
    ];
    for (const id of invalidIds) {
      expect(() => validateIdentifier(id)).toThrow();
    }
  });

  it('allows valid identifier formats used by the Python engine', () => {
    const validIds = [
      '0f961fd4-4393-4dbf-8e7b-79c9636f9b5a', // UUID
      '1899eaa0475d71655b6530ec1e333e817d5c63b5cbaab30fdb6968ada05da78c', // SHA256
      'test-assessment-id-123', // Alphanumeric with hyphens
    ];
    for (const id of validIds) {
      expect(validateIdentifier(id)).toBe(id);
    }
  });

  it('rejects paths escaping the workspace in getWorkspacePath', () => {
    const invalidSubPaths = [
      '../../etc/passwd',
      '../outside',
    ];
    for (const subPath of invalidSubPaths) {
      expect(() => getWorkspacePath(subPath)).toThrow(/path traversal/i);
    }
  });

  it('resolves valid paths inside the workspace in getWorkspacePath', () => {
    const validSubPaths = [
      'data/assessments',
      'traces',
      './data',
    ];
    for (const subPath of validSubPaths) {
      const resolved = getWorkspacePath(subPath);
      expect(resolved).toContain('AI-Agent-Reliability-Engine');
    }
  });
});

describe('api.ts Real Artifact Verification', () => {
  it('loads a real assessment, verifies its content hash and integrity', () => {
    const assessmentId = '0f961fd4-4393-4dbf-8e7b-79c9636f9b5a';
    const assessment = loadAssessment(assessmentId);
    
    expect(assessment).not.toBeNull();
    expect(assessment.assessment_id).toBe(assessmentId);
    
    // Verify integrity checks
    const integrity = checkAssessmentIntegrity(assessment);
    expect(integrity.valid).toBe(true);
  });

  it('verifies child artifact references and existence checks', () => {
    const assessmentId = '0f961fd4-4393-4dbf-8e7b-79c9636f9b5a';
    const assessment = loadAssessment(assessmentId);
    expect(assessment).not.toBeNull();

    // Challenge Pack
    const packCheck = checkArtifactExistence('Challenge Pack', assessment.challenge_pack_id);
    expect(packCheck.exists).toBe(true);
    expect(packCheck.path).toBe(`data/challenge_packs/${assessment.challenge_pack_id}.json`);

    // Execution Run
    const runCheck = checkArtifactExistence('Execution Run', assessment.execution_run_id);
    expect(runCheck.exists).toBe(true);
    expect(runCheck.path).toBe(`data/runs/${assessment.execution_run_id}.json`);

    // Trace reference (might be missing because traces are gitignored, but check existence)
    if (assessment.trace_ids.length > 0) {
      const firstTraceId = assessment.trace_ids[0];
      const traceCheck = checkArtifactExistence('Trace', firstTraceId);
      expect(traceCheck.path).toBe(`traces/${firstTraceId}.json`);
    }
  });

  it('lists all assessments without error and verifies integrity of every assessment', () => {
    const list = listAssessments();
    expect(list.length).toBeGreaterThan(0);
    for (const item of list) {
      expect(item.assessment_id).toBeDefined();
      expect(item.content_hash).toBeDefined();
      
      const integrity = checkAssessmentIntegrity(item);
      expect(integrity.valid).toBe(true);
    }
  });
});
