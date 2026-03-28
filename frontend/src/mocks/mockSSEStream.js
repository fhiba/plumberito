const delay = (ms) => new Promise((res) => setTimeout(res, ms));

function sseEvent(payload) {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

function streamText(text, chunkSize = 8) {
  const chunks = [];
  for (let i = 0; i < text.length; i += chunkSize) {
    chunks.push(text.slice(i, i + chunkSize));
  }
  return chunks;
}

const MOCK_STEPS = [
  {
    step: 1,
    action: "ANALYZE",
    title: "Analyzing prompt.",
    content: "Breaking down the request and generating an execution plan.",
  },
  {
    step: 2,
    action: "REPO_CREATE",
    title: "Creating GitHub repository.",
    content: "Initializing repository `plumberito-demo` under your account with default branch `main`.",
  },
  {
    step: 3,
    action: "CODE_GEN",
    title: "Generating project files.",
    content: `Scaffolding project structure:\n\`\`\`bash\n├── index.html\n├── app.py\n├── requirements.txt\n└── README.md\n\`\`\``,
  },
  {
    step: 4,
    action: "INFRA_PROV",
    title: "Provisioning infrastructure via Pulumi.",
    content: "Creating S3 bucket for static assets and Cloud Run service for the backend. Stack: `plumberito-demo-dev`.",
  },
  {
    step: 5,
    action: "DEPLOY",
    title: "Deploying to target infrastructure.",
    content: "Build complete. Service live at: https://plumberito-demo.run.app",
  },
];

export function createMockSSEStream(prompt) {
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const enqueue = (payload) =>
        controller.enqueue(encoder.encode(sseEvent(payload)));

      await delay(400);
      enqueue({ type: "agent_start" });

      for (const step of MOCK_STEPS) {
        await delay(600);

        // Send step header (no content yet)
        enqueue({ type: "agent_step", step: step.step, action: step.action, title: step.title, content: "" });

        // Stream content word by word
        const chunks = streamText(step.content, 12);
        for (const chunk of chunks) {
          await delay(40);
          enqueue({ type: "agent_stream", delta: chunk });
        }

        await delay(300);
        enqueue({ type: "agent_step_done" });
      }

      await delay(400);
      enqueue({
        type: "token_usage",
        payload: {
          total_tokens: 1847,
          prompt_tokens: 312,
          completion_tokens: 1535,
          cost_usd: 0.0041,
        },
      });

      await delay(100);
      enqueue({ type: "agent_done" });

      controller.close();
    },
  });

  return stream;
}
