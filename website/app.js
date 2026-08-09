// CONTINUUM Website Interactive Script

document.addEventListener('DOMContentLoaded', () => {
  initSimulator();
  initCodeTabs();
  initCalculator();
  initArchInteractivity();
});

// ---------------------------------------------------------------------------
// 1. Live Fault Recovery Simulator
// ---------------------------------------------------------------------------
const scenarios = {
  crash: {
    title: "Process Crash / Restart",
    output: `<span class="term-dim">$ continuum resume run_4821</span>

<span class="term-highlight">CONTINUUM RECOVERY ENGINE</span>
Run ID: run_4821
Checkpoint Version: v17 (SHA-256: 8f3a92b1...)

<span class="term-dim">--- State Audit ---</span>
<span class="term-ok">[OK]</span> Goal: "Analyze 10,000 research documents"
<span class="term-ok">[OK]</span> Progress: 3,421 completed, 6,579 pending
<span class="term-ok">[OK]</span> 127 findings preserved (100% evidence verified)
<span class="term-ok">[OK]</span> 14 decisions valid
<span class="term-ok">[OK]</span> Action Ledger: 8 side effects verified (0 duplicated)

<span class="term-dim">--- Recovery Decision ---</span>
Status: <span class="term-ok">SAFE_TO_RESUME</span>
Mode: RESUME
Next permitted action: process_batch(start_index=3422)

<span class="term-ok">✓ Task resumed from verified progress. Zero duplicated work.</span>`
  },

  dataset: {
    title: "Environment Shift (Dataset v3 -> v4)",
    output: `<span class="term-dim">$ continuum resume run_4821</span>

<span class="term-highlight">CONTINUUM RECOVERY ENGINE</span>
Run ID: run_4821
Checkpoint Version: v17

<span class="term-dim">--- Environment Snapshot Audit ---</span>
<span class="term-ok">[OK]</span> Goal & Progress verified
<span class="term-err">[FAIL] Dependency Mismatch</span>: Resource 'dataset' changed from v3 -> v4
<span class="term-warn">[STALE]</span> 4 findings tied to dataset v3 marked REQUIRES_REVALIDATION
<span class="term-warn">[INVALIDATED]</span> Decision #7 ('Only subset A analyzed') invalidated

<span class="term-dim">--- Recovery Contract Generated ---</span>
Recovery Status: <span class="term-warn">REQUIRES_REPAIR</span>
Mode: REPAIR_AND_RESUME
Invalidated: ["dataset_v3", "decision_7"]
Required Action: "Revalidate experiments 14-17 against dataset v4"
Next Allowed Action: dataset_revalidation

<span class="term-warn">⚠ State validation caught environment shift. Unsafe replay prevented.</span>`
  },

  model: {
    title: "Model Switch (GPT-4 -> Claude 3.5)",
    output: `<span class="term-dim">$ continuum resume run_4821 --model claude-3-5-sonnet</span>

<span class="term-highlight">CONTINUUM RECOVERY ENGINE</span>
Run ID: run_4821
Checkpoint Version: v17

<span class="term-dim">--- Model Transition Audit ---</span>
Previous Model: gpt-4o (provider: openai)
Target Model: claude-3-5-sonnet (provider: anthropic)

<span class="term-warn">[MODEL_SPECIFIC_STATE]</span> Item 'prompt_formatting_v1' requires re-eval
<span class="term-ok">[OK]</span> Task Goal, Verified Progress, Findings, and Evidence preserved
<span class="term-ok">[OK]</span> Bounded recovery context reconstructed (4,200 tokens vs 182,000 original)

<span class="term-dim">--- Recovery Decision ---</span>
Status: <span class="term-ok">SAFE_TO_RESUME</span>
Mode: RESUME (Framework-Agnostic Context Transferred)

<span class="term-ok">✓ Switched models safely without replaying prompt history.</span>`
  },

  sideeffect: {
    title: "Uncertain Side-Effect Guard",
    output: `<span class="term-dim">$ continuum resume run_4821</span>

<span class="term-highlight">CONTINUUM ACTION LEDGER RECONCILIATION</span>
Run ID: run_4821
Last Action: action_812 ("github.create_issue")

<span class="term-err">[UNKNOWN_SIDE_EFFECT]</span> Process terminated during API write.
Action state: STARTED (completion unconfirmed by server ack).

<span class="term-dim">--- Reconciliation Guard ---</span>
Action ID: action_812
Arguments Hash: e3b0c442...
Outcome: UNCERTAIN

Status: <span class="term-warn">REQUIRES_HUMAN</span>
Action: Execution halted to prevent double-posting issue.

<span class="term-err">❌ Automatic retry blocked to protect external system idempotency.</span>`
  }
};

function initSimulator() {
  const simOutput = document.getElementById('simOutput');
  const buttons = document.querySelectorAll('.sim-btn');

  if (!simOutput || !buttons.length) return;

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const scenarioKey = btn.getAttribute('data-scenario');
      const data = scenarios[scenarioKey];
      if (!data) return;

      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      simOutput.innerHTML = data.output;
    });
  });
}

// ---------------------------------------------------------------------------
// 2. Code Snippet Tabs
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

# Start a run
continuum run --goal "Analyze documents"

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
  const tabs = document.querySelectorAll('.tab-btn');
  const codeDisplay = document.getElementById('codeDisplay');
  const copyBtn = document.getElementById('copyBtn');

  if (!tabs.length || !codeDisplay) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const tabKey = tab.getAttribute('data-tab');
      if (!codeSnippets[tabKey]) return;

      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      codeDisplay.textContent = codeSnippets[tabKey];
    });
  });

  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(codeDisplay.textContent).then(() => {
        const origText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => copyBtn.textContent = origText, 2000);
      });
    });
  }
}

// ---------------------------------------------------------------------------
// 3. Benchmark Compression Calculator
// ---------------------------------------------------------------------------
function initCalculator() {
  const turnsInput = document.getElementById('turnsInput');
  const turnsVal = document.getElementById('turnsVal');
  const tokensVal = document.getElementById('tokensVal');
  const compRatioVal = document.getElementById('compRatioVal');
  const costSavedVal = document.getElementById('costSavedVal');

  if (!turnsInput || !turnsVal) return;

  function updateCalc() {
    const turns = parseInt(turnsInput.value, 10);
    turnsVal.textContent = turns.toLocaleString();

    // Est context growth: ~1,500 tokens per turn
    const rawTokens = turns * 1500;
    // CONTINUUM semantic checkpoint: ~3,500 tokens fixed
    const recoveryTokens = 3500;

    const ratio = (rawTokens / recoveryTokens).toFixed(1);
    // Est cost at $5 per 1M tokens (GPT-4o blend)
    const costSaved = ((rawTokens - recoveryTokens) / 1000000 * 5.0).toFixed(2);

    tokensVal.textContent = (rawTokens / 1000).toFixed(0) + 'k';
    compRatioVal.textContent = `${ratio}x`;
    costSavedVal.textContent = `$${costSaved}`;
  }

  turnsInput.addEventListener('input', updateCalc);
  updateCalc();
}

// ---------------------------------------------------------------------------
// 4. Interactive Architecture Hover Tooltips
// ---------------------------------------------------------------------------
function initArchInteractivity() {
  const nodes = document.querySelectorAll('.arch-node');
  const infoTitle = document.getElementById('archInfoTitle');
  const infoDesc = document.getElementById('archInfoDesc');

  if (!nodes.length || !infoTitle) return;

  const nodeInfo = {
    agent: {
      title: "AI Agent Engine",
      desc: "Any agent framework (LangGraph, OpenAI SDK, custom agent). Interacts exclusively through the lightweight CONTINUUM SDK."
    },
    stateEngine: {
      title: "State Projection Engine",
      desc: "Folds the event log into a compact, versioned SemanticState tree (goals, findings, evidence, decisions)."
    },
    ledger: {
      title: "Idempotent Action Ledger",
      desc: "Tracks external API calls and side-effects. Prevents double-execution on crash recovery."
    },
    evidence: {
      title: "Evidence Registry",
      desc: "Maintains checksums and source references for all claims asserted by the agent."
    },
    checkpoint: {
      title: "Semantic Checkpoint",
      desc: "The minimal verified task snapshot. Replaces massive raw conversation dumps."
    },
    validator: {
      title: "Environment Validator",
      desc: "Compares checkpoint against live environment (file hashes, dataset versions, permissions) before resuming."
    },
    contract: {
      title: "Recovery Contract",
      desc: "Machine-readable contract stipulating state validity, invalidated items, and next allowed actions."
    }
  };

  nodes.forEach(node => {
    node.addEventListener('mouseenter', () => {
      const key = node.getAttribute('data-node');
      const info = nodeInfo[key];
      if (info) {
        infoTitle.textContent = info.title;
        infoDesc.textContent = info.desc;
      }
    });
  });
}
