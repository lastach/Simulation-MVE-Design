import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
import pandas as pd
import streamlit as st

# ----------------------------------------
# Page config
# ----------------------------------------
st.set_page_config(
    page_title="Simulation #2 — Designing & Running Early Experiments",
    page_icon="🧪",
    layout="wide"
)

# ----------------------------------------
# Utility
# ----------------------------------------
def _ss(key: str, default):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

def init_once():
    if _ss("initialized", False):
        return
    # Stages:
    # 0: Intro
    # 1: Choose Idea
    # 2: Rank Risks
    # 3: Round 1 - Select
    # 4: Round 1 - Results
    # 5: Round 2 - Select
    # 6: Round 2 - Results
    # 7: Round 3 - Select
    # 8: Round 3 - Results
    # 9: Learning Summary
    # 10: Feedback & Score
    st.session_state.stage = 0
    st.session_state.idea_idx = None

    # Budgets per round
    st.session_state.round_budgets = {1: 10, 2: 8, 3: 6}

    # Experiments master list (cost, speed, description and the bucket it mainly hits)
    # Buckets used internally to recommend: desirability / feasibility / viability
    st.session_state.experiments = {
        "Landing page (smoke test)": {
            "cost": 3, "speed": "days", "bucket": "desirability",
            "desc": "Create a simple page that promises the outcome and captures interest (email/sign-up). Measures real pull."
        },
        "Concierge MVP": {
            "cost": 4, "speed": "days", "bucket": "desirability",
            "desc": "Manually deliver a thin slice of the service to a small set of users to measure willingness to continue."
        },
        "Wizard-of-Oz prototype": {
            "cost": 5, "speed": "days", "bucket": "feasibility",
            "desc": "Prototype the experience; automate UI while you manually do the back-end. Validates UX and feasibility at small scale."
        },
        "Pre-order / deposit": {
            "cost": 4, "speed": "days", "bucket": "desirability",
            "desc": "Ask for refundable deposits or card-on-file to validate real willingness to pay, not just interest."
        },
        "Expert / installer interview": {
            "cost": 2, "speed": "days", "bucket": "feasibility",
            "desc": "Speak with professionals to map hidden constraints and edge cases quickly."
        },
        "Benchmark vs workaround": {
            "cost": 3, "speed": "days", "bucket": "desirability",
            "desc": "Compare behavior using your stopgap vs. current workaround to see if you improve key outcomes."
        },
        "Ad split test": {
            "cost": 3, "speed": "days", "bucket": "desirability",
            "desc": "Run small paid tests with several messages to find which value prop pulls best."
        },
        "Diary / usage log": {
            "cost": 2, "speed": "weeks", "bucket": "desirability",
            "desc": "Have users log behavior over time to reveal triggers, frequency and real-world friction."
        },
        "Pilot install (micro)": {
            "cost": 6, "speed": "weeks", "bucket": "feasibility",
            "desc": "Run a small real-world install with 1–2 households/locations to validate data capture and reliability."
        },
        "Partner referral probe": {
            "cost": 3, "speed": "days", "bucket": "viability",
            "desc": "Ask adjacent partners to introduce you. Measures channel willingness and early CAC assumptions."
        },
        "Pricing probe": {
            "cost": 3, "speed": "days", "bucket": "viability",
            "desc": "Offer two–three price anchors to see acceptance and pushback patterns."
        },
        "Scale drill (ops)": {
            "cost": 4, "speed": "days", "bucket": "feasibility",
            "desc": "Walk through processes for 10× volume. Reveals manual bottlenecks and cost drivers."
        },
    }

    # Idea cards (three), each with 8–10 assumptions. These reflect Simulation #1 “best” problem statements.
    st.session_state.idea_cards = [
        {
            "name": "Smart-vent retrofit kit + mobile app",
            "summary": "Room-by-room airflow control with occupancy/temperature sensing; app + optional vents retrofit.",
            "assumptions": [
                ("10% of homeowners willing to buy retrofit vents within 30 days", "desirability"),
                ("Occupancy+temp sensors maintain ±1.5°F room balance", "feasibility"),
                ("Average install time < 60 minutes per vent", "feasibility"),
                ("Noise/power from vent motors acceptable in bedrooms", "desirability"),
                ("App setup < 10 minutes with clear guidance", "feasibility"),
                ("Starter kit at $199 yields ≥60% gross margin", "viability"),
                ("Monthly service at $6.99 acceptable to 20%+ buyers", "viability"),
                ("DIY install acceptable for 70% of target homes", "feasibility"),
                ("Partners (HVAC shops) open to offering kits", "viability"),
            ]
        },
        {
            "name": "ThermaLoop plug-in booster + insights",
            "summary": "An inline booster device that smooths temperature swings and logs savings; app provides coaching.",
            "assumptions": [
                ("Homeowners perceive comfort improvement within 48 hours", "desirability"),
                ("Booster can be installed without cutting ducts", "feasibility"),
                ("Measured energy savings ≥ 7% for typical homes", "feasibility"),
                ("Starter kit at $149 hits ≥55% gross margin", "viability"),
                ("Refund rate ≤ 8% after 30-day trial", "viability"),
                ("App onboarding < 8 minutes", "feasibility"),
                ("Contractors willing to stock for upsell", "viability"),
                ("Noise level under 35 dB in bedrooms", "desirability"),
                ("Mobile app daily tips used by ≥30% weekly", "desirability"),
            ]
        },
        {
            "name": "Tenant-friendly smart radiator valves",
            "summary": "No-plumber clip-on valves for radiators; app schedules heat, reduces waste for renters/landlords.",
            "assumptions": [
                ("Landlords allow tenant install in ≥50% cases", "desirability"),
                ("Clip-on valve fits 80% of common radiator types", "feasibility"),
                ("Battery life ≥ 9 months per device", "feasibility"),
                ("Bundle price $179 acceptable to tenants", "viability"),
                ("Landlords pay monthly for building dashboard", "viability"),
                ("App scheduling cuts overheating events by 30%", "feasibility"),
                ("Install time < 5 minutes per radiator", "feasibility"),
                ("Tenants value comfort more than aesthetics", "desirability"),
                ("Support load < 0.2 tickets per device per month", "viability"),
            ]
        }
    ]

    # Ground-truth risk map used to bias results (hidden)
    # Weight: desirability > feasibility > viability in round 1, then adaptively reweighted
    st.session_state.risk_weights = {"desirability": 0.45, "feasibility": 0.35, "viability": 0.20}

    # Learner state
    st.session_state.ranked = []       # list of tuples (assumption, bucket)
    st.session_state.portfolio = {1: [], 2: [], 3: []}  # selections [(assumption_idx, exp_key)]
    st.session_state.results = {1: [], 2: [], 3: []}    # results per round
    st.session_state.learned = []      # narrative bullets from results
    st.session_state.initialized = True

init_once()

# ----------------------------------------
# UI Helpers
# ----------------------------------------
def step_tabs(active_stage: int):
    labels = [
        "Intro", "Choose Idea", "Rank Risks",
        "Round 1 — Select", "Round 1 — Results",
        "Round 2 — Select", "Round 2 — Results",
        "Round 3 — Select", "Round 3 — Results",
        "Learning Summary", "Feedback & Score"
    ]
    cols = st.columns(len(labels))
    for i, (c, label) in enumerate(zip(cols, labels)):
        with c:
            btn = st.button(label, use_container_width=True)
            if btn:
                st.session_state.stage = i
    # Progress bar
    st.progress(active_stage / (len(labels) - 1))

def section_header(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)

def idea_picker():
    st.markdown("### Pick an idea card")
    for i, card in enumerate(st.session_state.idea_cards):
        with st.expander(f"{i+1}. {card['name']}", expanded=(st.session_state.idea_idx == i)):
            st.write(card["summary"])
            st.markdown("**Example assumptions (hidden risks in parentheses):**")
            df = pd.DataFrame([{"Assumption": a, "Risk bucket": b} for a, b in card["assumptions"]])
            st.dataframe(df, use_container_width=True, hide_index=True)
            if st.button(f"Choose '{card['name']}'", key=f"choose_{i}"):
                st.session_state.idea_idx = i
    if st.session_state.idea_idx is not None:
        st.success(f"Chosen: {st.session_state.idea_cards[st.session_state.idea_idx]['name']}")
        if st.button("Next: Rank Risks ▶"):
            st.session_state.stage = 2

def rank_risks():
    section_header("Rank your assumptions (highest → lowest risk)",
                   "Enter 1, 2, 3... (ties allowed, but lower number means higher risk).")
    card = st.session_state.idea_cards[st.session_state.idea_idx]
    df = pd.DataFrame([{"Assumption": a, "Bucket": b} for a, b in card["assumptions"]])
    ranks = []
    for idx, row in df.iterrows():
        r = st.number_input(f"Rank: {row['Assumption']}", min_value=1, max_value=10, value=min(idx+1, 10), step=1, key=f"rank_{idx}")
        ranks.append((idx, r))
    ranks.sort(key=lambda x: x[1])  # lowest rank first
    st.session_state.ranked = [(card["assumptions"][i][0], card["assumptions"][i][1], r) for i, r in ranks]
    st.write("**Your ranking (1 = highest risk):**")
    df_show = pd.DataFrame([{"Rank": r, "Assumption": a, "Bucket": b} for (a, b, r) in st.session_state.ranked])
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    if st.button("Next: Round 1 — Select ▶"):
        st.session_state.stage = 3

def list_experiments_for_assumption(assumption_bucket: str) -> List[str]:
    # Suggest experiments that primarily hit this bucket
    exps = [k for k, v in st.session_state.experiments.items() if v["bucket"] == assumption_bucket]
    # plus two generics
    generic = ["Ad split test", "Benchmark vs workaround"]
    for g in generic:
        if g not in exps:
            exps.append(g)
    return exps

def select_round(round_idx: int):
    section_header(f"Round {round_idx} — Select experiments",
                   f"You have **{st.session_state.round_budgets[round_idx]} tokens**. "
                   "Pick as many experiments as your budget allows. "
                   "We recommend tackling the **riskiest** assumptions first.")
    # Show top risky assumptions (show all ranked; learner chooses where to spend)
    df_ranked = pd.DataFrame([
        {"Rank": r, "Assumption": a, "Bucket": b}
        for (a, b, r) in st.session_state.ranked
    ]).sort_values("Rank")
    st.dataframe(df_ranked, use_container_width=True, hide_index=True)

    # Selection area
    remaining = st.session_state.round_budgets[round_idx]
    st.info(f"**Round {round_idx} tokens remaining:** {remaining}")

    # Build a grid of cards: Assumption → recommended experiments with checkboxes
    chosen: List[Tuple[int, str]] = []
    # We cap display to top 8 to keep UI compact
    for idx, (assumption, bucket, rank) in enumerate(st.session_state.ranked[:8]):
        with st.expander(f"Assumption (rank {rank}): {assumption}  —  [{bucket}]", expanded=False):
            options = list_experiments_for_assumption(bucket)
            for exp_key in options:
                meta = st.session_state.experiments[exp_key]
                label = f"{exp_key}  • cost {meta['cost']}  • {meta['speed']}  \n_{meta['desc']}_"
                check = st.checkbox(label, key=f"r{round_idx}_a{idx}_e{exp_key}")
                if check:
                    chosen.append((idx, exp_key))

    # Compute cost and enforce budget locally (no auto reruns)
    total_cost = sum(st.session_state.experiments[e]["cost"] for (_, e) in chosen)
    over = total_cost - st.session_state.round_budgets[round_idx]
    if over > 0:
        st.error(f"Over budget by {over} tokens. Uncheck some experiments to proceed.")
    else:
        st.success(f"Planned total cost: {total_cost} tokens (≤ budget).")

    if st.button("Run selected experiments ▶", disabled=(over > 0 or total_cost == 0)):
        # Save portfolio (convert assumption index to global index)
        st.session_state.portfolio[round_idx] = chosen.copy()
        # Run results immediately and advance stage
        st.session_state.results[round_idx] = run_experiments(round_idx, chosen)
        st.session_state.stage = round_idx * 2  # 1->2*1=2? (but our stage map uses: 4=R1 results, 6=R2 results, 8=R3 results)
        # Map: R1 Select (3) -> Results (4), R2 Select (5) -> Results (6), R3 Select (7) -> Results (8)
        st.session_state.stage = {1: 4, 2: 6, 3: 8}[round_idx]

def run_experiments(round_idx: int, selections: List[Tuple[int, str]]) -> List[Dict[str, Any]]:
    """Simulate experiment outcomes with noise, biased by hidden ground-truth weights."""
    random.seed(42 + round_idx)  # deterministic per round for now
    results = []
    card = st.session_state.idea_cards[st.session_state.idea_idx]
    for (a_idx, exp_key) in selections:
        assumption, bucket, rank = st.session_state.ranked[a_idx]
        base = st.session_state.experiments[exp_key]

        # Prioritize desirability in Round 1, then adaptively for remaining risks
        weight = st.session_state.risk_weights[bucket]
        # Better-ranked assumptions (lower rank number) get stronger signal
        rank_factor = 1.0 + (max(0, 6 - rank) * 0.08)  # rank 1..5 slightly stronger
        # Cost also influences: more costly => a bit better signal
        cost_factor = 1.0 + (base["cost"] * 0.05)
        # Aggregate signal strength
        signal = min(0.95, 0.30 + weight * 0.6 * rank_factor * 0.9 + 0.05 * cost_factor)

        # Create a human-readable outcome snippet
        if base["bucket"] == "desirability":
            # e.g., CTR, signups, preorders
            impressions = random.randint(200, 800)
            ctr = max(0.01, min(0.25, random.gauss(mu=0.06 + 0.20 * signal, sigma=0.02)))
            clicks = int(impressions * ctr)
            conversions = int(clicks * (0.15 + 0.6 * signal))
            outcome = f"{impressions} visits → {clicks} clicks (CTR {ctr:.1%}) → {conversions} signups"
            validated = conversions >= max(8, int(0.01 * impressions))
        elif base["bucket"] == "feasibility":
            success_rate = max(0.3, min(0.95, random.gauss(mu=0.55 + 0.35 * signal, sigma=0.1)))
            outcome = f"Prototype tasks success rate: {success_rate:.0%} across small pilot"
            validated = success_rate >= 0.7
        else:  # viability
            accept = max(0.05, min(0.6, random.gauss(mu=0.12 + 0.5 * signal, sigma=0.06)))
            payback = max(4, int(18 - 10 * signal + random.randint(-1, 2)))
            outcome = f"Price acceptance ~{accept:.0%}; CAC payback ~{payback} months (modelled)"
            validated = (accept >= 0.10 and payback <= 12)

        results.append({
            "assumption": assumption,
            "bucket": bucket,
            "experiment": exp_key,
            "outcome": outcome,
            "validated": validated
        })

    # Build learning bullets
    for r in results:
        verdict = "validated" if r["validated"] else "inconclusive/invalidated"
        st.session_state.learned.append(f"{r['experiment']} on “{r['assumption']}” → **{verdict}**: {r['outcome']}")
    return results

def show_results(round_idx: int, next_stage_label: str):
    section_header(f"Round {round_idx} — Results")
    res = st.session_state.results[round_idx]
    if not res:
        st.warning("No experiments were run.")
    else:
        df = pd.DataFrame(res)
        st.dataframe(df, use_container_width=True, hide_index=True)
    if round_idx < 3:
        if st.button(f"Next: {next_stage_label} ▶"):
            st.session_state.stage = {1: 5, 2: 7}[round_idx]
    else:
        if st.button("Next: Learning Summary ▶"):
            st.session_state.stage = 9

def learning_summary():
    section_header("Learning Summary", "What you actually learned from the tests you ran.")
    if st.session_state.learned:
        for b in st.session_state.learned:
            st.markdown(f"- {b}")
    else:
        st.info("No learning captured yet.")
    if st.button("Next: Feedback & Score ▶"):
        st.session_state.stage = 10

def feedback_and_score():
    section_header("Feedback & Score", "How well you chose, sequenced, and used resources.")
    # Compute scoring components
    # 1) Assumption Quality: Did they prioritize desirability first in R1?
    top3 = st.session_state.ranked[:3]
    desir_first = sum(1 for (_, b, r) in top3 if b == "desirability")
    assumption_quality = 70 + 10 * desir_first  # up to 100
    assumption_quality = min(100, assumption_quality)

    # 2) Risk Prioritization: Did they test highest-ranked early?
    # Evaluate if R1 portfolio hits rank 1–3 assumptions
    r1_idxs = [a for (a, _) in st.session_state.portfolio[1]]
    hits_top = sum(1 for i in r1_idxs if i in [0, 1, 2])
    risk_prior = 50 + hits_top * 15
    risk_prior = min(100, risk_prior)

    # 3) Experiment Fit: bucket-aligned experiments
    fit = 0
    total = 0
    for rnd in (1, 2, 3):
        for (a_idx, exp_key) in st.session_state.portfolio[rnd]:
            bucket = st.session_state.ranked[a_idx][1]
            total += 1
            if st.session_state.experiments[exp_key]["bucket"] == bucket:
                fit += 1
    exp_fit = int(100 * (fit / total)) if total else 0

    # 4) Resource Efficiency: under or equal to budget and not many high-cost in R1
    eff = 100
    for rnd in (1, 2, 3):
        spent = sum(st.session_state.experiments[e]["cost"] for (_, e) in st.session_state.portfolio[rnd])
        budget = st.session_state.round_budgets[rnd]
        if spent == 0:
            eff -= 25
        elif spent > budget:
            eff -= 20
        elif rnd == 1 and spent > budget * 0.8:
            eff -= 5  # small nudge to leave room for iteration
    eff = max(0, eff)

    # 5) Learning Outcome: share of validated signals
    all_res = sum((st.session_state.results[r] for r in (1, 2, 3)), [])
    if all_res:
        validated = sum(1 for r in all_res if r["validated"])
        learn_out = int(100 * validated / len(all_res))
    else:
        learn_out = 0

    # Weighted total (30/25/25/10/10)
    total_score = round(
        0.30 * assumption_quality +
        0.25 * risk_prior +
        0.25 * exp_fit +
        0.10 * eff +
        0.10 * learn_out
    )

    # Display
    cols = st.columns(2)
    with cols[0]:
        st.metric("Total score", total_score)
        st.progress(total_score/100)
    with cols[1]:
        st.write("**Category scores**")
        st.write(f"- Assumption Quality (30%): **{assumption_quality}**")
        st.write(f"- Risk Prioritization (25%): **{risk_prior}**")
        st.write(f"- Experiment Fit (25%): **{exp_fit}**")
        st.write(f"- Resource Efficiency (10%): **{eff}**")
        st.write(f"- Learning Outcome (10%): **{learn_out}**")

    st.markdown("### Reasons (personalized)")
    reasons = []
    # Reasons tie to exactly what they did
    if desir_first >= 2:
        reasons.append("You prioritized **desirability** assumptions early, which is ideal for a new concept.")
    else:
        reasons.append("Consider testing **desirability** signals first (demand/WTP) before heavier feasibility or viability work.")

    if hits_top >= 2:
        reasons.append("You tested **top-ranked risks** in Round 1, reducing uncertainty quickly.")
    else:
        reasons.append("Testing highest-ranked risks earlier would accelerate learning and avoid waste.")

    if exp_fit >= 70:
        reasons.append("Most chosen experiments matched the **risk type** (e.g., smoke tests for demand, pilots for feasibility).")
    else:
        reasons.append("Some experiments didn’t match the assumption type. Use short smoke tests for demand; pilots/benchmarks for feasibility; pricing/probes for viability.")

    if eff >= 90:
        reasons.append("You used tokens **efficiently**, leaving room for iteration in later rounds.")
    else:
        reasons.append("Conserve some budget in R1 so you can pivot or double-down with better tests in R2/R3.")

    if learn_out >= 60:
        reasons.append("You extracted **clear signals** from experiments—good framing and selection.")
    else:
        reasons.append("Outcomes were weak/inconclusive—tighten assumption wording and choose tests with clearer pass/fail thresholds.")

    for r in reasons:
        st.markdown(f"- {r}")

    st.markdown("### Coaching notes")
    st.markdown(
        "- Start with **pull** (desirability); aim for concrete evidence (signups, deposits, repeated use).\n"
        "- Use **lightweight** tests first (low cost, fast): it increases the number of shots on goal.\n"
        "- Match **test → assumption**: Smoke tests for demand; expert/pilot/benchmark for feasibility; price/payback probes for viability.\n"
        "- **Iterate**: adapt R2/R3 based on data—not momentum.\n"
    )

    if st.button("Restart simulation 🔁"):
        for k in list(st.session_state.keys()):
            if k not in ("initialized",):
                st.session_state.pop(k, None)
        init_once()
        st.session_state.stage = 0

# ----------------------------------------
# Render
# ----------------------------------------
st.title("Simulation #2 — Designing & Running Early Experiments")
st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly")

step_tabs(st.session_state.stage)

if st.session_state.stage == 0:
    section_header("Intro",
                   "You’ll pick an idea card, rank risky assumptions, then run three rounds of scrappy experiments "
                   "under token budgets: **R1=10**, **R2=8**, **R3=6**. The goal is to reduce the **riskiest** unknowns fast.")
    st.markdown(
        "- **Round 1**: prioritize **desirability** (real demand / willingness to pay)\n"
        "- **Round 2**: address remaining **feasibility** gaps (can we deliver?)\n"
        "- **Round 3**: check **viability** (margins, payback) or double-down on the biggest blocker"
    )
    if st.button("Start ▶"):
        st.session_state.stage = 1

elif st.session_state.stage == 1:
    idea_picker()

elif st.session_state.stage == 2:
    if st.session_state.idea_idx is None:
        st.warning("Pick an idea first.")
    else:
        rank_risks()

elif st.session_state.stage == 3:
    if st.session_state.ranked:
        select_round(1)
    else:
        st.warning("Rank risks first.")

elif st.session_state.stage == 4:
    show_results(1, "Round 2 — Select")

elif st.session_state.stage == 5:
    select_round(2)

elif st.session_state.stage == 6:
    show_results(2, "Round 3 — Select")

elif st.session_state.stage == 7:
    select_round(3)

elif st.session_state.stage == 8:
    show_results(3, "Learning Summary")

elif st.session_state.stage == 9:
    learning_summary()

else:
    feedback_and_score()
