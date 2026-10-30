"""
Shared utilities for web-dev app.
Re-exports from shared-canonical-services for consistent usage across apps.
"""

// Re-export types
export type {
  WorkflowNodeData,
  WorkflowNodeCreate,
  WorkflowEdgeCreate,
  WorkflowCreate,
  WorkflowResponse,
  WorkflowExecutionCreate,
  WorkflowExecutionResponse,
} from '@retention-analytics-platform/shared-canonical-services/src/types';

// Re-export API client
export { APIClient } from '@retention-analytics-platform/shared-canonical-services/src/api/client';

// Re-export validation
export {
  ResponseValidator,
  JSONSchemaValidator,
  DataValidator,
  SecurityTester,
  SecurityTestResult,
} from '@retention-analytics-platform/shared-canonical-services/src/validation';

// Re-export performance testing
export {
  PerformanceResult,
  PerformanceTester,
  Benchmark,
  async_benchmark,
} from '@retention-analytics-platform/shared-canonical-services/src/testing/performance';

// Re-export utils
export {
  cn,
  formatDate,
  formatCurrency,
  formatPercentage,
  truncateText,
  slugify,
  debounce,
  throttle,
} from '@retention-analytics-platform/shared-canonical-services/src/utils';

// Helper to create authenticated API client
export function createApiClient(baseUrl: string, token?: string): APIClient {
  const client = new APIClient(baseUrl);
  if (token) {
    client.setAuthToken(token);
  }
  return client;
}
