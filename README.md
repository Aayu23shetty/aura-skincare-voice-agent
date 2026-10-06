# Aura Skincare — Aria Voice CX Agent

A browser-first AI voice customer-support prototype built for the DataStraw AI Voice Agent assessment.

## What this submission includes

- Browser microphone input using the Web Speech API.
- Spoken agent responses using the browser's speech synthesis, preferring an `en-IN` voice when the browser provides one.
- Flask backend with a small, auditable order database.
- `get_order_details(order_id)` function exposed to the LLM as a tool.
- Brand-policy guardrails for shipping, returns/refunds, cancellation, COD, and scope.
- Graceful handling for unknown order IDs and out-of-scope requests.
- Post-call chronological transcript.
- Structured JSON outcome after the call.
- Visible test-order helper and one-click test prompts.
- A deterministic Demo Mode so the UI can be tested without an API key.

The assignment explicitly allows the technology stack to be chosen by the candidate and asks for a browser-accessible application, source repository, README, `.env.example`, demo video, approach note, and LinkedIn link. The supplied assessment also states that AI-assisted development tools are encouraged, but the candidate should understand the submitted system.

## Architecture

```text
Browser
  |
  | microphone
  v
Web Speech Recognition (en-IN)
  |
  | text
  v
Flask /api/chat
  |
  +--> policy prompt + conversation history
  |
  +--> LLM
  |      |
  |      +--> get_order_details(order_id)
  |               |
  |               v
  |          data/orders.json
  |
  v
concise text response
  |
  v
Browser Speech Synthesis
  |
  v
customer hears Aria

After End Call:
Browser transcript -> Flask /api/summary -> structured JSON
```

### Why this architecture?

I deliberately kept the first version modular rather than tying the whole prototype to a realtime voice vendor. The browser handles microphone capture and playback, while the backend owns policy, order data, and tool execution. That separation makes the demo easy to inspect: a reviewer can see exactly where the business rules live and exactly when an order lookup is performed.

The assessment specifically says that a modular STT → LLM/tool → TTS pipeline or a realtime API are both acceptable, and that the evaluator is more interested in the natural experience, latency, and understanding of the implementation than a particular vendor choice.

## Technology choices

- **Python + Flask:** small backend footprint and straightforward deployment.
- **OpenAI API:** used only when `OPENAI_API_KEY` is configured. The code uses tool calling for the order lookup.
- **Web Speech API:** avoids shipping API credentials to the browser and provides a zero-extra-service voice layer for the prototype.
- **JSON order store:** intentionally tiny and transparent because the supplied assessment gives only three mock orders.
- **Vanilla HTML/CSS/JS:** keeps the demo dependency-light and fast to run.

## Guardrail design

Aria receives a policy block on every AI request. It is instructed to:

1. use the order tool for order-specific facts;
2. never invent tracking or delivery information;
3. ask for an order ID instead of guessing;
4. reject unsupported scope politely;
5. explain policy constraints instead of promising exceptions;
6. keep spoken responses short.

The tool result is treated as the source of truth for the three sample orders.

## Edge cases covered

### Invalid order
`Where is ORD-999?`

Expected behavior: Aria says the order could not be located and asks the customer to verify the ID.

### Missing order ID
`Can you track my order?`

Expected behavior: Aria asks for the order ID.

### Return outside policy
`I bought this 20 days ago and opened it. Can I return it?`

Expected behavior: the agent explains that the request falls outside the 7-day return window and the unopened/unused condition.

### Cancellation
`Can I cancel ORD-103?`

Expected behavior: the agent looks up the order and confirms that Processing orders are eligible for cancellation.

`Can I cancel ORD-101?`

Expected behavior: the agent explains that an Out for Delivery order cannot be cancelled.

### Out of scope
`Can you book me a flight to Goa?`

Expected behavior: the agent politely says it only supports Aura Skincare-related requests.

## Local setup

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy `.env.example` to `.env`.

For AI mode:

```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5
DEMO_MODE=0
```

For no-key testing:

```env
DEMO_MODE=1
```

### 4. Run

```bash
python run.py
```

Open `http://127.0.0.1:5000`.

For microphone access, use Chrome or Edge and allow microphone permission.

## Demo script

A clean 3–5 minute walkthrough:

1. Open the app and point out the three sample orders.
2. Click **Start Call**.
3. Ask: “Where is order ORD-101?”
4. Show that Aria uses the order lookup and answers with the BlueDart status.
5. Ask: “Can I cancel it?”
6. Let Aria explain the policy because the order is already Out for Delivery.
7. Ask the return-policy edge case about an opened item after 20 days.
8. Ask the out-of-scope Goa flight question.
9. Click **End Call**.
10. Show the transcript and JSON outcome.
11. Briefly walk through `app/agent.py`, `get_order_details`, and the policy prompt.

## Section 9 — How I Think About the Build

### 1. Why this architecture and stack?

I wanted the demo to make the important product boundaries visible. Voice input/output belongs in the browser, but customer-support policy and order retrieval belong behind the server. Flask keeps that backend easy to inspect, while the LLM is given one narrow business tool rather than direct access to the order store.

### 2. Most difficult part

The tricky part is not generating a sentence; it is making sure a fluent model does not turn missing information into a confident answer. I addressed that by separating order facts into a tool, putting the brand rules into the system instruction, and making invalid/missing order IDs explicit cases in the tool response.

### 3. One more week

I would move from browser speech recognition to a realtime streaming voice pipeline with interruption handling. That would reduce the turn-taking delay and make the interaction feel closer to a real support call, while also giving the application more consistent speech recognition across browsers.

### 4. What changes at 1,000 conversations/day?

I would separate the web layer from the agent workers, move order data to a real transactional database, add structured logs and tracing, add rate limiting/authentication, and make the conversation/session store durable. I would also add evaluation datasets for policy compliance, tool accuracy, latency, and failure recovery before increasing traffic.

## Approach note

I built Aria as a browser-first voice CX agent with a thin Flask backend. The backend keeps the brand rules and order lookup deterministic, while the language model handles conversational reasoning and invokes `get_order_details` only when order-specific facts are needed.

## Important submission notes

The assignment requires the final application to be publicly accessible and asks for a GitHub repository, a 3–5 minute demo video, an approach note, and a LinkedIn profile link. Those external links cannot be generated from this local project archive; add your own deployment URL, repository URL, video URL, and LinkedIn URL before sending the email.

Submission email format from the assessment:

- To: `ozair.shaikh@datastraw.in`, `aryan.jaiswal@datastraw.in`
- CC: `talent@datastraw.in`
- Subject: `AI Voice Agent Assignment - [Your Full Name]`

## Project structure

```text
aura_voice_agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── routes.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── app.js
│       └── styles.css
├── data/
│   └── orders.json
├── docs/
│   ├── DEMO_SCRIPT.md
│   └── ARCHITECTURE.md
├── tests/
│   └── test_logic.py
├── .env.example
├── .gitignore
├── Procfile
├── README.md
├── requirements.txt
└── run.py
```

## API smoke tests

With the app running:

```bash
curl http://127.0.0.1:5000/api/health
```

Order tool endpoint:

```bash
curl -X POST http://127.0.0.1:5000/api/order ^
  -H "Content-Type: application/json" ^
  -d "{\"order_id\":\"ORD-101\"}"
```

On macOS/Linux, replace `^` with `\`.
