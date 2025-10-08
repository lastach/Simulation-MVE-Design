# ============================================================================
# Simulation #2 — ThermaLoop: Designing & Running Early Experiments
# ----------------------------------------------------------------------------
# No external UI deps (no drag-and-drop). Ranking is handled by Up/Down buttons.
# 3 rounds, token budgets, experiment cards with descriptions, semi-random
# outcomes biased by a hidden risk map, and detailed scoring reasons.
# ============================================================================

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Streamlit config
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Simulation #2 — ThermaLoop", page_icon="🧪", layout="wide")

# -----------------------------------------------------------------------------
# Constants & Data
# -----------------------------------------------------------------------------
ROUND_BUDGET = {"r1": 12, "r2": 10, "r3": 8}  # token budgets per round

@dataclass
class Experiment:
    """A scrappy test option."""
    name: str
    cost: int
    description: str
    tags_for_fit: List[str]
    strength: int  # 1..3 relative confidence gain

EXPERIMENTS: List[Experiment] = [
    Experiment(
        "Landing Page Test", 3,
        "Publish a simple page with a clear promise; send small traffic to measure click-through and signups.",
        ["desirability"], 2
    ),
    Experiment(
        "Smoke Test (Reserve Now)", 4,
        "Offer a ‘Reserve’ or ‘Join Waitlist’ CTA with light friction to test real intent.",
        ["desirability", "viability"], 3
    ),
    Experiment(
        "Concierge Trial", 4,
        "Manually deliver the value for a few users (no code) and observe outcomes and willingness to continue.",
        ["desirability", "feasibility"], 2
    ),
    Experiment(
        "Wizard-of-Oz Prototype", 4,
        "Fake the backend but keep the real UI; validate that the flow/output meets expectations.",
        ["feasibility", "desirability"], 2
    ),
    Experiment(
        "Pre-Order Test", 4,
        "Collect card-on-file or deposits (refundable) to measure true willingness to pay.",
        ["viability", "desirability"], 3
    ),
    Experiment(
        "Ad Split Test", 3,
        "Run tiny-budget ads with different messages to see what attracts attention from your segment.",
        ["desirability"], 1
    ),
    Experiment(
        "Expert Interview", 2,
        "Short calls with domain experts to surface blockers (compliance, installation, supply-chain).",
        ["feasibility", "viability"], 1
    ),
    Experiment(
        "Diary / Usage Log", 3,
        "Have users log behaviors for 1–2 weeks; discover triggers, frequency and sticking points.",
        ["desirability"], 2
    ),
]

# --- Idea cards & hidden risk maps (0..1; higher = riskier/less likely to succeed) ---
IDEA_CARDS: Dict[str, Dict] = {
    "homeowners": {
        "title": "Homeowner: Comfort & Energy",
        "assumptions": [
            ("Main motivation is saving money, not comfort.", "desirability"),
            ("Homeowners will try a 14-day free trial.", "desirability"),
            ("Self-install can be done in under 45 minutes.", "feasibility"),
            ("Users will allow data collection from the thermostat.", "viability"),
            ("Monthly price under $9 is acceptable.", "viability"),
            ("Comfort improvement is noticeable within 7 days.", "desirability"),
            ("Mobile notifications drive weekly action.", "desirability"),
            ("Household members will not object to auto-scheduling.", "desirability"),
            ("Data privacy copy is sufficient to build trust.", "viability"),
            ("Geofencing works reliably across devices.", "feasibility"),
        ],
        "risk_truth": [0.8, 0.7, 0.6, 0.55, 0.7, 0.5, 0.45, 0.6, 0.6, 0.5],
    },
    "landlords": {
        "title": "Small Landlords: Portfolio Savings",
        "assumptions": [
            ("Property managers will share thermostat data per unit.", "viability"),
            ("Premium $49/month tier is viable.", "viability"),
            ("Main value is fewer maintenance visits (not energy).", "desirability"),
            ("80% activation within two weeks is achievable.", "feasibility"),
            ("Tenants will not disable automations.", "desirability"),
            ("PM partnerships can drive warm leads.", "desirability"),
            ("Bulk onboarding tools reduce setup time by 50%.", "feasibility"),
            ("Annual contracts with 30-day pilot are acceptable.", "viability"),
        ],
        "risk_truth": [0.7, 0.62, 0.7, 0.5, 0.6, 0.5, 0.5, 0.58],
    },
    "installers": {
        "title": "HVAC Installers: Smart Upsell",
        "assumptions": [
            ("Installers accept a 20% revenue share.", "viability"),
            ("Techs can demo the app in under 5 minutes on site.", "feasibility"),
            ("Customers approve data collection at install time.", "viability"),
            ("Comfort-focused pitch converts better than savings-first.", "desirability"),
            ("Lead routing from installer CRM is feasible without deep integration.", "feasibility"),
            ("Post-install follow-ups lift attach rate by 30%.", "desirability"),
            ("No-code internal tool is enough for scheduling and support.", "feasibility"),
        ],
        "risk_truth": [0.6, 0.5, 0.62, 0.6, 0.5, 0.5, 0.4],
    },
}

# -----------------------------------------------------------------------------
# State init
# -----------------------------------------------------------------------------
def init_state():
    if "stage" in st.session_state:
        return
    st.session_state.stage = "intro"
    st.session_state.idea_key = None
    st.session_state.rank_order: List[int] = []  # indices of assumptions
    st.session_state.tokens = dict(ROUND_BUDGET)
    st.session_state.portfolio = {"r1": [], "r2": [], "r3": []}  # planned tests per round
    st.session_state.results = {"r1": [], "r2": [], "r3": []}    # outcomes per round
    st.session_state.scoring = {}
    st.session_state.log = []

def goto(stage: str):
    st.session_state.stage = stage
    st.experimental_rerun()

def header(active_idx: int):
    """A simple progress header; disabled buttons act as breadcrumbs."""
    steps = [
        "Intro", "Choose Idea", "Rank Risks",
        "Round 1 — Select", "Round 1 — Results",
        "Round 2 — Select", "Round 2 — Results",
        "Round 3 — Select", "Round 3 — Results",
        "Learning Summary", "Feedback & Score"
    ]
    cols = st.columns(len(steps))
    for i, lbl in enumerate(steps):
        with cols[i]:
            st.button(("✅ " if i == active_idx else "") + lbl, disabled=True)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def tokens_left(rk: str) -> int:
    return st.session_state.tokens[rk]

def current_assumptions() -> List[Tuple[str, str]]:
    key = st.session_state.idea_key
    return IDEA_CARDS[key]["assumptions"]

def success_probability(idea_key: str, ass_idx: int, fit: bool, strength: int, rank_pos: int) -> float:
    """
    Semi-realistic probability:
      - higher hidden risk → lower base
      - better fit and stronger tests → higher
      - earlier (riskier) ranks → slightly lower base
    """
    truth = IDEA_CARDS[idea_key]["risk_truth"][ass_idx]  # 0..1
    base = 0.55 - 0.25 * truth                      # 0.30..0.55
    base -= 0.05 * (0.2 * rank_pos)                 # earlier positions harder
    if fit:
        base += 0.12
    base += 0.06 * (strength - 1)                   # +0 / +0.06 / +0.12
    return max(0.05, min(0.90, base))

# -----------------------------------------------------------------------------
# Page: Intro
# -----------------------------------------------------------------------------
def page_intro():
    header(0)
    st.title("Simulation #2 — Designing & Running Early Experiments")
    st.caption("ThermaLoop: rank risks, pick scrappy tests, learn quickly.")
    st.markdown("""
**You will:**
1. **Choose** an idea focus (Homeowners, Landlords, or Installers)  
2. **Rank** assumptions from *highest → lowest* risk (use Up/Down controls)  
3. Run scrappy experiments over **3 rounds** using your token budget  
4. Review **learning** and receive **scoring + coaching** (with specific reasons)

**Tokens & costs:**  
Each round gives you tokens. Each experiment costs **2–4 tokens**.  
Add as many experiments per round as your tokens allow.
""")
    if st.button("Start"):
        goto("idea")

# -----------------------------------------------------------------------------
# Page: Choose Idea
# -----------------------------------------------------------------------------
def page_choose_idea():
    header(1)
    st.subheader("Choose your idea focus")
    cols = st.columns(len(IDEA_CARDS))
    for (key, card), c in zip(IDEA_CARDS.items(), cols):
        with c:
            st.markdown(f"**{card['title']}**")
            with st.expander("See sample assumptions"):
                for a, _tag in card["assumptions"]:
                    st.write("•", a)
            if st.button("Select", key=f"select_{key}"):
                st.session_state.idea_key = key
                st.session_state.rank_order = list(range(len(card["assumptions"])))
                goto("rank")

# -----------------------------------------------------------------------------
# Page: Rank Risks (no external package; Up/Down buttons)
# -----------------------------------------------------------------------------
def page_rank():
    header(2)
    st.subheader("Rank your assumptions (highest → lowest risk)")
    if not st.session_state.idea_key:
        st.info("Choose an idea first.")
        return

    assumptions = current_assumptions()
    order = st.session_state.rank_order

    st.caption("Use the Up / Down controls to move items. Top = riskiest.")
    for pos, idx in enumerate(order):
        a_text, _tag = assumptions[idx]
        colA, colB, colC = st.columns([8, 1, 1])
        with colA:
            st.write(f"**#{pos+1}**  {a_text}")
        with colB:
            if st.button("↑", key=f"up_{pos}", disabled=(pos == 0)):
                order[pos-1], order[pos] = order[pos], order[pos-1]
                st.experimental_rerun()
        with colC:
            if st.button("↓", key=f"dn_{pos}", disabled=(pos == len(order)-1)):
                order[pos+1], order[pos] = order[pos], order[pos+1]
                st.experimental_rerun()

    st.divider()
    if st.button("Proceed to Round 1"):
        goto("r1_select")

# -----------------------------------------------------------------------------
# Experiment selection UI
# -----------------------------------------------------------------------------
def experiment_card(round_key: str, ass_idx: int, a_text: str, a_tag: str):
    """Render all experiment options for a single assumption."""
    for exp in EXPERIMENTS:
        fits = "✅ Best fit" if a_tag in exp.tags_for_fit else "OK fit"
        disabled = tokens_left(round_key) < exp.cost
        with st.container(border=True):
            st.markdown(f"**{exp.name}**  ·  Cost **{exp.cost}**  ·  {fits}")
            st.caption(exp.description)
            if st.button(f"Add to plan ({exp.cost} tokens)", key=f"{round_key}_{ass_idx}_{exp.name}", disabled=disabled):
                st.session_state.tokens[round_key] -= exp.cost
                st.session_state.portfolio[round_key].append({
                    "ass_idx": ass_idx,
                    "assumption": a_text,
                    "tag": a_tag,
                    "exp_name": exp.name,
                    "cost": exp.cost,
                    "fit": a_tag in exp.tags_for_fit,
                    "strength": exp.strength
                })

def sidebar_plan(round_key: str):
    with st.sidebar:
        st.markdown(f"### {round_key.upper()} Plan")
        st.write(f"Tokens left: **{tokens_left(round_key)}**")
        if not st.session_state.portfolio[round_key]:
            st.caption("No experiments yet.")
        else:
            for i, itm in enumerate(st.session_state.portfolio[round_key], 1):
                st.write(f"{i}. {itm['exp_name']} → _{itm['assumption']}_ (cost {itm['cost']})")
            if st.button("Clear round plan", key=f"clear_{round_key}"):
                refund = sum(itm["cost"] for itm in st.session_state.portfolio[round_key])
                st.session_state.tokens[round_key] += refund
                st.session_state.portfolio[round_key].clear()

def page_round_select(round_key: str, header_idx: int, next_stage: str):
    header(header_idx)
    assumptions = current_assumptions()
    order = st.session_state.rank_order

    st.subheader(f"{round_key.upper()} — Select Experiments")
    st.write(f"Use your tokens (**{tokens_left(round_key)}** available) to add as many tests as you like.")
    sidebar_plan(round_key)

    # Show assumptions in current risk order; expand top few by default
    for rank_pos, idx in enumerate(order, 1):
        a_text, a_tag = assumptions[idx]
        with st.expander(f"#{rank_pos}  {a_text}", expanded=(rank_pos <= 2)):
            experiment_card(round_key, idx, a_text, a_tag)

    st.divider()
    col1, col2 = st.columns([1, 1])
    if col1.button("Run selected tests"):
        run_round(round_key)
        goto(next_stage)
    col2.caption("Tip: Fast learning → multiple small bets early, not one big bet.")

# -----------------------------------------------------------------------------
# Run a round
# -----------------------------------------------------------------------------
def run_round(round_key: str):
    idea = st.session_state.idea_key
    order = st.session_state.rank_order
    out = []
    for itm in st.session_state.portfolio[round_key]:
        rank_pos = order.index(itm["ass_idx"]) + 1
        p = success_probability(idea, itm["ass_idx"], itm["fit"], itm["strength"], rank_pos)
        success = random.random() < p
        detail = random.choice([
            "Strong positive signal (quotes + conversion).",
            "Moderate interest; conversion below target.",
            "Mixed feedback; unclear value articulation.",
            "Low signal; likely invalid."
        ])
        out.append({
            "Assumption": itm["assumption"],
            "Experiment": itm["exp_name"],
            "Success": success,
            "Detail": detail,
            "RankPos": rank_pos,
            "Fit": "Good" if itm["fit"] else "OK",
            "Strength": itm["strength"],
            "Cost": itm["cost"]
        })
    st.session_state.results[round_key] = out

# -----------------------------------------------------------------------------
# Results page
# -----------------------------------------------------------------------------
def page_round_results(round_key: str, header_idx: int, next_stage: str, title: str):
    header(header_idx)
    st.subheader(title)
    data = st.session_state.results[round_key]
    if not data:
        st.info("No tests were run.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df, hide_index=True, use_container_width=True)
        sr = sum(1 for r in data if r["Success"]) / len(data)
        spent = sum(r["Cost"] for r in data)
        st.write(f"Success rate: **{sr:.0%}**  ·  Tokens spent: **{spent}**")
    if st.button("Next"):
        goto(next_stage)

# -----------------------------------------------------------------------------
# Learning summary
# -----------------------------------------------------------------------------
def page_learning():
    header(9)
    st.subheader("Learning Summary")
    all_rows = st.session_state.results["r1"] + st.session_state.results["r2"] + st.session_state.results["r3"]
    if not all_rows:
        st.info("You have no results yet.")
        return
    df = pd.DataFrame(all_rows)
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("#### Per-assumption roll-up")
    roll = df.groupby("Assumption")["Success"].agg(["count", "mean"]).reset_index()
    roll.rename(columns={"count": "tests", "mean": "success_rate"}, inplace=True)
    st.dataframe(roll, hide_index=True, use_container_width=True)

    if st.button("View Feedback & Score"):
        calc_score()
        goto("score")

# -----------------------------------------------------------------------------
# Scoring
# -----------------------------------------------------------------------------
def calc_score():
    idea = st.session_state.idea_key
    assumptions = IDEA_CARDS[idea]["assumptions"]
    order = st.session_state.rank_order

    # Coverage of top 3 risks in Round 1
    r1_targets = [r["Assumption"] for r in st.session_state.results["r1"]]
    top3_texts = [assumptions[i][0] for i in order[:3]]
    coverage = len([t for t in r1_targets if t in top3_texts]) / max(1, len(top3_texts))

    # Experiment Fit
    all_rows = st.session_state.results["r1"] + st.session_state.results["r2"] + st.session_state.results["r3"]
    if all_rows:
        fit_points = sum((1.0 if r["Fit"] == "Good" else 0.6) * (1 + 0.3 * (r["Strength"] - 1)) for r in all_rows)
        fit_pct = min(1.0, fit_points / len(all_rows))
    else:
        fit_pct = 0.0

    # Resource efficiency
    spent = {rk: sum(itm["Cost"] for itm in st.session_state.portfolio[rk]) for rk in ["r1", "r2", "r3"]}
    idle_tokens = sum(st.session_state.tokens.values())
    early_bias = min(1.0, (spent["r1"] + 0.5 * spent["r2"]) / max(1, sum(spent.values()))) if sum(spent.values()) else 0.0
    efficiency = max(0.0, 1.0 - (idle_tokens / (ROUND_BUDGET["r1"] + ROUND_BUDGET["r2"] + ROUND_BUDGET["r3"])) * 0.8)
    resource = 0.6 * early_bias + 0.4 * efficiency

    # Learning outcome (success rate + diversity)
    if all_rows:
        sr = sum(1 for r in all_rows if r["Success"]) / len(all_rows)
        diversity = len(set(r["Assumption"] for r in all_rows)) / max(1, len(assumptions))
        learning = 0.6 * sr + 0.4 * diversity
    else:
        learning = 0.0

    # Assumption Quality proxy (rank + early coverage)
    quality = 0.5 + 0.5 * coverage

    to_pct = lambda x: int(100 * max(0.0, min(1.0, x)))
    S = st.session_state.scoring = {
        "Assumption Quality": to_pct(quality),
        "Risk Prioritization": to_pct(coverage),
        "Experiment Fit": to_pct(fit_pct),
        "Resource Efficiency": to_pct(resource),
        "Learning Outcome": to_pct(learning),
    }
    S["Total"] = int(
        0.30 * S["Assumption Quality"] +
        0.25 * S["Risk Prioritization"] +
        0.25 * S["Experiment Fit"] +
        0.10 * S["Resource Efficiency"] +
        0.10 * S["Learning Outcome"]
    )

    # Reasons tailored to action
    reasons = {}
    # Risk Prioritization
    if coverage >= 0.67:
        reasons["Risk Prioritization"] = "You tested most of the top-ranked risks in Round 1—good sequencing."
    elif coverage >= 0.34:
        reasons["Risk Prioritization"] = "You tackled some top risks early; next time, move the scariest unknowns to Round 1."
    else:
        reasons["Risk Prioritization"] = "You left top risks for later rounds—start with the hardest unknowns to maximize learning."

    # Experiment Fit
    if fit_pct >= 0.85:
        reasons["Experiment Fit"] = "Strong alignment between assumption types and chosen tests."
    elif fit_pct >= 0.70:
        reasons["Experiment Fit"] = "Mixed alignment—some tests were ideal, others only loosely matched the risk."
    else:
        reasons["Experiment Fit"] = "Many tests didn’t fit the assumption type; review the card descriptions to improve fit."

    # Resource Efficiency
    if resource >= 0.8:
        reasons["Resource Efficiency"] = "Healthy early spend with little idle budget—nice pacing across rounds."
    elif resource >= 0.6:
        reasons["Resource Efficiency"] = "Reasonable pacing, but you could shift a bit more learning into earlier rounds."
    else:
        reasons["Resource Efficiency"] = "Too many tokens were left idle or saved for late rounds—run more scrappy tests early."

    # Assumption Quality
    if quality >= 0.8:
        reasons["Assumption Quality"] = "Your ranking looks thoughtful and you aimed at high-risk unknowns first."
    else:
        reasons["Assumption Quality"] = "Clarify and rank assumptions more sharply—place the scariest unknowns at the top."

    # Learning Outcome
    if learning >= 0.7:
        reasons["Learning Outcome"] = "Good mix of clear signals and spread; you can now refine metrics and double-down."
    elif learning >= 0.45:
        reasons["Learning Outcome"] = "Some actionable signals emerged; add a follow-up test where results were ambiguous."
    else:
        reasons["Learning Outcome"] = "Few actionable signals—prefer tests with stronger confidence gain (e.g., Pre-order, Smoke test)."

    S["_reasons"] = reasons

# -----------------------------------------------------------------------------
# Score page
# -----------------------------------------------------------------------------
def page_score():
    header(10)
    st.subheader("Feedback & Score")
    S = st.session_state.scoring
    if not S:
        st.info("Run through the rounds first.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Assumption Quality", S["Assumption Quality"])
        st.metric("Risk Prioritization", S["Risk Prioritization"])
        st.metric("Experiment Fit", S["Experiment Fit"])
    with c2:
        st.metric("Resource Efficiency", S["Resource Efficiency"])
        st.metric("Learning Outcome", S["Learning Outcome"])
        st.success(f"Total Score: {S['Total']}")

    st.markdown("### Reasons")
    for k in ["Assumption Quality", "Risk Prioritization", "Experiment Fit", "Resource Efficiency", "Learning Outcome"]:
        st.write(f"**{k}:** {S['_reasons'][k]}")

    st.markdown("### What to do next")
    st.write("• Plan a follow-up test for any assumption with mixed/weak signals.")
    st.write("• Convert a successful scrappy test into a clearer metric target for your next milestone.")
    st.divider()
    if st.button("Restart Simulation"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        init_state()
        st.experimental_rerun()

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
def main():
    init_state()
    stage = st.session_state.stage

    if stage == "intro":
        page_intro()
    elif stage == "idea":
        page_choose_idea()
    elif stage == "rank":
        page_rank()
    elif stage == "r1_select":
        page_round_select("r1", 3, "r1_results")
    elif stage == "r1_results":
        page_round_results("r1", 4, "r2_select", "Round 1 — Results")
    elif stage == "r2_select":
        page_round_select("r2", 5, "r2_results")
    elif stage == "r2_results":
        page_round_results("r2", 6, "r3_select", "Round 2 — Results")
    elif stage == "r3_select":
        page_round_select("r3", 7, "r3_results")
    elif stage == "r3_results":
        page_round_results("r3", 8, "learning", "Round 3 — Results")
    elif stage == "learning":
        page_learning()
    elif stage == "score":
        page_score()
    else:
        page_intro()

if __name__ == "__main__":
    main()
