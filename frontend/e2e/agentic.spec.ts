import { expect, test } from './helpers'

test.describe('Agentic RAG page', () => {
  test('runs diagnosis and displays decision, tool calls, trace, and escalation', async ({ page }) => {
    await page.route('**/api/v1/acceptance/overview', async (route) => {
      await route.fulfill({ json: { status: 'ok', version: 'test', generated_from: [], panels: [] } })
    })
    await page.route('**/api/v1/rag/graph/relations', async (route) => {
      await route.fulfill({
        json: [
          {
            source: 'UPS-30K',
            relation: 'HAS_FAULT',
            target: 'SMOKE',
            weight: 1,
            evidence_source: 'local_graph',
          },
        ],
      })
    })
    await page.route('**/api/v1/agent/diagnose', async (route) => {
      await route.fulfill({
        json: {
          decision: 'escalate',
          answer: 'High risk: stop operation and escalate to human review.',
          plan: ['check security', 'search knowledge base', 'check risk'],
          tool_calls: [
            { tool: 'security_check', status: 'passed', summary: 'ALLOW', inputs: {}, outputs: {} },
            {
              tool: 'knowledge_search',
              status: 'completed',
              summary: '2 chunks retrieved',
              inputs: {},
              outputs: { retrieval_attempts: 2, rewritten_query: 'UPS smoke high risk' },
            },
            { tool: 'risk_check', status: 'completed', summary: 'high', inputs: {}, outputs: { risk_level: 'high' } },
            {
              tool: 'ticket_escalation',
              status: 'created',
              summary: 'wait_for_human',
              inputs: {},
              outputs: { ticket_id: 'TCK-123' },
            },
          ],
          citations: [{ source: 'ups_30k.txt', chunk_index: 0, content: 'UPS smoke is high risk.' }],
          quality: {
            retrieval_score: 0.8,
            citation_count: 1,
            faithfulness_hint: 'grounded',
            risk_level: 'high',
          },
          trace_id: 'TRACE-123',
          ticket_id: 'TCK-123',
        },
      })
    })

    await page.goto('/#/agentic')
    await expect(page.locator('[data-testid="page-agentic"]')).toBeVisible()

    await page.locator('textarea').first().fill('UPS-30K battery smoke and odor')
    await page.click('[data-testid="agentic-run"]')

    await expect(page.locator('[data-testid="agentic-decision"]')).toContainText('escalate')
    await expect(page.locator('[data-testid="agentic-trace-id"]')).toContainText('TRACE-123')
    await expect(page.locator('[data-testid="agentic-tool-calls"]')).toContainText('knowledge_search')
    await expect(page.locator('[data-testid="agentic-adaptive"]')).toContainText('2')
    await expect(page.locator('[data-testid="agentic-graph-relations"]')).toContainText('UPS-30K')
  })
})
