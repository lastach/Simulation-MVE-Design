import math
import random
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulation #2 — Designing & Running Early Experiments",
    page_icon="🧪",
    layout="wide",
)

# --------------------------------------------------------------------------------------
# Global targets / knobs (as agreed)
# --------------------------------------------------------------------------------------
TARGET_CPLP = 3.0               # Target Cost Per Learning Point (tokens per learning point)
TARGET_LEARNING_POINTS = 10     # Target learning points across the whole sim

# Seed for stability (still some randomness, but less jittery)
random.seed(42)

# --------------------------------------------------------------------------------------
# Session state helpers
# --------------------------------------------------------------------------------------
def init_state():
    if "stage" not in st.session_state:
        st.session_state.stage = "intro"
    if "idea_key" not in st.session_state:
        st.session_state.idea_key = None
    if "assumptions" not in st.session_state:
        st.session_state.assumptions = []  # all assumptions for selected idea
    if "ranked" not in st.session_state:
        st.session_state.ranked = []  # ordered copy for risk priority (learner edits)
    if "round" not in st.session_state:
        st.session_state.round = 1
    if "tokens_total" not in st.session_state:
        st.session_state.tokens_total = 30  # TOTAL pool across all 3 rounds
    if "tokens_spent" not in st.session_state:
        st.session_state.tokens_spent = 0   # consumed when a round actually runs
    if "portfolio" not in st.session_state:
        # scheduled tests: round -> list[(assumption_id, exp_key)]
        st.session_state.portfolio = {1: [], 2: [], 3: []}
    if "results" not in st.session_state:
        # realized results: round -> list[dict]
        st.session_state.results = {1: [], 2: [], 3: []}
    if "ground_truth" not in st.session_state:
        # assumption_id -> true risk level (1 low, 2 med, 3 high)
        st.session_state.ground_truth = {}
    if "validation_progress" not in st.session_state:
        # cumulative validated assumptions by type (increment on success)
        st.session_state.validation_progress = {
            "desirability": 0,
            "feasibility": 0,
            "viability": 0,
        }

init_state()

# --------------------------------------------------------------------------------------
# Idea cards & assumptions (ThermaLoop variants) — 3 cards, 6–9 assumptions each
# --------------------------------------------------------------------------------------
IDEAS = {
    "home_comfort": {
        "title": "Home Comfort Optimizer",
        "one_liner": "Smart vents + app to eliminate hot/cold rooms and reduce bills.",
        "assumptions": [
            {"id": "A1", "text": "Homeowners perceive uneven room temps as a top 3 comfort issue.", "type": "desirability"},
            {"id": "A2", "text": "≥20% of target homeowners will try a no-tools ‘one room fix’ kit.", "type": "desirability"},
            {"id": "A3", "text": "A single room kit can deliver a noticeable comfort delta in 48 hours.", "type": "feasibility"},
            {"id": "A4", "text": "BLE sensors + app can estimate room temp and airflow accurately enough.", "type": "feasibility"},
            {"id": "A5", "text": "Installed cost of starter kit ≤ $129 with ≥60% gross margin.", "type": "viability"},
            {"id": "A6", "text": "Homeowners will accept a subscription ($5–$9/mo) for seasonal tuning.", "type": "viability"},
            {"id": "A7", "text": "Return rate for the starter kit stays under 10%.", "type": "viability"},
            {"id": "A8", "text": "Install instructions can be done self-serve without pro help.", "type": "feasibility"},
        ],
        # truth risk: 3=very risky, 2=moderate, 1=low
        "truth": {"A1": 2, "A2": 3, "A3": 2, "A4": 1, "A5": 2, "A6": 3, "A7": 2, "A8": 1},
    },
    "landlord_energy": {
        "title": "Landlord Energy Saver",
        "one_liner": "LoRa sensors + portal for small landlords to cut HVAC waste and get rebates.",
        "assumptions": [
            {"id": "B1", "text": "Small landlords are willing to pilot a $0 down kit for 30 days.", "type": "desirability"},
            {"id": "B2", "text": "HVAC runtime can be reduced ≥10% without tenant complaints.", "type": "feasibility"},
            {"id": "B3", "text": "A property portal reduces landlord effort vs. spreadsheets.", "type": "desirability"},
            {"id": "B4", "text": "End-to-end logistics (ship, install, support) is manageable.", "type": "feasibility"},
            {"id": "B5", "text": "Gross margin ≥55% on device + ≥70% on SaaS at $6–$12/unit/mo.", "type": "viability"},
            {"id": "B6", "text": "Rebate paperwork & partner channel can acquire leads under $180 CAC.", "type": "viability"},
            {"id": "B7", "text": "Tenants won’t disable devices or complain about privacy.", "type": "desirability"},
            {"id": "B8", "text": "Landlords will sign annual agreements if payback ≤ 9 months.", "type": "viability"},
            {"id": "B9", "text": "Gateway connectivity (LoRa/LTE) works in ≥85% of buildings without site visit.", "type": "feasibility"},
        ],
        "truth": {"B1": 2, "B2": 3, "B3": 2, "B4": 2, "B5": 2, "B6": 3, "B7": 2, "B8": 2, "B9": 2},
    },
    "installer_tools": {
        "title": "Installer Pro Toolkit",
        "one_liner": "A pro kit + mobile app for HVAC installers to diagnose airflow issues fast.",
        "assumptions": [
            {"id": "C1", "text": "Installers see airflow diagnosis as a high-value differentiator.", "type": "desirability"},
            {"id": "C2", "text": "Pros will pre-order a kit at $299–$399 if it saves 30 min per job.", "type": "desirability"},
            {"id": "C3", "text": "Clamp sensors + app yield a clear pass/fail signal in < 5 minutes.", "type": "feasibility"},
            {"id": "C4", "text": "Kit COGS can hit ≤ $120 at pilot volumes.", "type": "viability"},
            {"id": "C5", "text": "Tool integrates with common thermostats for readings/logs.", "type": "feasibility"},
            {"id": "C6", "text": "Wholesale distributors will carry the kit with standard margin.", "type": "viability"},
            {"id": "C7", "text": "Pros actually use the tool in the field (not a shelf product).", "type": "desirability"},
            {"id": "C8", "text": "In-app ‘good/better/best’ recommendations reduce callbacks by ≥15%.", "type": "feasibility"},
            {"id": "C9", "text": "Field failure/return rate < 5% in first 90 days.", "type": "viability"},
        ],
        "truth": {"C1": 2, "C2": 3, "C3": 2, "C4": 2, "C5": 2, "C6": 2, "C7": 2, "C8": 2, "C9": 1},
    },
}

# Experiment menu: key -> (label, cost, days, description, good_for_types)
EXPERIMENTS: Dict[str, Dict] = {
    "landing": dict(
        label="Landing Page / Waitlist",
        cost=3,
        days=3,
        desc=("Publish a page stating value + offer with a clear CTA (e.g., ‘Join waitlist’). "
              "Drive a small trickle of traffic and measure visits/signups."),
        fit=["desirability", "viability"],
    ),
    "concierge": dict(
        label="Concierge Trial",
        cost=4,
        days=7,
        desc=("Manually deliver the experience to 1–5 users. "
              "Look for repeat intent (‘Would you do it again next week?’)."),
        fit=["desirability", "feasibility"],
    ),
    "wizard": dict(
        label="Wizard-of-Oz Prototype",
        cost=4,
        days=7,
        desc=("Fake the automation behind a clickable UI; observe if users reach value "
              "and where the workflow breaks."),
        fit=["feasibility", "desirability"],
    ),
    "preorder": dict(
        label="Pre-order / Deposit",
        cost=5,
        days=10,
        desc=("Ask for a deposit or card confirmation on a concrete offer. "
              "Stronger evidence of purchase intent and price acceptance."),
        fit=["viability", "desirability"],
    ),
    "expert": dict(
        label="Expert Interview",
        cost=2,
        days=2,
        desc=("Structured interviews with domain experts to uncover constraints and hidden costs."),
        fit=["feasibility", "viability"],
    ),
    "benchmark": dict(
        label="Benchmark vs Workaround",
        cost=3,
        days=5,
        desc=("Compare your approach against common workarounds on time/accuracy/comfort."),
        fit=["feasibility", "desirability"],
    ),
    "adsplit": dict(
        label="Ad Split Test",
        cost=4,
        days=5,
        desc=("Run 2–3 ad variants to the same audience; see which message earns more qualified clicks."),
        fit=["desirability"],
    ),
    "diary": dict(
        label="Diary Study / Usage Log",
        cost=3,
        days=7,
        desc=("Ask a handful of users to log pain episodes or usage for a week. Quantifies frequency/triggers."),
        fit=["desirability"],
    ),
}

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------
def next_stage(s: str):
    st.session_state.stage = s

def set_idea(key: str):
    """Choose idea, randomize starting assumption order, reset state."""
    st.session_state.idea_key = key
    idea = IDEAS[key]
    shuffled = idea["assumptions"].copy()
    random.shuffle(shuffled)  # randomize initial order so learner must reorder
    st.session_state.assumptions = shuffled
    st.session_state.ranked = shuffled.copy()
    st.session_state.ground_truth = idea["truth"].copy()
    st.session_state.round = 1
    st.session_state.tokens_spent = 0
    st.session_state.portfolio = {1: [], 2: [], 3: []}
    st.session_state.results = {1: [], 2: [], 3: []}
    st.session_state.validation_progress = {"desirability": 0, "feasibility": 0, "viability": 0}
    next_stage("rank")

def get_assumption(aid: str) -> dict:
    for a in st.session_state.assumptions:
        if a["id"] == aid:
            return a
    return {"id": aid, "text": aid, "type": "desirability"}

def move_item(idx: int, direction: int):
    items = st.session_state.ranked
    new_idx = idx + direction
    if 0 <= new_idx < len(items):
        items[idx], items[new_idx] = items[new_idx], items[idx]

def planned_spend() -> int:
    """Tokens spent (completed rounds) + tokens scheduled (all rounds, not yet run)."""
    scheduled_cost = 0
    for rnd in (1, 2, 3):
        for (_, ek) in st.session_state.portfolio[rnd]:
            scheduled_cost += EXPERIMENTS[ek]["cost"]
    return st.session_state.tokens_spent + scheduled_cost

def pool_remaining() -> int:
    return st.session_state.tokens_total - planned_spend()

def to_badge(txt: str, color: str = "#666"):
    st.markdown(
        f"<span style='padding:2px 8px;border-radius:12px;background:{color};color:#fff;font-size:0.85rem'>{txt}</span>",
        unsafe_allow_html=True,
    )

def stepper():
    cols = st.columns(10)
    steps = [
        "Intro",
        "Choose Idea",
        "Rank Risks",
        "Round 1 — Select",
        "Round 1 — Results",
        "Round 2 — Select",
        "Round 2 — Results",
        "Round 3 — Select",
        "Round 3 — Results",
        "Learning & Score",
    ]
    idx_map = {
        "intro": 0,
        "choose": 1,
        "rank": 2,
        "r1_select": 3,
        "r1_results": 4,
        "r2_select": 5,
        "r2_results": 6,
        "r3_select": 7,
        "r3_results": 8,
        "score": 9,
    }
    active_idx = idx_map.get(st.session_state.stage, 0)
    for i, c in enumerate(cols):
        with c:
            style = (
                "background:#eef6ff;border:1px solid #cde;"
                if i == active_idx
                else "background:#f7f7f9;border:1px solid #eee;"
            )
            st.markdown(
                f"""
                <div style="{style}padding:8px 10px;border-radius:10px;text-align:center;min-height:56px">
                {steps[i]}
                </div>
                """,
                unsafe_allow_html=True,
            )

# --------------------------------------------------------------------------------------
# Quant results generator per experiment (learner-facing numbers)
# --------------------------------------------------------------------------------------
def quant_for_experiment(exp_key: str, rng: random.Random) -> str:
    if exp_key == "landing":
        visits = rng.randint(800, 1500)
        signups = rng.randint(20, 120)
        rate = round(signups / visits * 100, 1)
        return f"{visits:,} visits → {signups} sign-ups ({rate}%)."
    if exp_key == "adsplit":
        imps = rng.randint(900, 2000)
        ctr_a = round(2.8 + 2.5 * rng.random(), 1)
        ctr_b = round(ctr_a * (0.85 + 0.3 * rng.random()), 1)
        winner = "A" if ctr_a >= ctr_b else "B"
        win_ctr = ctr_a if winner == "A" else ctr_b
        return f"{imps:,} impressions — variant {winner} higher CTR ({win_ctr}%)."
    if exp_key == "concierge":
        trials = rng.randint(3, 6)
        would_pay = rng.randint(max(1, trials // 2), trials)
        repeat = rng.randint(0, would_pay)
        return f"{would_pay} of {trials} would pay again; {repeat} repeated use."
    if exp_key == "preorder":
        visitors = rng.randint(120, 300)
        confirmed = rng.randint(1, 12)
        return f"{confirmed} confirmed cards from {visitors} visitors."
    if exp_key == "wizard":
        sessions = rng.randint(6, 14)
        tasks = rng.randint(max(2, sessions // 3), sessions)
        ttv = rng.randint(6, 18)
        return f"{tasks}/{sessions} tasks completed; time-to-value ≈ {ttv} min."
    if exp_key == "expert":
        experts = rng.randint(3, 6)
        converge = rng.randint(max(1, experts // 3), experts)
        return f"{experts} experts; {converge} converged on feasibility/cost drivers."
    if exp_key == "benchmark":
        ours = rng.randint(8, 18)
        workaround = ours + rng.randint(-3, 6)
        delta = workaround - ours
        better = "faster" if delta > 0 else "slower"
        return f"Our method {abs(delta)} min {better} than workaround ({ours} vs {workaround} min)."
    if exp_key == "diary":
        participants = rng.randint(4, 8)
        episodes = rng.randint(participants * 3, participants * 10)
        avg = round(episodes / participants, 1)
        return f"{participants} participants logged {episodes} pain episodes (avg {avg}/person)."
    return "—"

# --------------------------------------------------------------------------------------
# Simulation engine (more deterministic when aligned)
# --------------------------------------------------------------------------------------
def simulate_result(aid: str, ek: str, rng: random.Random) -> dict:
    """Simulate a single test result, including quant, time, and cost."""
    a = get_assumption(aid)
    e = EXPERIMENTS[ek]
    risk = st.session_state.ground_truth.get(aid, 2)  # 1..3
    fit = 1 if a["type"] in e["fit"] else 0

    # Raised base success chance + stronger fit boost, capped at 0.95
    base_success = {3: 0.35, 2: 0.55, 1: 0.75}[risk]
    p = base_success + 0.25 * fit
    p = min(p, 0.95)
    success = rng.random() < p

    # Signal more deterministic: fit tends to strong
    if not success:
        signal = "no-signal"
    else:
        signal = "strong" if (fit and rng.random() < 0.8) else "weak"

    quant_line = quant_for_experiment(ek, rng)
    note = synth_result_note(aid, ek, success, signal)

    return dict(
        aid=aid,
        experiment=ek,
        success=success,
        signal=signal,
        note=note,
        quant=quant_line,
        cost=e["cost"],
        days=e["days"],
        assumption_type=a["type"],
        fit=fit,
    )

def synth_result_note(aid: str, ek: str, success: bool, signal: str) -> str:
    a = get_assumption(aid)
    e = EXPERIMENTS[ek]
    stem = f"**{e['label']}** — "
    if success:
        return stem + (f"strongly supports “{a['text']}”." if signal == "strong" else f"weakly supports “{a['text']}”.")
    return stem + f"did not support “{a['text']}” this round."

def run_round(round_idx: int):
    """Run all scheduled tests in a round. Parallelism ⇒ time = max(days) in the round."""
    rng = random.Random(100 + round_idx)  # stable-ish per round
    results = []
    for (aid, ek) in st.session_state.portfolio[round_idx]:
        r = simulate_result(aid, ek, rng)
        results.append(r)
        st.session_state.tokens_spent += EXPERIMENTS[ek]["cost"]
        if r["success"]:
            st.session_state.validation_progress[r["assumption_type"]] += 1
    st.session_state.results[round_idx] = results
    # After running, clear scheduled list for that round (already accounted for in tokens_spent)
    st.session_state.portfolio[round_idx] = []

# --------------------------------------------------------------------------------------
# Resource efficiency & scoring helpers
# --------------------------------------------------------------------------------------
def resource_efficiency():
    """
    Efficiency based on Cost Per Learning Point (CPLP).
    - learning_points = strong*2 + weak*1
    - actual_cplp = total_cost / learning_points  (if learning_points == 0 ⇒ ∞)
    - efficiency_pct = min(100, 100 * TARGET_CPLP / actual_cplp)
    Returns: (score_0_25, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak)
    """
    total_cost = sum(r["cost"] for rnd in (1, 2, 3) for r in st.session_state.results[rnd])
    # Within a round, tests run in parallel → time = max(days) in that round
    total_time = sum(max([r["days"] for r in st.session_state.results[rnd]] or [0]) for rnd in (1, 2, 3))
    strong = sum(1 for rnd in (1, 2, 3) for r in st.session_state.results[rnd] if r["signal"] == "strong")
    weak = sum(1 for rnd in (1, 2, 3) for r in st.session_state.results[rnd] if r["signal"] == "weak")
    learning_points = strong * 2 + weak * 1

    if learning_points <= 0:
        actual_cplp = float("inf")
        efficiency_pct = 0.0
        score = 0
        return score, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak

    actual_cplp = total_cost / learning_points
    efficiency_pct = min(100.0, 100.0 * TARGET_CPLP / actual_cplp)
    score = round(25 * (efficiency_pct / 100.0))  # map 0–100% → 0–25 points
    return score, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak

def risk_prioritization_score() -> Tuple[int, float, float, dict]:
    """
    Full-ranking scoring you specified:
      - For each ranked position i (1..N):
          base points = 3 if exact, 2 if off by 1, 1 if off by 2, else 0
          weight = 2.0 if i<=3; 1.5 if 4<=i<=6; 1.0 if i>=7
      - Sum(base*weight) = achieved_points
      - Max points = sum(3*weight) across i
      - Category score (0–25) = 25 * (achieved_points / max_points)
    """
    ranked_ids = [a["id"] for a in st.session_state.ranked]
    truth = st.session_state.ground_truth
    # Build ground-truth ranking (1..N), tie-broken stably by ID
    truth_sorted = sorted(truth.items(), key=lambda kv: (-kv[1], kv[0]))
    truth_rank = {aid: idx + 1 for idx, (aid, _) in enumerate(truth_sorted)}
    N = len(ranked_ids)

    def weight_for_pos(pos: int) -> float:
        if pos <= 3:
            return 2.0
        if pos <= 6:
            return 1.5
        return 1.0

    achieved = 0.0
    max_points = 0.0
    exact_ct = near1_ct = near2_ct = 0
    per_item = []
    for i, aid in enumerate(ranked_ids, start=1):
        j = truth_rank.get(aid, N)  # ground-truth rank
        dist = abs(i - j)
        base = 3 if dist == 0 else 2 if dist == 1 else 1 if dist == 2 else 0
        if base == 3:
            exact_ct += 1
        elif base == 2:
            near1_ct += 1
        elif base == 1:
            near2_ct += 1
        w = weight_for_pos(i)
        achieved += base * w
        max_points += 3 * w
        per_item.append((i, aid, base, w, j))

    score = int(round(25 * (achieved / max_points))) if max_points > 0 else 0
    details = {
        "exact_matches": exact_ct,
        "within_one": near1_ct,
        "within_two": near2_ct,
        "items": per_item,  # tuples of (user_pos, aid, base_points, weight, truth_pos)
    }
    return score, achieved, max_points, details

def compute_score() -> Tuple[int, Dict[str, int], Dict[str, str], List[str], List[str]]:
    # Risk Prioritization (0–25) — full ranking method
    risk_prior, rp_achieved, rp_max, rp_details = risk_prioritization_score()

    # Experiment Fit (0–25): proportion of COMPLETED tests whose type matches assumption type
    total_results = 0
    good_results = 0
    for rnd in (1, 2, 3):
        for r in st.session_state.results[rnd]:
            total_results += 1
            if r["assumption_type"] in EXPERIMENTS[r["experiment"]]["fit"]:
                good_results += 1
    exp_fit = int(25 * (good_results / total_results)) if total_results else 0

    # Resource Efficiency (0–25) — CPLP target/actual
    eff, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak = resource_efficiency()

    # Learning Outcome (0–15): strong=2, weak=1 (cap 15)
    learn = min(15, learning_points)

    # Assumption Quality (0–10): diversity among top 5
    ranked_ids = [a["id"] for a in st.session_state.ranked]
    diversity = len(set(get_assumption(aid)["type"] for aid in ranked_ids[:5]))
    qual = 6 + (4 if diversity >= 2 else 0)

    total_score = min(100, risk_prior + exp_fit + eff + learn + qual)

    # reasons (aligned one-to-one with categories)
    reasons = {
        "Assumption Quality": f"Top 5 include {diversity} distinct risk types.",
        "Risk Prioritization": (
            f"Full-order match score: {rp_achieved:.1f}/{rp_max:.1f} "
            f"(exact={rp_details['exact_matches']}, ±1={rp_details['within_one']}, ±2={rp_details['within_two']})."
        ),
        "Experiment Fit": f"{good_results}/{total_results} completed tests matched assumption type (fit-aligned).",
        "Resource Efficiency": (
            f"CPLP target={TARGET_CPLP:.2f}, actual={actual_cplp:.2f} ⇒ efficiency {efficiency_pct:.0f}% "
            f"(maps to 0–25)."
        ),
        "Learning Outcome": f"Signals: strong={strong} (×2), weak={weak} (×1) ⇒ {learning_points} pts "
                            f"(target={TARGET_LEARNING_POINTS}).",
    }

    # For details table, show top 3 user picks and ground-truth top 3 (by text)
    def ids_to_texts(ids):
        out = []
        for aid in ids:
            a = get_assumption(aid)
            out.append(f"{aid}: {a['text']}")
        return out
    truth_sorted = sorted(st.session_state.ground_truth.items(), key=lambda kv: (-kv[1], kv[0]))
    true_top3 = [aid for aid, _ in truth_sorted[:3]]
    user_top3 = ranked_ids[:3]

    breakdown = {
        "Assumption Quality": qual,     # /10
        "Risk Prioritization": risk_prior,  # /25
        "Experiment Fit": exp_fit,      # /25
        "Resource Efficiency": eff,     # /25
        "Learning Outcome": learn,      # /15
    }
    return total_score, breakdown, reasons, true_top3, user_top3

# --------------------------------------------------------------------------------------
# UI Screens
# --------------------------------------------------------------------------------------
def screen_intro():
    stepper()
    st.title("Simulation #2 — Designing & Running Early Experiments")
    st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly.")
    st.subheader("What you’ll do")
    st.markdown(
        """
1) **Choose a seed idea**.  
2) **Rank** 6–10 assumptions from *riskiest to least risky*.  
3) Across **three rounds**, spend from your **total token budget** to run scrappy tests (be intentional so you have tokens left for later rounds).  
4) Review **quant results**, track **cumulative validation**, and iterate.  
5) See your **score** with targeted coaching notes.
"""
    )
    st.info("**Tokens (30) are a single pool across all rounds.** Within a round, tests run in parallel; round time = the longest test.")
    st.button("Start", type="primary", on_click=lambda: next_stage("choose"))

def screen_choose():
    stepper()
    st.subheader("Pick your idea to test")
    cols = st.columns(3)

    def idea_card(key: str, col):
        idea = IDEAS[key]
        with col:
            st.markdown(f"### {idea['title']}")
            st.caption(idea["one_liner"])
            with st.expander("Show initial assumptions", expanded=False):
                for a in idea["assumptions"]:
                    st.markdown(f"- {a['text']}  _({a['type']})_")
            st.button("Choose", key=f"pick_{key}", on_click=lambda k=key: set_idea(k), type="primary", use_container_width=True)

    idea_card("home_comfort", cols[0])
    idea_card("landlord_energy", cols[1])
    idea_card("installer_tools", cols[2])

def screen_rank():
    stepper()
    st.subheader("Rank your assumptions (highest → lowest risk)")
    st.caption("Use the ▲▼ buttons to reorder. Put the **riskiest** items at the **top**.")
    items = st.session_state.ranked

    for i, a in enumerate(items):
        cols = st.columns([0.06, 0.06, 0.88])
        with cols[0]:
            st.button("▲", key=f"up_{i}", on_click=lambda idx=i: move_item(idx, -1))
        with cols[1]:
            st.button("▼", key=f"dn_{i}", on_click=lambda idx=i: move_item(idx, +1))
        with cols[2]:
            to_badge(a["type"], "#3a7")
            st.markdown(f"**{a['id']}** — {a['text']}")

    st.divider()
    st.button("Next: Round 1 — Select Tests", type="primary", on_click=lambda: next_stage("r1_select"))

def screen_round_select(round_idx: int):
    stepper()
    st.subheader(f"Round {round_idx} — Select your experiments")
    st.caption("Be intentional — keep tokens for later rounds. Within a round, tests run in parallel; time = the longest test.")

    # tokens (pool)
    remaining = pool_remaining()
    to_badge(f"Total token budget (all rounds): {st.session_state.tokens_total}", "#295")
    st.write(" ")
    to_badge(f"Remaining now (scheduled + spent considered): {remaining}", "#295")

    # show ranked list with selector of experiments
    ranked = st.session_state.ranked
    st.markdown("##### Assumptions (your order)")
    for a in ranked:
        with st.expander(f"{a['id']} — {a['text']}", expanded=False):
            st.caption(f"Type: **{a['type']}**")
            cols = st.columns(4)
            keys = list(EXPERIMENTS.keys())
            for i, ek in enumerate(keys):
                card = EXPERIMENTS[ek]
                with cols[i % 4]:
                    st.markdown(
                        f"**{card['label']}**  \n_{card['desc']}_  \nCost: **{card['cost']}**, Duration: **{card['days']}d**"
                    )
                    if st.button(f"Add → {a['id']}", key=f"add_{round_idx}_{a['id']}_{ek}"):
                        # enforce strict 30-token cap including scheduled-but-not-run tests
                        if planned_spend() + card["cost"] <= st.session_state.tokens_total:
                            st.session_state.portfolio[round_idx].append((a["id"], ek))
                            st.toast(f"Added {card['label']} for {a['id']}")
                        else:
                            st.warning("Not enough total tokens remaining.")

    st.divider()
    scheduled = st.session_state.portfolio[round_idx]
    if scheduled:
        st.markdown("#### Scheduled this round")
        # Show with remove buttons
        for idx, (aid, ek) in enumerate(list(scheduled)):
            card = EXPERIMENTS[ek]
            c1, c2, c3, c4, c5 = st.columns([0.25, 0.35, 0.15, 0.15, 0.10])
            with c1:
                st.write(f"**{aid}**")
            with c2:
                st.write(card["label"])
            with c3:
                st.write(f"Cost: {card['cost']}")
            with c4:
                st.write(f"Days: {card['days']}")
            with c5:
                if st.button("✖️ Remove", key=f"rm_{round_idx}_{idx}"):
                    st.session_state.portfolio[round_idx].pop(idx)
                    st.experimental_rerun()
    else:
        st.info("No tests scheduled yet.")

    can_run = len(scheduled) > 0
    if can_run:
        st.button(
            f"Run Round {round_idx}",
            type="primary",
            on_click=lambda r=round_idx: (run_round(r), next_stage(f"r{r}_results")),
        )
    else:
        st.button(f"Run Round {round_idx}", disabled=True)

def show_validation_table():
    """Cumulative validation as a table (no chart)."""
    totals = {"desirability": 0, "feasibility": 0, "viability": 0}
    for a in st.session_state.assumptions:
        totals[a["type"]] += 1
    prog = st.session_state.validation_progress
    rows = []
    for t in ["desirability", "feasibility", "viability"]:
        validated = prog.get(t, 0)
        total = totals.get(t, 0)
        pct = (validated / total * 100) if total else 0
        rows.append({"Assumption Type": t.title(), "Validated": validated, "Total": total, "Completion %": round(pct, 1)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

def screen_round_results(round_idx: int):
    stepper()
    st.subheader(f"Round {round_idx} — Results")

    res = st.session_state.results[round_idx]
    if not res:
        st.warning("No results recorded. Go back and schedule tests.")
        return

    # show each result card with quant + signal
    for r in res:
        a = get_assumption(r["aid"])
        e = EXPERIMENTS[r["experiment"]]
        box = st.container(border=True)
        with box:
            st.markdown(f"**{a['id']}** — {a['text']}")
            st.markdown(
                f"**Experiment:** {e['label']}  \n"
                f"**Outcome:** {'✅ Success' if r['success'] else '❌ No evidence'}  \n"
                f"**Signal:** {r['signal']}"
            )
            st.markdown(f"*{r['quant']}*")
            st.caption(r["note"])

    # cumulative validation progress (table)
    st.divider()
    st.markdown("#### Cumulative Validation Progress")
    show_validation_table()
    st.caption("Progress accumulates across rounds, by assumption type.")

    st.divider()
    if round_idx < 3:
        st.button("Next Round — Select", type="primary", on_click=lambda r=round_idx + 1: next_stage(f"r{r}_select"))
    else:
        st.button("See Learning Summary & Score", type="primary", on_click=lambda: next_stage("score"))

# --------------------------------------------------------------------------------------
# Scoring & Feedback screen
# --------------------------------------------------------------------------------------
def screen_score():
    stepper()
    st.subheader("Learning Summary & Score")

    total, breakdown, reasons, true_top3, user_top3 = compute_score()

    # Show total and table with /100 aligned reasons
    st.metric("Total Score (0–100)", total)
    ordered = ["Assumption Quality", "Risk Prioritization", "Experiment Fit", "Resource Efficiency", "Learning Outcome"]
    weights = {
        "Assumption Quality": 10,
        "Risk Prioritization": 25,
        "Experiment Fit": 25,
        "Resource Efficiency": 25,
        "Learning Outcome": 15,
    }
    rows = []
    for cat in ordered:
        raw = breakdown.get(cat, 0)
        out100 = round(100 * raw / weights[cat]) if weights[cat] else 0
        rows.append({"Category": cat, "Score (/100)": out100, "Why you scored this way": reasons.get(cat, "—")})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Clarify Risk Prioritization mapping (show top 3 by full text)
    def ids_to_texts(ids):
        out = []
        for aid in ids:
            a = get_assumption(aid)
            out.append(f"{aid}: {a['text']}")
        return out

    st.markdown("#### Risk Prioritization Details (Top 3 shown for reference)")
    st.write("- **Your Top 3:**")
    for line in ids_to_texts(user_top3):
        st.write(f"  - {line}")
    st.write("- **Ground-Truth Top 3:**")
    for line in ids_to_texts(true_top3):
        st.write(f"  - {line}")
    st.caption("Category score uses the full ranking with proximity & weights (1–3× base; 2× top3, 1.5× ranks 4–6).")

    # Cumulative time & money summary + learning points and CPLP
    eff_score, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak = resource_efficiency()
    st.markdown("#### Cumulative Time & Money Summary")
    st.write(f"- **Total tokens spent:** {st.session_state.tokens_spent}/{st.session_state.tokens_total}")
    st.write(f"- **Total elapsed time:** {total_time} days (sum of the longest test each round)")
    st.write(f"- **Learning points:** {learning_points} (strong={strong}×2, weak={weak}×1) | **Target:** {TARGET_LEARNING_POINTS}")
    if learning_points > 0 and actual_cplp != float('inf'):
        st.write(f"- **Cost per learning point (CPLP):** actual {actual_cplp:.2f} tokens vs target {TARGET_CPLP:.2f} tokens")
        st.write(f"- **Efficiency:** {efficiency_pct:.0f}% of target (maps to 0–25 Resource Efficiency)")
    else:
        st.write("- **Cost per learning point (CPLP):** — (no learning points yet)")

    # Coaching notes (updated for CPLP model & sequencing)
    st.divider()
    st.markdown("#### Coaching Notes")
    notes = []
    if breakdown["Risk Prioritization"] < 17:  # < ~70/100
        notes.append("Revisit your **risk ranking** — push uncertain desirability assumptions to the top early.")
    if breakdown["Experiment Fit"] < 17:
        notes.append("Improve **test–assumption fit** — intent tests for demand, workflow/latency for feasibility, price/preorder for viability.")
    if eff_score < 14:
        notes.append("Lower your **CPLP** — prefer quicker/cheaper tests that still yield strong signals; bundle tests within a round to keep time down.")
    if breakdown["Learning Outcome"] < 10:
        notes.append(f"Increase **learning yield** — aim for {TARGET_LEARNING_POINTS}+ points with stronger signals (pre-orders, repeat use).")
    diversity = len(set(get_assumption(aid)["type"] for aid in [a["id"] for a in st.session_state.ranked[:5]]))
    if diversity < 2:
        notes.append("Diversify your **top five** across desirability, feasibility, and viability.")
    if pool_remaining() > 0:
        notes.append(f"You ended with **{pool_remaining()} tokens** unallocated. Reserve some, but avoid chronic under-testing early.")
    if not notes:
        notes.append("Excellent balance. Your sequencing, fit, and CPLP are strong — this is textbook early validation.")
    for n in notes:
        st.write(f"- {n}")

    st.success("Simulation complete. Refresh to try a different idea or ranking strategy.")
    st.button("Restart", on_click=lambda: next_stage("intro"))

# --------------------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------------------
def router():
    s = st.session_state.stage
    if s == "intro":
        screen_intro()
    elif s == "choose":
        screen_choose()
    elif s == "rank":
        screen_rank()
    elif s == "r1_select":
        screen_round_select(1)
    elif s == "r1_results":
        screen_round_results(1)
    elif s == "r2_select":
        screen_round_select(2)
    elif s == "r2_results":
        screen_round_results(2)
    elif s == "r3_select":
        screen_round_select(3)
    elif s == "r3_results":
        screen_round_results(3)
    elif s == "score":
        screen_score()
    else:
        screen_intro()

# --------------------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------------------
router()
