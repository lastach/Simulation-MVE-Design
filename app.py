import math
import random
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------------------
# Basic page setup
# --------------------------------------------------------------------------------------
st.set_page_config(page_title="Simulation #2 — Designing & Running Early Experiments",
                   page_icon="🧪", layout="wide")

# --------------------------------------------------------------------------------------
# Helper: session state
# --------------------------------------------------------------------------------------
def init_state():
    if "stage" not in st.session_state:
        st.session_state.stage = "intro"
    if "idea_key" not in st.session_state:
        st.session_state.idea_key = None
    if "assumptions" not in st.session_state:
        st.session_state.assumptions = []      # list[dict]
    if "ranked" not in st.session_state:
        st.session_state.ranked = []           # same items ordered
    if "round" not in st.session_state:
        st.session_state.round = 1
    # ----- CHANGE: single carryover pool instead of per-round buckets -----
    if "tokens_pool" not in st.session_state:
        # Sum of your old per-round amounts (12+10+8) = 30
        st.session_state.tokens_pool = 30
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = {1: [], 2: [], 3: []}  # list of (assumption_id, exp_key)
    if "results" not in st.session_state:
        st.session_state.results = {1: [], 2: [], 3: []}    # list of dicts per round
    if "ground_truth" not in st.session_state:
        st.session_state.ground_truth = {}     # assumption_id -> true risk level
    if "risk_ranking" not in st.session_state:
        st.session_state.risk_ranking = []     # list of (assumption_id, user_rank)
    if "learned" not in st.session_state:
        st.session_state.learned = []

init_state()

# --------------------------------------------------------------------------------------
# Data: Idea cards & assumptions (6–10 each)
# These map from Sim #1 “best” problem statements in the ThermaLoop direction
# --------------------------------------------------------------------------------------

IDEAS = {
    "home_comfort": {
        "title": "Home Comfort Optimizer",
        "one_liner": "Smart vents + app to eliminate hot/cold rooms and reduce bills.",
        "assumptions": [
            {"id": "A1", "text": "Homeowners perceive uneven room temps as a top 3 comfort issue.",
             "type": "desirability"},
            {"id": "A2", "text": "≥20% of target homeowners will try a no-tools ‘one room fix’ kit.",
             "type": "desirability"},
            {"id": "A3", "text": "A single room kit can deliver a noticeable comfort delta in 48 hours.",
             "type": "feasibility"},
            {"id": "A4", "text": "BLE sensors + app can estimate room temp and airflow accurately enough.",
             "type": "feasibility"},
            {"id": "A5", "text": "Installed cost of starter kit ≤ $129 with ≥60% gross margin.",
             "type": "viability"},
            {"id": "A6", "text": "Homeowners will accept a subscription ($5–$9/mo) for seasonal tuning.",
             "type": "viability"},
            {"id": "A7", "text": "Return rate for the starter kit stays under 10%.",
             "type": "viability"},
            {"id": "A8", "text": "Install instructions can be done self-serve without pro help.",
             "type": "feasibility"},
        ],
        # truth: which assumptions are actually riskiest (drives results)
        "truth": {"A1": 2, "A2": 3, "A3": 2, "A4": 1, "A5": 2, "A6": 3, "A7": 2, "A8": 1}
        # 3=very risky, 2=moderate, 1=low
    },
    "landlord_energy": {
        "title": "Landlord Energy Saver",
        "one_liner": "LoRa sensors + portal for small landlords to cut HVAC waste and get rebates.",
        "assumptions": [
            {"id": "B1", "text": "Small landlords are willing to pilot a $0 down kit for 30 days.",
             "type": "desirability"},
            {"id": "B2", "text": "HVAC runtime can be reduced ≥10% without tenant complaints.",
             "type": "feasibility"},
            {"id": "B3", "text": "A property portal reduces landlord effort vs. spreadsheets.",
             "type": "desirability"},
            {"id": "B4", "text": "End-to-end hardware logistics (ship, install guide, support) is manageable.",
             "type": "feasibility"},
            {"id": "B5", "text": "Gross margin ≥ 55% on device + 70% on SaaS at $6–$12/unit/mo.",
             "type": "viability"},
            {"id": "B6", "text": "Rebate paperwork and partner channel can acquire leads under $180 CAC.",
             "type": "viability"},
            {"id": "B7", "text": "Tenants won’t disable devices or complain about privacy.",
             "type": "desirability"},
            {"id": "B8", "text": "Landlords will sign an annual agreement if payback ≤ 9 months.",
             "type": "viability"},
            {"id": "B9", "text": "Gateway connectivity (LoRa/LTE) works in ≥85% of buildings without site visit.",
             "type": "feasibility"},
        ],
        "truth": {"B1": 2, "B2": 3, "B3": 2, "B4": 2, "B5": 2, "B6": 3, "B7": 2, "B8": 2, "B9": 2}
    },
    "installer_tools": {
        "title": "Installer Pro Toolkit",
        "one_liner": "A pro kit + mobile app for HVAC installers to diagnose airflow issues fast.",
        "assumptions": [
            {"id": "C1", "text": "Installers see airflow diagnosis as a high-value differentiator.",
             "type": "desirability"},
            {"id": "C2", "text": "Pros will pre-order a kit at $299–$399 if it saves 30 min per job.",
             "type": "desirability"},
            {"id": "C3", "text": "Clamp sensors + app yield a clear pass/fail signal in < 5 minutes.",
             "type": "feasibility"},
            {"id": "C4", "text": "Kit COGS can hit ≤ $120 at pilot volumes.",
             "type": "viability"},
            {"id": "C5", "text": "Tool integrates with common thermostats for readings/logs.",
             "type": "feasibility"},
            {"id": "C6", "text": "Wholesale distributors will carry the kit with standard margin.",
             "type": "viability"},
            {"id": "C7", "text": "Pros actually use the tool in the field (not a shelf product).",
             "type": "desirability"},
            {"id": "C8", "text": "In-app ‘good/better/best’ recommendations reduce callbacks by ≥15%.",
             "type": "feasibility"},
            {"id": "C9", "text": "Field failure/return rate < 5% in first 90 days.",
             "type": "viability"},
        ],
        "truth": {"C1": 2, "C2": 3, "C3": 2, "C4": 2, "C5": 2, "C6": 2, "C7": 2, "C8": 2, "C9": 1}
    }
}

# Experiment menu: key -> (label, cost, days, description, good_for_types)
EXPERIMENTS: Dict[str, Dict] = {
    "landing": dict(
        label="Landing Page / Waitlist",
        cost=3,
        days=3,
        desc=("Publish a simple page that states the value, a concrete offer, "
              "and a clear call-to-action (e.g., ‘Join waitlist’). Drive a small amount of traffic "
              "to observe CTR and signup rate."),
        fit=["desirability", "viability"],
    ),
    "concierge": dict(
        label="Concierge Trial",
        cost=4,
        days=7,
        desc=("Manually deliver the experience to a tiny cohort (1–5 users). "
              "Look for repeat intent (‘Would you do it again next week?’)."),
        fit=["desirability", "feasibility"],
    ),
    "wizard": dict(
        label="Wizard-of-Oz Prototype",
        cost=4,
        days=7,
        desc=("Fake the automation behind a clickable UI. Let users think it’s working; "
              "observe whether it solves the job and where it breaks."),
        fit=["feasibility", "desirability"],
    ),
    "preorder": dict(
        label="Pre-order / Deposit",
        cost=5,
        days=10,
        desc=("Ask for a small deposit or signed intent for a specific offer. "
              "Useful for pricing and purchase intent."),
        fit=["viability", "desirability"],
    ),
    "expert": dict(
        label="Expert Interview",
        cost=2,
        days=2,
        desc=("Structured interview with a domain expert (installer, energy auditor, distributor) "
              "to test realism, constraints, and hidden costs."),
        fit=["feasibility", "viability"],
    ),
    "benchmark": dict(
        label="Benchmark vs Workaround",
        cost=3,
        days=5,
        desc=("Compare your approach against common workarounds to see if it’s meaningfully better "
              "on time/accuracy/comfort."),
        fit=["feasibility", "desirability"],
    ),
    "adsplit": dict(
        label="Ad Split Test",
        cost=4,
        days=5,
        desc=("Run two to three ad messages to the same audience to discover which outcome or phrase "
              "drives more qualified clicks."),
        fit=["desirability"],
    ),
    "diary": dict(
        label="Diary Study / Usage Log",
        cost=3,
        days=7,
        desc=("Ask a handful of users to log pain episodes or usage for a week. "
              "Quantifies frequency, recency, and triggers."),
        fit=["desirability"],
    ),
}

# --------------------------------------------------------------------------------------
# NEW: Quantifiable results per experiment (numbers learners expect IRL)
# --------------------------------------------------------------------------------------
def quant_for_experiment(exp_key: str, a_type: str, rng: random.Random) -> Tuple[Dict, str]:
    """
    Return (metrics dict, short note) per experiment key.
    Uses assumption type for rough realism; keeps it simple & fast.
    """
    q = {}
    note = ""

    if exp_key == "landing":
        impressions = rng.randint(400, 900)
        ctr = max(0.5, 6.0 + (2.0 if a_type == "desirability" else 0.0))  # %
        clicks = round(impressions * ctr / 100)
        signups = round(clicks * (0.22 + 0.18 * rng.random()))
        q = {"Impressions": impressions, "CTR %": round(ctr, 1), "Clicks": clicks, "Signups": signups}
        note = "Landing page: impressions → CTR → signups show top-of-funnel pull."

    elif exp_key == "adsplit":
        impressions = rng.randint(800, 1600)
        ctr_a = round(4.0 + 3.0 * rng.random(), 1)
        ctr_b = round(ctr_a * (0.85 + 0.3 * rng.random()), 1)
        clicks_a = round(impressions/2 * ctr_a / 100)
        clicks_b = round(impressions/2 * ctr_b / 100)
        q = {"Impressions": impressions, "CTR A %": ctr_a, "CTR B %": ctr_b,
             "Clicks A": clicks_a, "Clicks B": clicks_b}
        note = "Ad split: compare CTR/clicks to see which proposition/message pulls better."

    elif exp_key == "concierge":
        trials = rng.randint(4, 9)
        would_pay = rng.randint(max(1, trials//3), trials)
        repeat = rng.randint(0, would_pay)
        q = {"Trials": trials, "Would pay again": would_pay, "Repeat after trial": repeat}
        note = "Concierge: paying intent & repeat behavior are stronger than ‘interest’."

    elif exp_key == "preorder":
        visitors = rng.randint(120, 300)
        checkouts = rng.randint(10, 40)
        confirmed = rng.randint(0, checkouts)
        q = {"Visitors": visitors, "Checkouts": checkouts, "Confirmed cards": confirmed}
        note = "Pre-order: confirmed cards (or deposits) are high-signal demand evidence."

    elif exp_key == "wizard":
        sessions = rng.randint(6, 14)
        tasks_done = rng.randint(max(2, sessions//3), sessions)
        ttv = rng.randint(6, 18)  # minutes to ‘aha’
        q = {"Sessions": sessions, "Tasks completed": tasks_done, "Time-to-value (min)": ttv}
        note = "WoZ: can users succeed and reach an ‘aha’ quickly without full automation?"

    elif exp_key == "expert":
        experts = rng.randint(3, 6)
        converge = rng.randint(max(1, experts//3), experts)
        q = {"Experts": experts, "Converging signals": converge}
        note = "Expert interviews: look for convergence on constraints & hidden costs."

    elif exp_key == "benchmark":
        trials = rng.randint(5, 12)
        better = rng.randint(max(1, trials//3), trials)
        q = {"Comparative trials": trials, "Beats workaround": better}
        note = "Benchmark: show your method beats the common workaround on something that matters."

    elif exp_key == "diary":
        participants = rng.randint(5, 10)
        events = rng.randint(10, 40)
        severe = rng.randint(0, max(2, events//4))
        q = {"Participants": participants, "Problem events": events, "High-frustration events": severe}
        note = "Diary: frequency & severity distribution over a week."

    else:
        q = {}
        note = "No quant generator for this test yet."

    return q, note

# --------------------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------------------
def next_stage(s: str):
    st.session_state.stage = s

def get_active_assumptions() -> List[dict]:
    return st.session_state.assumptions

def set_idea(key: str):
    st.session_state.idea_key = key
    idea = IDEAS[key]
    st.session_state.assumptions = idea["assumptions"].copy()
    st.session_state.ranked = idea["assumptions"].copy()
    st.session_state.ground_truth = idea["truth"].copy()
    st.session_state.round = 1
    st.session_state.portfolio = {1: [], 2: [], 3: []}
    st.session_state.results = {1: [], 2: [], 3: []}
    st.session_state.learned = []
    next_stage("rank")

def move_item(idx: int, direction: int):
    items = st.session_state.ranked
    new_idx = idx + direction
    if 0 <= new_idx < len(items):
        items[idx], items[new_idx] = items[new_idx], items[idx]

# ----- CHANGES: token carryover helpers -----
def total_scheduled_cost() -> int:
    return sum(EXPERIMENTS[e]["cost"] for r in (1,2,3) for (_, e) in st.session_state.portfolio[r])

def pool_remaining() -> int:
    return st.session_state.tokens_pool - total_scheduled_cost()

def token_balance(round_idx: int) -> int:
    # Backwards-compatible: show pool remaining when on a round screen
    return pool_remaining()

def schedule_test(round_idx: int, assumption_id: str, exp_key: str):
    cost = EXPERIMENTS[exp_key]["cost"]
    if pool_remaining() >= cost:
        st.session_state.portfolio[round_idx].append((assumption_id, exp_key))
        st.toast(f"Added {EXPERIMENTS[exp_key]['label']} for {assumption_id} (Round {round_idx})")
    else:
        st.warning("Not enough tokens in your pool.")

def run_round(round_idx: int):
    # produce results biased by ground truth risk level
    out = []
    truth = st.session_state.ground_truth
    rng = random.Random(42 + round_idx)  # stable per round
    for (aid, ek) in st.session_state.portfolio[round_idx]:
        risk = truth.get(aid, 2)  # 1..3
        fit = 1 if get_assumption(aid)["type"] in EXPERIMENTS[ek]["fit"] else 0
        # Success chance ~ inverse of risk, boosted if experiment fits the type
        base = {3: 0.25, 2: 0.45, 1: 0.65}[risk]
        p = base + 0.15 * fit
        success = random.random() < p
        signal = "strong" if success and random.random() < (0.5 + 0.2*fit) else ("weak" if success else "no-signal")
        note = synth_result_note(aid, ek, success, signal)

        # ----- NEW: quant metrics per experiment -----
        a_type = get_assumption(aid)["type"]
        quant, quant_note = quant_for_experiment(ek, a_type, rng)

        out.append(dict(aid=aid, experiment=ek, success=success, signal=signal, note=note,
                        quant=quant, quant_note=quant_note))
    st.session_state.results[round_idx] = out

def get_assumption(aid: str) -> dict:
    for a in st.session_state.assumptions:
        if a["id"] == aid:
            return a
    return {"id": aid, "text": aid, "type": "desirability"}

def synth_result_note(aid: str, ek: str, success: bool, signal: str) -> str:
    a = get_assumption(aid)
    e = EXPERIMENTS[ek]
    if success:
        if signal == "strong":
            return f"Clear evidence: {e['label']} strongly supports “{a['text']}”."
        return f"Some evidence: {e['label']} weakly supports “{a['text']}”."
    else:
        return f"No evidence found: {e['label']} did not support “{a['text']}” this round."

def to_badge(txt: str, color: str = "gray"):
    st.markdown(f"<span style='padding:2px 8px;border-radius:12px;background:{color};color:white;font-size:0.85rem'>{txt}</span>", unsafe_allow_html=True)

def stepper():
    cols = st.columns(10)
    steps = ["Intro","Choose Idea","Rank Risks","Round 1 — Select","Round 1 — Results",
             "Round 2 — Select","Round 2 — Results","Round 3 — Select","Round 3 — Results",
             "Learning & Score"]
    active_idx = {
        "intro": 0, "choose": 1, "rank": 2,
        "r1_select": 3, "r1_results": 4,
        "r2_select": 5, "r2_results": 6,
        "r3_select": 7, "r3_results": 8,
        "score": 9
    }[st.session_state.stage]
    for i, c in enumerate(cols):
        with c:
            style = "background:#eef6ff;border:1px solid #cde;" if i == active_idx else "background:#f7f7f9;border:1px solid #eee;"
            st.markdown(f"""
            <div style="{style}padding:8px 10px;border-radius:10px;text-align:center;min-height:56px">
            {steps[i]}
            </div>
            """, unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# UI Screens
# --------------------------------------------------------------------------------------
def screen_intro():
    stepper()
    st.title("Simulation #2 — Designing & Running Early Experiments")
    st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly")
    st.subheader("What you’ll do")
    st.markdown("""
    1) **Choose a seed idea** (from three).  
    2) **Rank** 6–10 assumptions from *riskiest to least risky*.  
    3) For **three rounds**, spend **tokens** to run scrappy tests.  
    4) Review **results**, adjust, and learn.  
    5) Get a **score** with targeted coaching notes.
    """)
    st.info("Tip: Early on, test **desirability** cheaply before you invest in feasibility or scaling.")
    st.button("Start", type="primary", on_click=lambda: next_stage("choose"))

def screen_choose():
    stepper()
    st.subheader("Pick your idea to test")
    cols = st.columns(3)
    def idea_card(key: str, col):
        idea = IDEAS[key]
        with col:
            st.markdown(f"#### {idea['title']}")
            st.caption(idea["one_liner"])
            with st.expander("Show initial assumptions", expanded=False):
                for a in idea["assumptions"]:
                    st.markdown(f"- {a['text']}  _({a['type']})_")
            st.button("Choose", key=f"pick_{key}", on_click=lambda k=key: set_idea(k), type="primary", use_container_width=True)

    idea_card("home_comfort", cols[0])
    idea_card("landlord_energy", cols[1])
    idea_card("installer_tools", cols[2])

    if st.session_state.idea_key:
        st.success(f"Chosen: **{IDEAS[st.session_state.idea_key]['title']}**")
        st.button("Next: Rank Risks", on_click=lambda: next_stage("rank"))

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
    st.caption("Schedule as many tests as your **tokens** allow. Mix quick/cheap with higher-signal where it fits.")
    # tokens (carryover pool)
    to_badge(f"Token pool (carryover): {st.session_state.tokens_pool}", "#295")
    st.write(" ")
    to_badge(f"Remaining now: {pool_remaining()}", "#295")

    # show ranked list with selector of experiments
    ranked = st.session_state.ranked
    st.markdown("##### Assumptions (your order)")
    for a in ranked:
        with st.expander(f"{a['id']} — {a['text']}", expanded=False):
            st.caption(f"Type: **{a['type']}**")
            cols = st.columns(4)
            for ek, card in EXPERIMENTS.items():
                with cols[list(EXPERIMENTS.keys()).index(ek) % 4]:
                    st.markdown(f"**{card['label']}**  \n_{card['desc']}_  \nCost: **{card['cost']}**, ~{card['days']} days")
                    if st.button(f"Add → {a['id']}", key=f"add_{round_idx}_{a['id']}_{ek}"):
                        schedule_test(round_idx, a['id'], ek)

    st.divider()
    scheduled = st.session_state.portfolio[round_idx]
    if scheduled:
        st.markdown("#### Scheduled this round")
        df = pd.DataFrame([{
            "Assumption": aid,
            "Experiment": EXPERIMENTS[ek]["label"],
            "Cost": EXPERIMENTS[ek]["cost"]
        } for (aid, ek) in scheduled])
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("No tests scheduled yet.")

    can_run = len(scheduled) > 0
    if can_run:
        st.button(f"Run Round {round_idx}", type="primary", on_click=lambda r=round_idx: (run_round(r), next_stage(f"r{r}_results")))
    else:
        st.button(f"Run Round {round_idx}", disabled=True)

def screen_round_results(round_idx: int):
    stepper()
    st.subheader(f"Round {round_idx} — Results")
    res = st.session_state.results[round_idx]
    if not res:
        st.warning("No results recorded. Go back and schedule tests.")
        return

    # Show each result (outcome + signal + quant metrics)
    quant_rows = []
    quant_notes = []
    for r in res:
        a = get_assumption(r["aid"])
        e = EXPERIMENTS[r["experiment"]]
        box = st.container(border=True)
        with box:
            st.markdown(f"**{a['id']}** — {a['text']}")
            st.markdown(f"**Experiment:** {e['label']}  \n**Outcome:** {'✅ Success' if r['success'] else '❌ No evidence'}  \n**Signal:** {r['signal']}")
            st.caption(r["note"])
        if r.get("quant"):
            quant_rows.append({"Assumption": a["id"], "Experiment": e["label"], **r["quant"]})
            if r.get("quant_note"):
                quant_notes.append(r["quant_note"])

    if quant_rows:
        st.markdown("#### Quant results")
        st.dataframe(pd.DataFrame(quant_rows), hide_index=True, use_container_width=True)
        with st.expander("How to read these numbers"):
            for n in sorted(set(quant_notes)):
                st.markdown(f"- {n}")

    # ----- NEW: DFV progress visualization -----
    st.markdown("#### Validation progress (Desirability / Feasibility / Viability)")
    # map signal strength to [0..1]
    strength = {"strong": 1.0, "weak": 0.5, "no-signal": 0.0}
    agg = {"desirability": [], "feasibility": [], "viability": []}
    for r in res:
        typ = get_assumption(r["aid"])["type"]
        agg[typ].append(strength.get(r["signal"], 0.0))
    pct = {k.capitalize(): (round(100*sum(v)/len(v),1) if v else 0.0) for k, v in agg.items()}
    st.bar_chart(pd.DataFrame([pct], index=["Progress"]))
    st.caption("Progress = average signal strength this round (0–100).")

    st.divider()
    if round_idx < 3:
        st.button("Next Round — Select", type="primary",
                  on_click=lambda r=round_idx+1: next_stage(f"r{r}_select"))
    else:
        st.button("See Learning Summary & Score", type="primary", on_click=lambda: next_stage("score"))

# --------------------------------------------------------------------------------------
# Scoring & Feedback
# --------------------------------------------------------------------------------------
CATEGORY_WEIGHTS = {
    "Assumption Quality": 30,
    "Risk Prioritization": 25,
    "Experiment Fit": 25,
    "Resource Efficiency": 10,
    "Learning Outcome": 10,
}

def compute_score() -> Tuple[int, Dict[str, int], Dict[str, str]]:
    truth = st.session_state.ground_truth
    # user priority: higher in the list = riskier
    ranked_ids = [a["id"] for a in st.session_state.ranked]
    # “true“ top-3 risks by ground truth
    truth_sorted = sorted(truth.items(), key=lambda kv: kv[1], reverse=True)
    true_top3 = [aid for aid, _ in truth_sorted[:3]]

    # 1) Risk Prioritization (25)
    hits = sum(1 for aid in ranked_ids[:3] if aid in true_top3)
    risk_prior = int(25 * (hits / 3))

    # 2) Experiment Fit (25): proportion of scheduled tests whose type matches assumption type
    total = 0
    good = 0
    for rnd in (1, 2, 3):
        for aid, ek in st.session_state.portfolio[rnd]:
            total += 1
            if get_assumption(aid)["type"] in EXPERIMENTS[ek]["fit"]:
                good += 1
    exp_fit = int(25 * (good / total)) if total else 0

    # 3) Resource Efficiency (10): leftover tokens in pool
    leftover = pool_remaining()
    eff = min(10, 3 + leftover // 3)  # gentle curve

    # 4) Learning Outcome (10): number of “strong” signals
    strongs = sum(1 for rnd in (1,2,3) for r in st.session_state.results[rnd] if r["signal"] == "strong")
    learn = min(10, strongs * 3)

    # 5) Assumption Quality (30): inferred via your ranking spread (not all desirability on top)
    types_top5 = [get_assumption(aid)["type"] for aid in ranked_ids[:5]]
    diversity = len(set(types_top5))
    qual = 20 + (10 if diversity >= 2 else 0)

    total_score = risk_prior + exp_fit + eff + learn + qual

    # reasons
    reasons = {
        "Assumption Quality": f"Diversity in top priorities: {diversity} distinct assumption types.",
        "Risk Prioritization": f"{hits}/3 of the true riskiest assumptions were in your top priorities.",
        "Experiment Fit": f"{good}/{total} tests matched assumption type (fit-aligned).",
        "Resource Efficiency": f"Leftover tokens after Round 3: {leftover} (carryover pool).",
        "Learning Outcome": f"Strong signals collected: {strongs}.",
    }
    breakdown = {
        "Assumption Quality": qual,
        "Risk Prioritization": risk_prior,
        "Experiment Fit": exp_fit,
        "Resource Efficiency": eff,
        "Learning Outcome": learn,
    }
    return total_score, breakdown, reasons

def screen_score():
    stepper()
    st.subheader("Learning Summary & Score")

    total, breakdown, reasons = compute_score()

    # Convert to /100 display while preserving category order
    ordered = list(CATEGORY_WEIGHTS.keys())
    display_rows = []
    for cat in ordered:
        raw = breakdown.get(cat, 0)
        out100 = round(100 * raw / CATEGORY_WEIGHTS[cat]) if CATEGORY_WEIGHTS[cat] else 0
        display_rows.append({"Category": cat, "Score /100": out100, "Why you scored this way": reasons.get(cat, "—")})

    st.metric("Total Score (sum of categories)", total)
    st.markdown("#### Category scores (out of 100) + reasons")
    st.dataframe(pd.DataFrame(display_rows), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("#### Coaching Notes")
    notes = []
    if breakdown["Risk Prioritization"] < 18:
        notes.append("Push the **riskiest desirability** items to the top and test cheaply first.")
    if breakdown["Experiment Fit"] < 18:
        notes.append("Pick experiments that match the **assumption type** (e.g., intent tests for desirability).")
    if breakdown["Resource Efficiency"] < 8:
        notes.append("Avoid stacking multiple high-cost tests in early rounds; preserve tokens for iteration.")
    if breakdown["Learning Outcome"] < 7:
        notes.append("Favor experiments that can yield **stronger signals** in days, not weeks.")
    if breakdown["Assumption Quality"] < 26:
        notes.append("Ensure your top assumptions are **specific and measurable**, not vague themes.")
    if not notes:
        notes.append("Great balance. Your sequencing and test selection show strong product sense.")
    for n in notes:
        st.write(f"- {n}")

    st.success("Simulation complete. You can refresh to try a different idea or ranking strategy.")

# --------------------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------------------
def router():
    stage = st.session_state.stage
    if stage == "intro":
        screen_intro()
    elif stage == "choose":
        screen_choose()
    elif stage == "rank":
        screen_rank()
    elif stage == "r1_select":
        screen_round_select(1)
    elif stage == "r1_results":
        screen_round_results(1)
    elif stage == "r2_select":
        screen_round_select(2)
    elif stage == "r2_results":
        screen_round_results(2)
    elif stage == "r3_select":
        screen_round_select(3)
    elif stage == "r3_results":
        screen_round_results(3)
    elif stage == "score":
        screen_score()
    else:
        screen_intro()

# --------------------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------------------
router()
