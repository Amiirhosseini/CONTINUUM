// CONTINUUM — Interactive Application Logic

document.addEventListener('DOMContentLoaded', () => {
  initSimulator();
  initDiffViewer();
  initCalculator();
  initCodeTabs();
  initArchTooltips();
});

// ---------------------------------------------------------------------------
// 1. Live Fault Recovery Simulator Engine
// ---------------------------------------------------------------------------
const scenarioData = {
  crash: {
    badgeClass: "ok",
    badgeText: "RESUME [SAFE]",
    terminal: `<span class="hl-dim">$ continuum resume run_4821</span>

<span class="hl-bold">CONTINUUM RECOVERY ENGINE v0.1.0</span>
Run ID: run_4821
Checkpoint Version: v17 (SHA-256: 8f3a92b1...)
Event Log Chain Audit: <span class="hl-green">INTEGRITY_VERIFIED (102/102 events trusted)</span>

<span class="hl-dim">--- State Audit ---</span>
<span class="hl-green">[VALID]</span> Goal: "Analyze 10,000 research documents"
<span class="hl-green">[VALID]</span> Progress: 3,421 completed, 6,579 pending
<span class="hl-green">[VALID]</span> 127 findings preserved (100% evidence verified)
<span class="hl-green">[VALID]</span> 14 decisions valid
<span class="hl-green">[VALID]</span> Action Ledger: 8 side effects verified (0 duplicated)

<span class="hl-dim">--- Recovery Decision ---</span>
Recovery Safety: <span class="hl-green">SAFE_TO_RESUME</span>
Mode: RESUME
Next permitted action: process_batch(start_index=3422)

<span class="hl-green">✓ Task resumed from verified progress. Zero duplicated work.</span>`,

    stateJson: `{
  "run_id": "run_4821",
  "goal": {
    "description": "Analyze 10,000 research documents",
    "version": 1
  },
  "progress": { "completed": 3421, "pending": 6579, "failed": 0 },
  "decisions": [
    {
      "decision_id": "dec_014",
      "decision": "Include peer-reviewed meta-analyses",
      "status": "valid",
      "evidence": ["ev_088", "ev_089"]
    }
  ],
  "findings_count": 127,
  "source_sequence": 102
}`,

    contractJson: `{
  "run_id": "run_4821",
  "recovery_status": "safe_to_resume",
  "verified": ["goal", "progress", "decisions", "evidence"],
  "invalidated": [],
  "required_actions": [],
  "next_allowed_action": "process_batch(3422)"
}`
  },

  dataset: {
    badgeClass: "warn",
    badgeText: "REPAIR_AND_RESUME",
    terminal: `<span class="hl-dim">$ continuum resume run_4821</span>

<span class="hl-bold">CONTINUUM RECOVERY ENGINE v0.1.0</span>
Run ID: run_4821
Checkpoint Version: v17

<span class="hl-dim">--- Environment Snapshot Audit ---</span>
<span class="hl-green">[VALID]</span> Goal & Progress verified
<span class="hl-red">[FAIL] Resource Mismatch</span>: Dependency 'dataset' changed from version 'v3' -> 'v4'
<span class="hl-amber">[STALE]</span> 4 findings tied to dataset v3 marked REQUIRES_REVALIDATION
<span class="hl-red">[INVALIDATED]</span> Decision #7 ('Only subset A analyzed') marked INVALID

<span class="term-dim">--- Recovery Contract Generated ---</span>
Recovery Safety: <span class="hl-amber">REQUIRES_REPAIR</span>
Mode: REPAIR_AND_RESUME
Invalidated Components: ["dataset_v3", "decision_7"]
Required Actions: ["revalidate experiments 14-17 against dataset v4"]
Next Allowed Action: dataset_revalidation

<span class="hl-amber">⚠ Environment shift detected. Unsafe replay prevented by contract.</span>`,

    stateJson: `{
  "run_id": "run_4821",
  "external_dependencies": [
    {
      "resource": "dataset",
      "version": "v4",
      "status": "conflicted",
      "metadata": { "previous_version": "v3" }
    }
  ],
  "decisions": [
    {
      "decision_id": "dec_007",
      "decision": "Only subset A analyzed",
      "status": "invalidated",
      "invalidated_reason": "Dependency dataset updated v3 -> v4"
    }
  ]
}`,

    contractJson: `{
  "run_id": "run_4821",
  "recovery_status": "requires_repair",
  "verified": ["goal", "completed_documents_1_to_3400"],
  "invalidated": ["dataset_v3", "decision_7"],
  "required_actions": ["revalidate_experiments_14_to_17"],
  "next_allowed_action": "dataset_revalidation"
}`
  },

  model: {
    badgeClass: "warn",
    badgeText: "MODEL TRANSITION",
    terminal: `<span class="hl-dim">$ continuum resume run_4821 --model claude-3-5-sonnet</span>

<span class="hl-bold">CONTINUUM RECOVERY ENGINE v0.1.0</span>
Run ID: run_4821
Checkpoint Version: v17

<span class="hl-dim">--- Model Transition Audit ---</span>
Previous Model: gpt-4o (provider: openai)
Target Model: claude-3-5-sonnet (provider: anthropic)

<span class="hl-amber">[MODEL_SPECIFIC_STATE]</span> Assumption 'prompt_format_v1' requires re-eval
<span class="hl-green">[VALID]</span> Task Goal, Verified Progress, Findings, and Evidence preserved
<span class="hl-cyan">[RECONSTRUCTION]</span> Bounded recovery context reconstructed (3,800 tokens vs 182,000 transcript)

<span class="hl-dim">--- Recovery Decision ---</span>
Recovery Safety: <span class="hl-green">SAFE_TO_RESUME</span>
Mode: RESUME (Framework-Agnostic Context Transferred)

<span class="hl-green">✓ Switched models safely without replaying full prompt transcript.</span>`,

    stateJson: `{
  "run_id": "run_4821",
  "model": {
    "model": "claude-3-5-sonnet",
    "provider": "anthropic",
    "model_specific_state": [
      {
        "item_id": "model_state_001",
        "description": "GPT-4 prompt formatting assumption",
        "required_validation": "Must be revalidated after model change"
      }
    ]
  }
}`,

    contractJson: `{
  "run_id": "run_4821",
  "recovery_status": "safe_to_resume",
  "verified": ["goal", "progress", "evidence"],
  "invalidated": ["model_specific_state_001"],
  "required_actions": ["reevaluate_prompt_format"],
  "next_allowed_action": "continue_execution"
}`
  },

  sideeffect: {
    badgeClass: "err",
    badgeText: "HUMAN REVIEW",
    terminal: `<span class="hl-dim">$ continuum resume run_4821</span>

<span class="hl-bold">CONTINUUM ACTION LEDGER RECONCILIATION</span>
Run ID: run_4821
Last Action: action_812 ("github.create_issue")

<span class="hl-red">[UNKNOWN_SIDE_EFFECT]</span> Process killed during external write call.
Action status: STARTED (completion unconfirmed by server ack).

<span class="hl-dim">--- Reconciliation Guard ---</span>
Action ID: action_812
Arguments Hash: e3b0c442...
Outcome: UNCERTAIN

Recovery Safety: <span class="hl-red">REQUIRES_HUMAN</span>
Mode: REQUEST_HUMAN
Action: Execution halted to prevent duplicate issue creation.

<span class="hl-red">❌ Automatic retry blocked to protect external system idempotency.</span>`,

    stateJson: `{
  "action_id": "action_812",
  "action_type": "github.create_issue",
  "arguments_hash": "e3b0c442...",
  "status": "started",
  "side_effect_uncertain": true
}`,

    contractJson: `{
  "run_id": "run_4821",
  "recovery_status": "requires_human",
  "verified": ["prior_actions_1_to_811"],
  "invalidated": [],
  "required_actions": ["human_reconcile_action_812"],
  "next_allowed_action": null
}`
  }
};

let currentScenario = 'crash';
let currentTab = 'terminal';

function initSimulator() {
  const navBtns = document.querySelectorAll('.sim-nav-btn');
  const tabBtns = document.querySelectorAll('.sim-tab-btn');

  if (!navBtns.length) return;

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const scenarioKey = btn.getAttribute('data-scenario');
      if (!scenarioData[scenarioKey]) return;

      navBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      currentScenario = scenarioKey;
      renderSimulatorOutput();
    });
  });

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabKey = btn.getAttribute('data-tab');
      tabBtns.forEach(t => t.classList.remove('active'));
      btn.classList.add('active');

      currentTab = tabKey;
      renderSimulatorOutput();
    });
  });

  renderSimulatorOutput();
}

function renderSimulatorOutput() {
  const outputEl = document.getElementById('simOutputArea');
  if (!outputEl) return;

  const data = scenarioData[currentScenario];
  if (!data) return;

  if (currentTab === 'terminal') {
    outputEl.innerHTML = data.terminal;
  } else if (currentTab === 'state') {
    outputEl.textContent = data.stateJson;
  } else if (currentTab === 'contract') {
    outputEl.textContent = data.contractJson;
  }
}

// ---------------------------------------------------------------------------
// 2. Interactive Checkpoint Diff Engine
// ---------------------------------------------------------------------------
const diffLeftState = `{
  "checkpoint_id": "chk_v16",
  "version": 16,
  "progress": { "completed": 3400, "pending": 6600 },
  "external_dependencies": [
    { "resource": "dataset", "version": "v3" }
  ],
  "decisions": [
    { "id": "dec_007", "decision": "Subset A filter", "status": "valid" }
  ]
}`;

const diffRightState = `{
  "checkpoint_id": "chk_v17",
  "version": 17,
  "progress": { "completed": 3421, "pending": 6579 },
  "external_dependencies": [
    <span class="diff-mod">~ "resource": "dataset", "version": "v4" (CHANGED)</span>
  ],
  "decisions": [
    <span class="diff-del">- { "id": "dec_007", "status": "invalidated" } (INVALIDATED)</span>,
    <span class="diff-add">+ { "id": "dec_014", "decision": "Peer review filter", "status": "valid" }</span>
  ],
  "findings": [
    <span class="diff-add">+ { "id": "finding_127", "claim": "Correlation verified", "confidence": 0.94 }</span>
  ]
}`;

function initDiffViewer() {
  const leftEl = document.getElementById('diffLeftBox');
  const rightEl = document.getElementById('diffRightBox');

  if (leftEl && rightEl) {
    leftEl.textContent = diffLeftState;
    rightEl.innerHTML = diffRightState;
  }
}

// ---------------------------------------------------------------------------
// 3. Real-Time CONTINUUM-Bench Metric Calculator
// ---------------------------------------------------------------------------
function initCalculator() {
  const rangeInput = document.getElementById('calcRange');
  const turnsDisplay = document.getElementById('calcTurnsDisplay');
  const ratioDisplay = document.getElementById('calcRatioDisplay');
  const tokensSavedDisplay = document.getElementById('calcTokensSavedDisplay');
  const costSavedDisplay = document.getElementById('calcCostSavedDisplay');
  const actionsDisplay = document.getElementById('calcActionsDisplay');

  if (!rangeInput || !turnsDisplay) return;

  function calculate() {
    const turns = parseInt(rangeInput.value, 10);
    turnsDisplay.textContent = turns;

    // Est. 1,500 tokens context growth per execution turn vs 3,500 fixed recovery state
    const rawTokens = turns * 1500;
    const recoveryTokens = 3500;

    const ratio = (rawTokens / recoveryTokens).toFixed(1);
    const tokensSaved = Math.round((rawTokens - recoveryTokens) / 1000);
    const costSaved = ((rawTokens - recoveryTokens) / 1000000 * 5.0).toFixed(2);
    const actionsPrevented = Math.round(turns * 0.18);

    ratioDisplay.textContent = `${ratio}x`;
    tokensSavedDisplay.textContent = `${tokensSaved}k`;
    costSavedDisplay.textContent = `$${costSaved}`;
    actionsDisplay.textContent = actionsPrevented;
  }

  rangeInput.addEventListener('input', calculate);
  calculate();
}

// ---------------------------------------------------------------------------
// 4. Quickstart Code Tabs & Copy
// ---------------------------------------------------------------------------
const codeSnippets = {
  sdk: `# Python SDK Quickstart
from continuum import Continuum

# Initialize local SQLite storage
runtime = Continuum(storage="sqlite:///agent.db")

# Start a run
run = runtime.start(goal="Analyze 10,000 research documents")

# Record progress and findings
run.record_finding(claim="Strong correlation observed", confidence=0.94)
run.update_progress(completed=3421, pending=6579)

# Checkpoint semantic state
run.checkpoint()

# Record external side effects safely
run.record_action(type="github.create_issue", arguments={"title": "Bug found"})

# Resume after crash
recovered_run = runtime.resume("run_4821")
status = recovered_run.validate()

if status.safe:
    recovered_run.continue_execution()`,

  cli: `# CONTINUUM CLI Commands

# Initialize database
continuum init

# Start a new run
continuum run --goal "Analyze 10,000 documents"

# Create a checkpoint
continuum checkpoint

# Validate state against live environment
continuum validate run_4821

# Inspect state at specific version
continuum inspect run_4821 --version 17

# Diff two checkpoints
continuum diff checkpoint_v16 checkpoint_v17

# Resume safely from crash
continuum resume run_4821`,

  extractor: `# Custom Deterministic State Extractor
from continuum.state import StateExtractor

class CustomExtractor(StateExtractor):
    def extract(self, event_log, environment):
        # Deterministically extract semantic state from event prefix
        decisions = [
            e.payload for e in event_log.by_type("DECISION_CREATED")
        ]
        return {
            "decisions": decisions,
            "validated_at": environment.captured_at
        }`,

  events: `# Hash-Chained Event Log Audit
from continuum.events import EventLog

log = EventLog()

# Append sealed (SHA-256 chained) events
event1 = log.append(run_id="run_4821", type="RUN_STARTED")
event2 = log.append(run_id="run_4821", type="DECISION_CREATED", payload={...})

# Verify chain integrity (tamper detection)
report = log.verify(run_id="run_4821")
print(f"Chain healthy: {report.ok}")
print(f"Trusted through sequence: {report.trusted_through['run_4821']}")`
};

function initCodeTabs() {
  const tabs = document.querySelectorAll('.code-tab-btn');
  const codeBody = document.getElementById('codeBody');
  const copyBtn = document.getElementById('copyBtn');

  if (!tabs.length || !codeBody) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const tabKey = tab.getAttribute('data-tab');
      if (!codeSnippets[tabKey]) return;

      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      codeBody.textContent = codeSnippets[tabKey];
    });
  });

  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(codeBody.textContent).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => copyBtn.textContent = originalText, 2000);
      });
    });
  }
}

// ---------------------------------------------------------------------------
// 5. Architecture Hover Tooltips
// ---------------------------------------------------------------------------
function initArchTooltips() {
  const nodes = document.querySelectorAll('.arch-node');
  const titleEl = document.getElementById('archInfoTitle');
  const descEl = document.getElementById('archInfoDesc');

  if (!nodes.length || !titleEl) return;

  const nodeInfo = {
    agent: {
      title: "AI Agent Engine",
      desc: "Any agent framework (LangGraph, OpenAI SDK, custom python agent). Interacts exclusively through the lightweight CONTINUUM SDK."
    },
    stateEngine: {
      title: "State Projection Engine",
      desc: "Folds the append-only event log into a compact, versioned SemanticState tree (goals, findings, evidence, decisions)."
    },
    ledger: {
      title: "Idempotent Action Ledger",
      desc: "Tracks external API calls and side-effects. Intercepts duplicate calls on recovery and returns original cached results."
    },
    evidence: {
      title: "Evidence Registry",
      desc: "Maintains checksums and source references for all claims and decisions asserted by the agent."
    },
    checkpoint: {
      title: "Semantic Checkpoint",
      desc: "The minimal verified task snapshot. Replaces massive raw conversation dumps with versioned structured state."
    },
    validator: {
      title: "Environment Validator",
      desc: "Compares saved checkpoint against live environment (file hashes, dataset versions, permissions) before resuming."
    },
    contract: {
      title: "Recovery Contract",
      desc: "Deterministic machine-readable contract stipulating state validity, invalidated items, and next allowed recovery actions."
    }
  };

  nodes.forEach(node => {
    node.addEventListener('mouseenter', () => {
      const key = node.getAttribute('data-node');
      const info = nodeInfo[key];
      if (info) {
        titleEl.textContent = info.title;
        descEl.textContent = info.desc;
      }
    });
  });
}
