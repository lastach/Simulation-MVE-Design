import math
import random
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="LaunchX: Designing & Running Early Experiments",
    page_icon="🧪",
    layout="wide",
)

# Hide Streamlit default menu, footer, and header for cleaner look
hide_streamlit_style = """
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --------------------------------------------------------------------------------------
# Global targets / knobs (as agreed)
# --------------------------------------------------------------------------------------
TARGET_CPLP = 3.0          # Target Cost Per Learning Point (tokens per learning point)
TARGET_LEARNING_POINTS = 10  # Target learning points across the whole sim

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
        st.session_state.assumptions = []      # all assumptions for selected idea
    if "ranked" not in st.session_state:
        st.session_state.ranked = []           # ordered copy for risk priority (learner edits)
    if "round" not in st.session_state:
        st.session_state.round = 1
    if "tokens_total" not in st.session_state:
        st.session_state.tokens_total = 30     # TOTAL pool across all 3 rounds
    if "tokens_spent" not in st.session_state:
        st.session_state.tokens_spent = 0      # consumed when a round actually runs
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
# Idea cards & assumptions (ThermaLoop variants)
# --------------------------------------------------------------------------------------
IDEAS = {
    "home_comfort": {
        "title": "Home Comfort Optimizer",
        "one_liner": "Smart vents + app to eliminate hot/cold rooms and reduce bills.",
        "hook": "Millions of homeowners fight the same battle every season: one room is freezing while another is sweltering. What if a simple kit could fix that without a contractor visit?",
        "customer": "Homeowners",
        "why_exciting": "Massive TAM (130M US households), visceral pain point, recurring revenue potential through seasonal tuning subscriptions.",
        "assumptions": [
            {"id": "A1", "text": "Homeowners perceive uneven room temps as a top 3 comfort issue.", "type": "desirability"},
            {"id": "A2", "text": ">=20% of target homeowners will try a no-tools 'one room fix' kit.", "type": "desirability"},
            {"id": "A3", "text": "A single room kit can deliver a noticeable comfort delta in 48 hours.", "type": "feasibility"},
            {"id": "A4", "text": "BLE sensors + app can estimate room temp and airflow accurately enough.", "type": "feasibility"},
            {"id": "A5", "text": "Installed cost of starter kit <= $129 with >=60% gross margin.", "type": "viability"},
            {"id": "A6", "text": "Homeowners will accept a subscription ($5-$9/mo) for seasonal tuning.", "type": "viability"},
            {"id": "A7", "text": "Return rate for the starter kit stays under 10%.", "type": "viability"},
            {"id": "A8", "text": "Install instructions can be done self-serve without pro help.", "type": "feasibility"},
        ],
        "truth": {"A1": 2, "A2": 3, "A3": 2, "A4": 1, "A5": 2, "A6": 3, "A7": 2, "A8": 1},
    },
    "landlord_energy": {
        "title": "Landlord Energy Saver",
        "one_liner": "LoRa sensors + portal for small landlords to cut HVAC waste and get rebates.",
        "hook": "Small landlords are bleeding money on HVAC in empty units and off-hours, but they have zero visibility into what is happening across their properties. What if a $0-down sensor kit could show them exactly where the waste is?",
        "customer": "Small landlords (5-50 units)",
        "why_exciting": "Clear ROI story (payback in months), sticky SaaS revenue, rebate partnerships create a built-in acquisition channel.",
        "assumptions": [
            {"id": "B1", "text": "Small landlords are willing to pilot a $0 down kit for 30 days.", "type": "desirability"},
            {"id": "B2", "text": "HVAC runtime can be reduced >=10% without tenant complaints.", "type": "feasibility"},
            {"id": "B3", "text": "A property portal reduces landlord effort vs. spreadsheets.", "type": "desirability"},
            {"id": "B4", "text": "End-to-end logistics (ship, install, support) is manageable.", "type": "feasibility"},
            {"id": "B5", "text": "Gross margin >=55% on device + >=70% on SaaS at $6-12/unit/mo.", "type": "viability"},
            {"id": "B6", "text": "Rebate paperwork & partner channel can acquire leads under $180 CAC.", "type": "viability"},
            {"id": "B7", "text": "Tenants won't disable devices or complain about privacy.", "type": "desirability"},
            {"id": "B8", "text": "Landlords will sign annual agreements if payback <= 9 months.", "type": "viability"},
            {"id": "B9", "text": "Gateway connectivity (LoRa/LTE) works in >=85% of buildings without site visit.", "type": "feasibility"},
        ],
        "truth": {"B1": 2, "B2": 3, "B3": 2, "B4": 2, "B5": 2, "B6": 3, "B7": 2, "B8": 2, "B9": 2},
    },
    "installer_tools": {
        "title": "Installer Pro Toolkit",
        "one_liner": "A pro kit + mobile app for HVAC installers to diagnose airflow issues fast.",
        "hook": "HVAC installers spend 30+ minutes per job diagnosing airflow problems by feel and guesswork. A $300 diagnostic kit that gives a clear pass/fail in under 5 minutes could become an industry standard.",
        "customer": "HVAC installers and contractors",
        "why_exciting": "B2B with clear time-savings ROI, strong word-of-mouth in trade communities, wholesale distribution is a proven channel.",
        "assumptions": [
            {"id": "C1", "text": "Installers see airflow diagnosis as a high-value differentiator.", "type": "desirability"},
            {"id": "C2", "text": "Pros will pre-order a kit at $299-$399 if it saves 30 min per job.", "type": "desirability"},
            {"id": "C3", "text": "Clamp sensors + app yield a clear pass/fail signal in < 5 minutes.", "type": "feasibility"},
            {"id": "C4", "text": "Kit COGS can hit <= $120 at pilot volumes.", "type": "viability"},
            {"id": "C5", "text": "Tool integrates with common thermostats for readings/logs.", "type": "feasibility"},
            {"id": "C6", "text": "Wholesale distributors will carry the kit with standard margin.", "type": "viability"},
            {"id": "C7", "text": "Pros actually use the tool in the field (not a shelf product).", "type": "desirability"},
            {"id": "C8", "text": "In-app 'good/better/best' recommendations reduce callbacks by >=15%.", "type": "feasibility"},
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
        desc=("Publish a page stating value + offer with a clear CTA (e.g., 'Join waitlist'). "
              "Drive a small trickle of traffic and measure visits/signups."),
        fit=["desirability", "viability"],
    ),
    "concierge": dict(
        label="Concierge Trial",
        cost=4,
        days=7,
        desc=("Manually deliver the experience to 1-5 users. "
              "Look for repeat intent ('Would you do it again next week?')."),
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
        desc=("Run 2-3 ad variants to the same audience; see which message earns more qualified clicks."),
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
# Narrative templates for experiment results (per idea variant)
# These make results feel like real founder moments rather than data readouts.
# --------------------------------------------------------------------------------------
NARRATIVE_TEMPLATES = {
    # ---- HOME COMFORT ----
    ("home_comfort", "landing"): {
        "success_strong": "You put up a simple landing page: 'Fix your hot and cold rooms for under $130, no contractor needed.' {visits} people visited over 3 days, and {signups} signed up for the waitlist. That is a {rate}% conversion rate. Homeowners are clearly searching for this solution, and the no-contractor angle resonated. You have early demand signal.",
        "success_weak": "Your landing page got {visits} visits and {signups} sign-ups ({rate}% conversion). Not bad, but not a slam dunk. People are curious, but the value prop might need sharper framing. Are they signing up because they are excited, or just mildly interested?",
        "failure": "The landing page pulled {visits} visits but only {signups} sign-ups ({rate}%). The traffic was there, but something about the offer did not compel action. Maybe 'smart vents' sounds too techy, or $129 feels steep for something they have never heard of.",
    },
    ("home_comfort", "concierge"): {
        "success_strong": "You personally installed a prototype kit in {trials} homes over a week. {would_pay} out of {trials} said they would pay for it, and {repeat} asked when they could get the 'real' version. One homeowner texted you a photo of her thermostat showing balanced temps across rooms for the first time in years. This is the kind of signal money cannot buy.",
        "success_weak": "You ran a concierge trial in {trials} homes. {would_pay} showed purchase intent, but only {repeat} followed up about repeat use. They liked it, but the 'must-have' urgency is not there yet. You may need to nail the installation experience before the product clicks.",
        "failure": "You manually set up kits in {trials} homes. Only {would_pay} showed any purchase intent, and {repeat} wanted to continue. The comfort improvement was noticeable but not dramatic enough to justify the hassle of a new device. Back to the drawing board on the value delivery.",
    },
    ("home_comfort", "wizard"): {
        "success_strong": "You built a clickable app prototype that 'controlled' smart vents (you were adjusting them manually behind the scenes). {tasks} of {sessions} users completed the full setup flow, reaching comfortable temps in about {ttv} minutes. Users trusted the interface and the experience felt magical to them.",
        "success_weak": "Your Wizard-of-Oz prototype got {tasks} out of {sessions} users through the setup flow. Time-to-value was {ttv} minutes. Some users got confused at the 'room mapping' step. The core concept works, but the UX needs simplification before it scales.",
        "failure": "Only {tasks} of {sessions} users completed the Wizard-of-Oz flow. At {ttv} minutes to value, the experience felt too complex. Users expected instant results, not a multi-step calibration process. The automation layer needs to be much simpler.",
    },
    ("home_comfort", "preorder"): {
        "success_strong": "{confirmed} people put down a deposit out of {visitors} who saw your offer page. That is real money on the table for a product that does not exist yet. At $129 per kit, these early believers are telling you the price point works.",
        "success_weak": "{confirmed} out of {visitors} visitors confirmed a pre-order. Some signal, but the conversion rate suggests the offer page needs work, or maybe the $129 price feels risky without reviews or a demo video.",
        "failure": "Only {confirmed} out of {visitors} visitors put down a deposit. Homeowners browsed but did not commit. The gap between 'interested' and 'willing to pay upfront' is wider than expected.",
    },
    ("home_comfort", "expert"): {
        "success_strong": "You interviewed {experts} HVAC and smart-home experts. {converge} independently flagged the same thing: BLE sensor accuracy is the technical bottleneck, but it is solvable with off-the-shelf components. One expert sketched a bill of materials that hit your $129 target. You now have a feasibility roadmap.",
        "success_weak": "Your {experts} expert interviews surfaced useful but scattered insights. {converge} agreed on cost drivers, but opinions diverged on sensor reliability. You have direction, but more prototyping is needed before you can commit to a BOM.",
        "failure": "{experts} experts gave you {experts} different answers. No convergence on feasibility or cost drivers. The technical path is murkier than expected. You may need to narrow your technical approach before experts can give you useful feedback.",
    },
    ("home_comfort", "benchmark"): {
        "success_strong": "You benchmarked your smart vent approach against the common workaround (manually adjusting dampers + space heaters). Your method was {delta} minutes faster and delivered more consistent temps. Homeowners who saw the comparison said the difference was 'obvious.'",
        "success_weak": "The benchmark showed your approach was {delta_desc} compared to manual workarounds ({ours} vs {workaround} min). There is an improvement, but it is not dramatic enough to make homeowners switch from their current habits without a stronger pitch.",
        "failure": "Your benchmark against manual workarounds came in at {ours} min vs {workaround} min. The improvement was marginal, and in some cases the workaround was actually {delta_desc}. You need to demonstrate a bigger delta to justify a new purchase.",
    },
    ("home_comfort", "adsplit"): {
        "success_strong": "You ran two ad variants to homeowner audiences across {imps} impressions. Variant {winner} ('Stop fighting your thermostat') crushed it at {win_ctr}% CTR. That messaging angle clearly resonates. You found the emotional trigger: frustration with the thermostat, not energy savings.",
        "success_weak": "Across {imps} impressions, variant {winner} won with {win_ctr}% CTR, but both variants performed similarly. You learned which angle is slightly better, but neither message drove exceptional engagement. The hook needs more work.",
        "failure": "Both ad variants underperformed across {imps} impressions. The best CTR was {win_ctr}%. Homeowners scrolled right past. Your messaging is not capturing attention. Consider testing a completely different angle, maybe comfort instead of savings.",
    },
    ("home_comfort", "diary"): {
        "success_strong": "{participants} homeowners logged {episodes} temperature complaints over a week (avg {avg} per person). The pattern was clear: most pain happens in the morning and evening, exactly when families are home. This frequency data proves the problem is daily, not occasional.",
        "success_weak": "{participants} participants logged {episodes} episodes (avg {avg}/person). The pain is real but less frequent than expected. Some participants forgot to log, so the true number might be higher. Consider whether 'annoying' is enough to drive a purchase.",
        "failure": "Only {episodes} pain episodes from {participants} participants ({avg}/person). The problem exists, but it is not top-of-mind enough for people to remember to log it. If they do not notice it daily, will they pay $129 to fix it?",
    },

    # ---- LANDLORD ENERGY ----
    ("landlord_energy", "landing"): {
        "success_strong": "Your landing page targeted small landlords: 'See exactly where your HVAC budget is leaking, $0 to start.' {visits} visits, {signups} sign-ups ({rate}%). Landlords are actively looking for ways to cut operating costs, and the free trial angle lowered the barrier.",
        "success_weak": "{visits} visits and {signups} sign-ups ({rate}%). Some traction, but landlords are skeptical of 'free' offers. Many probably assumed there is a catch. The value prop needs to lead with the dollar savings, not the technology.",
        "failure": "{visits} visits, {signups} sign-ups ({rate}%). Landlords did not bite. They may not be searching for this type of solution online, or the 'sensor kit' framing sounds like too much hassle for a busy property manager.",
    },
    ("landlord_energy", "concierge"): {
        "success_strong": "You personally installed sensors in {trials} properties and ran the dashboard for landlords manually. {would_pay} wanted to keep going, and {repeat} asked about annual pricing. One landlord showed you his utility bill and pointed out the exact month your system would have caught a $400 HVAC overrun. That is the story that sells this product.",
        "success_weak": "{would_pay} of {trials} landlords saw value, but only {repeat} committed to continued use. The dashboard impressed them, but the installation process took longer than promised. Logistics will make or break this business.",
        "failure": "Across {trials} properties, only {would_pay} landlords showed purchase intent. They liked the data but did not trust the savings projections enough to pay. You need harder proof: actual utility bill comparisons before and after.",
    },
    ("landlord_energy", "wizard"): {
        "success_strong": "Your prototype portal showed real-time HVAC data (with you manually updating it behind the scenes). {tasks} of {sessions} landlords completed the full workflow. Time-to-value was {ttv} minutes. Landlords loved seeing 'money saved per unit' as the primary metric.",
        "success_weak": "{tasks} of {sessions} landlords got through the Wizard-of-Oz flow in {ttv} minutes. The portal concept works, but some landlords got lost navigating between properties. The multi-property UX needs work.",
        "failure": "Only {tasks} of {sessions} landlords completed the flow. At {ttv} minutes, it felt too complex. Landlords manage properties on their phones between meetings. This needs to be glanceable, not a dashboard you sit down with.",
    },
    ("landlord_energy", "preorder"): {
        "success_strong": "{confirmed} landlords put deposits down from {visitors} who saw the offer. For a B2B hardware+SaaS product, that conversion rate is remarkable. These are landlords betting real money that your system will save them more than it costs.",
        "success_weak": "{confirmed} deposits from {visitors} visitors. Some signal, but landlords are cautious spenders. They want to see a case study from a peer before committing their own money.",
        "failure": "Only {confirmed} deposits from {visitors} visitors. Landlords do not pre-order. They need proof from an actual pilot before they will commit. You may need to give away 10 free pilots to get your first 3 paying customers.",
    },
    ("landlord_energy", "expert"): {
        "success_strong": "You spoke with {experts} experts across property management, HVAC engineering, and utility rebate programs. {converge} converged on the same insight: the rebate channel is the real wedge. Utility companies are desperate to hit energy reduction targets and will subsidize your hardware to get there.",
        "success_weak": "{experts} expert conversations yielded useful but mixed signals. {converge} agreed on cost drivers, but the rebate landscape varies wildly by region. Your go-to-market will need to be geography-specific.",
        "failure": "{experts} experts, {converge} points of convergence. The signal was noisy. Everyone agreed the market exists, but nobody could point you to a clear path through the rebate paperwork maze. This channel may be harder to crack than expected.",
    },
    ("landlord_energy", "benchmark"): {
        "success_strong": "You compared your sensor approach to the landlord's current method (quarterly manual thermostat checks). Your system flagged HVAC issues {delta} minutes faster on average. One simulated scenario caught a stuck damper that would have wasted $200 in a month. The comparison made the ROI tangible.",
        "success_weak": "Your benchmark showed a {delta_desc} improvement over manual checks ({ours} vs {workaround} min). The improvement is real but incremental. Landlords who already have a maintenance routine may not see enough delta to justify a new system.",
        "failure": "The benchmark did not clearly favor your approach ({ours} min vs {workaround} min). For landlords who are already checking their properties regularly, your system's advantage was not obvious enough to justify the change.",
    },
    ("landlord_energy", "adsplit"): {
        "success_strong": "You tested two ad angles with {imps} impressions targeting landlords. Variant {winner} ('Your empty units are running up the HVAC bill right now') won at {win_ctr}% CTR. The loss-aversion framing, specifically waste happening right now, outperformed the savings angle.",
        "success_weak": "Across {imps} impressions, variant {winner} edged out at {win_ctr}% CTR. Both performed moderately. Landlords are a hard audience to reach via ads. You may need to go where they already are: property management forums, local landlord associations.",
        "failure": "Neither ad variant performed well across {imps} impressions (best: {win_ctr}% CTR). Small landlords may not be reachable through paid ads. Consider partnerships with property management software companies instead.",
    },
    ("landlord_energy", "diary"): {
        "success_strong": "{participants} landlords tracked HVAC issues for a week. {episodes} total incidents (avg {avg}/person). The data revealed that most waste happens overnight and on weekends, exactly when nobody is checking. This frequency validates the always-on monitoring pitch.",
        "success_weak": "{participants} landlords logged {episodes} incidents ({avg}/person). The frequency is moderate. Some landlords only manage a few units and do not experience enough incidents to justify a monthly subscription.",
        "failure": "Only {episodes} incidents from {participants} landlords ({avg}/person). The problem may not be frequent enough for landlords with well-maintained properties. Your target customer might be specifically landlords with older buildings.",
    },

    # ---- INSTALLER TOOLS ----
    ("installer_tools", "landing"): {
        "success_strong": "Your landing page hit the installer community: 'Diagnose airflow in 5 minutes, not 30.' {visits} visits, {signups} sign-ups ({rate}%). Installers shared it in their group chats unprompted. When a B2B tool goes viral in a trade community, you have something special.",
        "success_weak": "{visits} visits, {signups} sign-ups ({rate}%). Installers checked it out but many bounced. They want to see the tool in action, not just read about it. A demo video might convert better than a landing page for this audience.",
        "failure": "{visits} visits, only {signups} sign-ups ({rate}%). Installers are skeptical of new tools that promise to replace their expertise. The messaging may need to position this as 'enhancing' their skills, not replacing their judgment.",
    },
    ("installer_tools", "concierge"): {
        "success_strong": "You showed up at {trials} job sites with a prototype kit. {would_pay} installers said they would buy it at $299, and {repeat} asked if they could keep the prototype. One installer used it to diagnose a problem in 3 minutes that normally takes 45. He said, 'This is going to change how I bid jobs.' That is your testimonial.",
        "success_weak": "{would_pay} of {trials} installers showed interest, {repeat} would use it again. They liked the speed, but some worried about accuracy on older systems. The tool needs to work reliably across different HVAC generations.",
        "failure": "Only {would_pay} of {trials} installers saw enough value. Most said their experience lets them diagnose fast enough already. The tool needs to solve a problem they cannot solve by hand, not just make an existing skill slightly faster.",
    },
    ("installer_tools", "wizard"): {
        "success_strong": "Your Wizard-of-Oz app showed pass/fail readings (you were calculating them on your laptop behind the scenes). {tasks} of {sessions} installers completed the diagnostic flow in about {ttv} minutes. They trusted the readings because the interface was clean and the output matched their gut instinct, then added precision they could not get on their own.",
        "success_weak": "{tasks} of {sessions} installers finished the flow. Time-to-value was {ttv} minutes, longer than the '5-minute' promise. The readings were useful, but the sensor placement step was confusing. Field UX needs to be dead simple.",
        "failure": "Only {tasks} of {sessions} installers completed the flow. {ttv} minutes was too long. Installers work on tight schedules and will not adopt a tool that slows them down during the learning curve, even if it pays off later.",
    },
    ("installer_tools", "preorder"): {
        "success_strong": "{confirmed} installers put deposits down out of {visitors} who saw the offer. For a $299-$399 tool, that is strong pre-order signal. These are pros who see enough value to bet on an unreleased product. You have your first beta testers.",
        "success_weak": "{confirmed} deposits from {visitors} visitors. Some interest, but installers generally want to hold a tool before buying. Consider offering a 'try before you buy' program at trade shows.",
        "failure": "Only {confirmed} of {visitors} visitors pre-ordered. Installers do not buy tools they have not held. The pre-order model may not work for this audience. You need hands-on demos at trade events.",
    },
    ("installer_tools", "expert"): {
        "success_strong": "You talked to {experts} HVAC industry experts (distributors, veteran installers, trade publication editors). {converge} agreed: the biggest unmet need is not diagnosis speed but documentation. Installers need proof of work for callbacks. If your tool generates a diagnostic report, it becomes indispensable for liability protection.",
        "success_weak": "{experts} experts gave useful input. {converge} agreed on key feasibility constraints, mainly around sensor accuracy in different duct configurations. The technical path is narrower than expected, but workable.",
        "failure": "{experts} conversations, {converge} convergent findings. The expert community is fragmented. Trade schools teach one diagnostic method, manufacturers recommend another, and field veterans do their own thing. Building a tool that works for all three will be harder than anticipated.",
    },
    ("installer_tools", "benchmark"): {
        "success_strong": "You benchmarked your kit against the standard method (manual airflow hood + experience). Your tool was {delta} minutes faster and caught 2 issues the manual method missed. The accuracy advantage, not just speed, is what makes this compelling.",
        "success_weak": "Your benchmark showed a {delta_desc} comparison ({ours} vs {workaround} min). Speed is comparable, but your tool provided more consistent readings. The value might be in standardization rather than raw speed.",
        "failure": "The benchmark showed mixed results ({ours} min vs {workaround} min). Experienced installers were actually faster with their existing methods. Your tool's advantage may only apply to less experienced techs, which narrows the market.",
    },
    ("installer_tools", "adsplit"): {
        "success_strong": "You ran ads across {imps} impressions in HVAC trade forums. Variant {winner} ('Bill for the diagnosis, not just the fix') won at {win_ctr}% CTR. The revenue angle, helping installers justify a diagnostic fee, resonated more than the time-savings angle.",
        "success_weak": "Across {imps} impressions, variant {winner} performed best at {win_ctr}% CTR. Moderate engagement. Installers respond better to peer recommendations than ads. Consider a referral program for your beta users.",
        "failure": "Both ad variants underperformed across {imps} impressions (best: {win_ctr}% CTR). This audience does not respond well to online ads. Trade shows, supply house partnerships, and word-of-mouth are likely better channels.",
    },
    ("installer_tools", "diary"): {
        "success_strong": "{participants} installers logged airflow diagnosis time for a week. {episodes} diagnosis events, averaging {avg} per person. The data confirmed installers spend significant time on diagnosis daily. A tool that cuts that by even 50% saves hours per week.",
        "success_weak": "{participants} installers, {episodes} logged events ({avg}/person). Some installers log very few airflow issues because they handle simpler jobs. Your core customer might be specifically commercial/multi-zone installers.",
        "failure": "Only {episodes} events from {participants} installers ({avg}/person). The frequency was lower than expected. Many installs do not require detailed airflow diagnosis. Your addressable use case might be narrower than the total installer market.",
    },
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
    random.shuffle(shuffled)       # randomize initial order so learner must reorder
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
        "Round 1: Select",
        "Round 1: Results",
        "Round 2: Select",
        "Round 2: Results",
        "Round 3: Select",
        "Round 3: Results",
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
# Returns dict of values for narrative template interpolation
# --------------------------------------------------------------------------------------
def quant_for_experiment(exp_key: str, rng: random.Random) -> dict:
    if exp_key == "landing":
        visits = rng.randint(800, 1500)
        signups = rng.randint(20, 120)
        rate = round(signups / visits * 100, 1)
        return {"visits": f"{visits:,}", "signups": str(signups), "rate": f"{rate}%"}

    if exp_key == "adsplit":
        imps = rng.randint(900, 2000)
        ctr_a = round(2.8 + 2.5 * rng.random(), 1)
        ctr_b = round(ctr_a * (0.85 + 0.3 * rng.random()), 1)
        winner = "A" if ctr_a >= ctr_b else "B"
        win_ctr = ctr_a if winner == "A" else ctr_b
        return {"imps": f"{imps:,}", "winner": winner, "win_ctr": f"{win_ctr}%"}

    if exp_key == "concierge":
        trials = rng.randint(3, 6)
        would_pay = rng.randint(max(1, trials // 2), trials)
        repeat = rng.randint(0, would_pay)
        return {"trials": str(trials), "would_pay": str(would_pay), "repeat": str(repeat)}

    if exp_key == "preorder":
        visitors = rng.randint(120, 300)
        confirmed = rng.randint(1, 12)
        return {"visitors": str(visitors), "confirmed": str(confirmed)}

    if exp_key == "wizard":
        sessions = rng.randint(6, 14)
        tasks = rng.randint(max(2, sessions // 3), sessions)
        ttv = rng.randint(6, 18)
        return {"sessions": str(sessions), "tasks": str(tasks), "ttv": str(ttv)}

    if exp_key == "expert":
        experts = rng.randint(3, 6)
        converge = rng.randint(max(1, experts // 3), experts)
        return {"experts": str(experts), "converge": str(converge)}

    if exp_key == "benchmark":
        ours = rng.randint(8, 18)
        workaround = ours + rng.randint(-3, 6)
        delta = workaround - ours
        better = "faster" if delta > 0 else "slower"
        return {
            "ours": str(ours), "workaround": str(workaround),
            "delta": f"{abs(delta)}", "delta_desc": f"{abs(delta)} min {better}",
        }

    if exp_key == "diary":
        participants = rng.randint(4, 8)
        episodes = rng.randint(participants * 3, participants * 10)
        avg = round(episodes / participants, 1)
        return {"participants": str(participants), "episodes": str(episodes), "avg": str(avg)}

    return {}


def build_narrative(idea_key: str, exp_key: str, success: bool, signal: str, quant_data: dict) -> str:
    """Build a rich narrative for an experiment result using templates."""
    template_key = (idea_key, exp_key)
    templates = NARRATIVE_TEMPLATES.get(template_key)

    if not templates:
        # Fallback for any missing combination
        if success and signal == "strong":
            return f"Strong result. The data supports your hypothesis. Numbers: {quant_data}"
        elif success:
            return f"Some evidence emerged, but the signal is not definitive. Numbers: {quant_data}"
        else:
            return f"This experiment did not produce supporting evidence this round. Numbers: {quant_data}"

    if success and signal == "strong":
        template = templates["success_strong"]
    elif success:
        template = templates["success_weak"]
    else:
        template = templates["failure"]

    try:
        return template.format(**quant_data)
    except KeyError:
        return template  # If some vars are missing, show the template as-is


# --------------------------------------------------------------------------------------
# Simulation engine
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

    # Signal: fit tends to strong
    if not success:
        signal = "no-signal"
    else:
        signal = "strong" if (fit and rng.random() < 0.8) else "weak"

    quant_data = quant_for_experiment(ek, rng)
    narrative = build_narrative(st.session_state.idea_key, ek, success, signal, quant_data)

    return dict(
        aid=aid,
        experiment=ek,
        success=success,
        signal=signal,
        narrative=narrative,
        quant_data=quant_data,
        cost=e["cost"],
        days=e["days"],
        assumption_type=a["type"],
        fit=fit,
    )


def run_round(round_idx: int):
    """Run all scheduled tests in a round. Parallelism: time = max(days) in the round."""
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
    Returns: (score_0_25, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak)
    """
    total_cost = sum(r["cost"] for rnd in (1, 2, 3) for r in st.session_state.results[rnd])
    # Within a round, tests run in parallel: time = max(days) in that round
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
    score = round(25 * (efficiency_pct / 100.0))  # map 0-100% to 0-25 points
    return score, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak


def risk_prioritization_score() -> Tuple[int, float, float, dict]:
    """
    Full-ranking scoring:
    - For each ranked position i (1..N):
      base points = 3 if exact, 2 if off by 1, 1 if off by 2, else 0
      weight = 2.0 if i<=3; 1.5 if 4<=i<=6; 1.0 if i>=7
    - Category score (0-25) = 25 * (achieved_points / max_points)
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
        "items": per_item,
    }
    return score, achieved, max_points, details


def compute_score() -> Tuple[int, Dict[str, int], Dict[str, str], List[str], List[str]]:
    # Risk Prioritization (0-25)
    risk_prior, rp_achieved, rp_max, rp_details = risk_prioritization_score()

    # Experiment Fit (0-25): proportion of COMPLETED tests whose type matches assumption type
    total_results = 0
    good_results = 0
    for rnd in (1, 2, 3):
        for r in st.session_state.results[rnd]:
            total_results += 1
            if r["assumption_type"] in EXPERIMENTS[r["experiment"]]["fit"]:
                good_results += 1
    exp_fit = int(25 * (good_results / total_results)) if total_results else 0

    # Resource Efficiency (0-25)
    eff, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak = resource_efficiency()

    # Learning Outcome (0-15): strong=2, weak=1 (cap 15)
    learn = min(15, learning_points)

    # Assumption Quality (0-10): diversity among top 5
    ranked_ids = [a["id"] for a in st.session_state.ranked]
    diversity = len(set(get_assumption(aid)["type"] for aid in ranked_ids[:5]))
    qual = 6 + (4 if diversity >= 2 else 0)

    total_score = min(100, risk_prior + exp_fit + eff + learn + qual)

    # Reasons (aligned one-to-one with categories)
    reasons = {
        "Assumption Quality": f"Top 5 include {diversity} distinct risk types.",
        "Risk Prioritization": (
            f"Full-order match score: {rp_achieved:.1f}/{rp_max:.1f} "
            f"(exact={rp_details['exact_matches']}, +/-1={rp_details['within_one']}, +/-2={rp_details['within_two']})."
        ),
        "Experiment Fit": f"{good_results}/{total_results} completed tests matched assumption type (fit-aligned).",
        "Resource Efficiency": (
            f"CPLP target={TARGET_CPLP:.2f}, actual={actual_cplp:.2f} = efficiency {efficiency_pct:.0f}% "
            f"(maps to 0-25)."
        ),
        "Learning Outcome": f"Signals: strong={strong} (x2), weak={weak} (x1) = {learning_points} pts "
                            f"(target={TARGET_LEARNING_POINTS}).",
    }

    # For details table, show top 3 user picks and ground-truth top 3 (by text)
    truth_sorted = sorted(st.session_state.ground_truth.items(), key=lambda kv: (-kv[1], kv[0]))
    true_top3 = [aid for aid, _ in truth_sorted[:3]]
    user_top3 = ranked_ids[:3]

    breakdown = {
        "Assumption Quality": qual,       # /10
        "Risk Prioritization": risk_prior, # /25
        "Experiment Fit": exp_fit,         # /25
        "Resource Efficiency": eff,        # /25
        "Learning Outcome": learn,         # /15
    }

    return total_score, breakdown, reasons, true_top3, user_top3


# --------------------------------------------------------------------------------------
# Personalized coaching engine
# --------------------------------------------------------------------------------------
def generate_personalized_coaching(breakdown, total_score):
    """Generate coaching notes that reference the player's actual choices and patterns."""
    notes = []
    idea = IDEAS.get(st.session_state.idea_key, {})
    idea_title = idea.get("title", "your idea")

    # ---- Analyze spending pattern across rounds ----
    round_costs = {}
    for rnd in (1, 2, 3):
        round_costs[rnd] = sum(r["cost"] for r in st.session_state.results[rnd])
    total_spent = sum(round_costs.values())

    if round_costs.get(1, 0) > 0.6 * total_spent and total_spent > 0:
        notes.append(
            f"**Spending pattern:** You allocated {round_costs[1]} of your {total_spent} tokens in Round 1. "
            f"Front-loading can be risky because early results should inform what you test next. "
            f"Consider reserving at least 40% of your budget for Rounds 2 and 3, where you can adapt based on what you have learned."
        )
    elif round_costs.get(3, 0) > 0.5 * total_spent and total_spent > 0:
        notes.append(
            f"**Spending pattern:** You saved most of your budget for Round 3 ({round_costs[3]} of {total_spent} tokens). "
            f"Patience can be strategic, but under-testing early means you had less signal to guide your later experiments. "
            f"A more balanced split (like 40/30/30) often produces better compounding learning."
        )

    # ---- Analyze experiment type diversity ----
    all_exp_types = [r["experiment"] for rnd in (1, 2, 3) for r in st.session_state.results[rnd]]
    unique_types = set(all_exp_types)
    if len(unique_types) == 1 and len(all_exp_types) > 1:
        exp_name = EXPERIMENTS[all_exp_types[0]]["label"]
        notes.append(
            f"**Experiment variety:** You only used one type of experiment ({exp_name}) across all rounds. "
            f"Different experiments reveal different things. A landing page tells you about demand, "
            f"a concierge trial reveals feasibility issues, and a pre-order tests willingness to pay. "
            f"Mixing experiment types gives you a more complete picture."
        )
    elif len(unique_types) >= 4:
        notes.append(
            f"**Experiment variety:** You used {len(unique_types)} different experiment types. "
            f"That diversity means you are looking at {idea_title} from multiple angles, which is exactly "
            f"what strong founders do. You are building a multi-dimensional view of your riskiest assumptions."
        )

    # ---- Analyze fit between experiments and assumptions ----
    misfit_examples = []
    good_fit_examples = []
    for rnd in (1, 2, 3):
        for r in st.session_state.results[rnd]:
            a = get_assumption(r["aid"])
            e = EXPERIMENTS[r["experiment"]]
            if a["type"] not in e["fit"]:
                misfit_examples.append((r["aid"], a["type"], e["label"]))
            elif r["signal"] == "strong":
                good_fit_examples.append((r["aid"], a["type"], e["label"]))

    if misfit_examples and len(misfit_examples) >= 2:
        ex = misfit_examples[0]
        notes.append(
            f"**Test-to-assumption fit:** Several of your experiments were mismatched. For example, "
            f"you used a {ex[2]} to test {ex[0]}, which is a {ex[1]} assumption. "
            f"That experiment is better suited for {'demand or pricing' if ex[1] == 'feasibility' else 'workflow or technical' if ex[1] == 'viability' else 'unit economics or pricing'} questions. "
            f"When the test type matches the assumption type, you get clearer, more actionable signals."
        )
    elif good_fit_examples and not misfit_examples:
        ex = good_fit_examples[0]
        notes.append(
            f"**Test-to-assumption fit:** Every experiment you chose was well-matched to its assumption. "
            f"For example, using a {ex[2]} for {ex[0]} (a {ex[1]} question) was a smart pairing. "
            f"This precision is why you got strong signals. You tested the right things with the right tools."
        )

    # ---- Analyze what they learned (or didn't) ----
    strong_results = [r for rnd in (1, 2, 3) for r in st.session_state.results[rnd] if r["signal"] == "strong"]
    no_signal = [r for rnd in (1, 2, 3) for r in st.session_state.results[rnd] if r["signal"] == "no-signal"]

    if strong_results:
        validated_types = set(r["assumption_type"] for r in strong_results)
        missing_types = {"desirability", "feasibility", "viability"} - validated_types
        if missing_types:
            missing_str = " and ".join(t for t in sorted(missing_types))
            notes.append(
                f"**Learning gaps:** You got strong signals on {', '.join(sorted(validated_types))}, "
                f"but you still have no strong evidence on {missing_str}. "
                f"An investor would notice that gap. Before your next pitch, design experiments that specifically target {missing_str}."
            )

    if len(no_signal) >= 3:
        wasted_tokens = sum(r["cost"] for r in no_signal)
        notes.append(
            f"**Failed experiments:** {len(no_signal)} of your experiments produced no usable signal, "
            f"costing {wasted_tokens} tokens. That is not necessarily bad. Failed experiments teach you something too. "
            f"But if a test fails, ask: was the hypothesis wrong, or was the experiment design flawed? "
            f"That distinction matters for your next round."
        )

    # ---- Risk ranking feedback ----
    if breakdown["Risk Prioritization"] >= 20:
        notes.append(
            f"**Risk instincts:** Your risk ranking was excellent. You correctly identified which assumptions "
            f"for {idea_title} carry the most uncertainty. This skill, knowing what to test first, is one of "
            f"the hardest things for new founders to develop. You are ahead of the curve."
        )
    elif breakdown["Risk Prioritization"] < 12:
        truth_sorted = sorted(st.session_state.ground_truth.items(), key=lambda kv: (-kv[1], kv[0]))
        true_top = truth_sorted[0]
        true_top_a = get_assumption(true_top[0])
        notes.append(
            f"**Risk instincts:** Your risk ranking diverged from the ground truth. The riskiest assumption "
            f"for {idea_title} was actually {true_top_a['id']} ('{true_top_a['text']}'). "
            f"A common mistake is ranking technical risks highest when the real danger is often demand or pricing. "
            f"Try asking: 'If this assumption is wrong, does the whole idea fall apart?' The ones where the answer is yes should be at the top."
        )

    # ---- Unspent tokens ----
    remaining = pool_remaining()
    if remaining >= 8:
        notes.append(
            f"**Unspent budget:** You left {remaining} tokens on the table. In a real startup, "
            f"unspent experiment budget is wasted runway. Every token you do not use is a question you did not ask. "
            f"Even late-stage experiments that refine your understanding are worth running."
        )

    # ---- Overall performance tier ----
    if total_score >= 80:
        notes.append(
            f"**Overall:** Scoring {total_score}/100 puts you in strong territory. You demonstrated the core skill "
            f"of early-stage founders: making smart bets with limited resources. "
            f"The way you sequenced experiments across rounds shows strategic thinking that most first-time founders lack."
        )
    elif total_score >= 55:
        notes.append(
            f"**Overall:** At {total_score}/100, you showed solid instincts with room to sharpen. "
            f"The foundations are there. Focus on matching your experiment types more precisely to your assumptions, "
            f"and do not be afraid to run cheap, fast tests in early rounds before committing to expensive ones."
        )
    else:
        notes.append(
            f"**Overall:** At {total_score}/100, there is significant room to grow, and that is exactly why simulations like this exist. "
            f"The biggest opportunity: slow down on experiment selection and ask, 'What specific question does this test answer?' "
            f"If you cannot articulate the question clearly, the experiment will not give you a clear answer either."
        )

    # Fallback
    if not notes:
        notes.append("Strong performance across the board. Your sequencing, fit, and budget management are well-balanced.")

    return notes


def get_percentile_estimate(total_score: int) -> Tuple[int, str]:
    """Estimate a percentile based on simulated peer distribution.
    Returns (percentile, descriptor)."""
    # Simulated distribution of scores (based on reasonable assumptions about student performance)
    if total_score >= 85:
        return 95, "Top 5%"
    elif total_score >= 75:
        return 85, "Top 15%"
    elif total_score >= 65:
        return 70, "Top 30%"
    elif total_score >= 55:
        return 50, "Middle of the pack"
    elif total_score >= 40:
        return 30, "Below average"
    else:
        return 15, "Bottom quartile"


def get_letter_grade(total_score: int) -> Tuple[str, str]:
    """Return letter grade and a short label."""
    if total_score >= 90:
        return "A", "Exceptional"
    elif total_score >= 80:
        return "A-", "Strong"
    elif total_score >= 70:
        return "B+", "Above Average"
    elif total_score >= 60:
        return "B", "Solid"
    elif total_score >= 50:
        return "B-", "Developing"
    elif total_score >= 40:
        return "C+", "Needs Work"
    else:
        return "C", "Keep Practicing"


# --------------------------------------------------------------------------------------
# UI Screens
# --------------------------------------------------------------------------------------
def screen_intro():
    stepper()

    hero_html = '''
    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 3rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 2rem;">
        <h1 style="margin: 0 0 0.5rem 0; font-size: 2.5rem;">Designing & Running Early Experiments</h1>
        <p style="margin: 0; font-size: 1.2rem; opacity: 0.95;">Simulation #2: ThermaLoop</p>
    </div>
    '''
    st.markdown(hero_html, unsafe_allow_html=True)

    st.markdown(
        "You just joined a founding team. The idea is called **ThermaLoop**: a technology that optimizes "
        "HVAC systems to save energy and improve comfort. But there is a problem. The team has three "
        "possible directions they could take this, and limited time and money to figure out which one "
        "is worth building."
    )
    st.markdown(
        "Your job: **be the founder who figures out what to test, and how to test it, before the money runs out.**"
    )

    st.markdown("### What You'll Do")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("🎯 **Choose a direction** for ThermaLoop (each one targets a different customer and market)")
        st.markdown("📊 **Rank your riskiest assumptions** because testing the wrong thing first wastes everything")
    with col2:
        st.markdown("🧪 **Design and run experiments** across three rounds, spending your 30-token budget wisely")
        st.markdown("📈 **Read your results like a founder** and decide what to test next based on what you learn")

    st.info(
        "**You have 30 tokens. That is your entire experiment budget.** "
        "Spend them across 3 rounds. Within a round, tests run in parallel (round time = the longest test). "
        "You cannot get more tokens. Choose wisely."
    )

    st.markdown('<div style="height: 1px; background: #e5e7eb; margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("I'm Ready. Let's Go.", type="primary", on_click=lambda: next_stage("choose"), use_container_width=True)
    st.caption("Takes about 15 minutes. There are no right answers, only strategic tradeoffs.")

    footer_html = '<div style="text-align: center; color: #888; font-size: 13px; margin-top: 2rem;">Brought to you by LaunchX</div>'
    st.markdown(footer_html, unsafe_allow_html=True)


def screen_choose():
    stepper()

    st.subheader("Choose Your Direction")
    st.markdown(
        "The ThermaLoop team has identified three possible products. Each one targets a different customer, "
        "solves a different version of the problem, and carries its own risks. **There is no 'right' choice.** "
        "What matters is what you do after you choose."
    )

    cols = st.columns(3)

    def idea_card(key: str, col):
        idea = IDEAS[key]
        with col:
            st.markdown(f"### {idea['title']}")
            st.markdown(f"*{idea['one_liner']}*")
            st.markdown(f"**Target customer:** {idea['customer']}")
            st.markdown(f"**Why this is exciting:** {idea['why_exciting']}")
            with st.expander(f"Preview assumptions ({len(idea['assumptions'])})", expanded=False):
                for a in idea["assumptions"]:
                    st.markdown(f"- {a['text']} _({a['type']})_")
            st.button(
                f"Build {idea['title']}",
                key=f"pick_{key}",
                on_click=lambda k=key: set_idea(k),
                type="primary",
                use_container_width=True,
            )

    idea_card("home_comfort", cols[0])
    idea_card("landlord_energy", cols[1])
    idea_card("installer_tools", cols[2])

    footer_html = '<div style="text-align: center; color: #888; font-size: 13px; margin-top: 2rem;">Brought to you by LaunchX</div>'
    st.markdown(footer_html, unsafe_allow_html=True)


def screen_rank():
    stepper()
    idea = IDEAS.get(st.session_state.idea_key, {})
    st.subheader(f"Rank Your Assumptions: {idea.get('title', '')}")

    st.markdown(
        f"Here are the key assumptions behind **{idea.get('title', 'your idea')}**. "
        f"Your job: drag them into order from **riskiest at the top** to **least risky at the bottom**."
    )
    st.caption(
        "Think about it this way: if this assumption turns out to be wrong, does the whole idea collapse? "
        "Those go at the top. Assumptions that are uncertain but survivable go lower."
    )

    items = st.session_state.ranked
    for i, a in enumerate(items):
        cols = st.columns([0.06, 0.06, 0.88])
        with cols[0]:
            st.button("▲", key=f"up_{i}", on_click=lambda idx=i: move_item(idx, -1))
        with cols[1]:
            st.button("▼", key=f"dn_{i}", on_click=lambda idx=i: move_item(idx, +1))
        with cols[2]:
            to_badge(a["type"], "#3a7")
            st.markdown(f"**{a['id']}**: {a['text']}")

    st.divider()
    st.button(
        "Lock My Rankings. Start Round 1.",
        type="primary",
        on_click=lambda: next_stage("r1_select"),
    )

    footer_html = '<div style="text-align: center; color: #888; font-size: 13px; margin-top: 2rem;">Brought to you by LaunchX</div>'
    st.markdown(footer_html, unsafe_allow_html=True)


def screen_round_select(round_idx: int):
    stepper()
    idea = IDEAS.get(st.session_state.idea_key, {})
    st.subheader(f"Round {round_idx}: Design Your Experiments")

    # Round-specific context
    if round_idx == 1:
        st.markdown(
            "This is your first round. You know nothing yet. Pick experiments that will "
            "give you the clearest signal on your riskiest assumptions. Remember: within a round, "
            "tests run in parallel, so scheduling multiple tests only costs you the time of the longest one."
        )
    elif round_idx == 2:
        # Summarize what they learned in round 1
        r1_results = st.session_state.results.get(1, [])
        strong_r1 = [r for r in r1_results if r["signal"] == "strong"]
        if strong_r1:
            validated_ids = [r["aid"] for r in strong_r1]
            st.markdown(
                f"Round 1 gave you strong signals on **{', '.join(validated_ids)}**. "
                f"Now: what questions remain? Use Round 2 to fill in the gaps or double down on weak signals."
            )
        else:
            st.markdown(
                "Round 1 did not produce strong signals. That happens. Round 2 is your chance to "
                "try different experiment types or target different assumptions."
            )
    else:
        remaining = pool_remaining()
        st.markdown(
            f"Final round. You have **{remaining} tokens** left. "
            f"Make them count. What is the one question that, if answered, would change everything?"
        )

    st.caption("Be intentional: keep tokens for later rounds.")

    # Tokens (pool)
    remaining = pool_remaining()
    to_badge(f"Total token budget (all rounds): {st.session_state.tokens_total}", "#295")
    st.write(" ")
    to_badge(f"Tokens left: {remaining} of {st.session_state.tokens_total}", "#295")

    # Show ranked list with selector of experiments
    ranked = st.session_state.ranked
    st.markdown("##### Assumptions (your order)")

    for a in ranked:
        with st.expander(f"{a['id']}: {a['text']}", expanded=False):
            st.caption(f"Type: **{a['type']}**")
            cols = st.columns(4)
            keys = list(EXPERIMENTS.keys())
            for i, ek in enumerate(keys):
                card = EXPERIMENTS[ek]
                with cols[i % 4]:
                    st.markdown(
                        f"**{card['label']}** \n_{card['desc']}_ \nCost: **{card['cost']}**, Duration: **{card['days']}d**"
                    )
                    # Check if this exact test is already scheduled for this assumption in this round
                    already_scheduled = any(
                        aid == a["id"] and ekey == ek
                        for aid, ekey in st.session_state.portfolio[round_idx]
                    )
                    if already_scheduled:
                        st.success("Added")
                    else:
                        if st.button(f"Add to {a['id']}", key=f"add_{round_idx}_{a['id']}_{ek}"):
                            # enforce strict 30-token cap including scheduled-but-not-run tests
                            if planned_spend() + card["cost"] <= st.session_state.tokens_total:
                                st.session_state.portfolio[round_idx].append((a["id"], ek))
                                st.rerun()
                            else:
                                st.warning("Not enough total tokens remaining.")

    st.divider()
    scheduled = st.session_state.portfolio[round_idx]

    if scheduled:
        st.markdown("#### Scheduled this round")
        round_cost = sum(EXPERIMENTS[ek]["cost"] for (_, ek) in scheduled)
        round_time = max(EXPERIMENTS[ek]["days"] for (_, ek) in scheduled) if scheduled else 0
        st.caption(f"Round cost: {round_cost} tokens | Round duration: {round_time} days (parallel)")
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
                if st.button("Remove", key=f"rm_{round_idx}_{idx}"):
                    st.session_state.portfolio[round_idx].pop(idx)
                    st.rerun()
    else:
        st.info("No tests scheduled yet. Expand an assumption above and add experiments.")

    can_run = len(scheduled) > 0
    if can_run:
        st.button(
            f"Run Round {round_idx}",
            type="primary",
            on_click=lambda r=round_idx: (run_round(r), next_stage(f"r{r}_results")),
        )
    else:
        st.button(f"Run Round {round_idx}", disabled=True)

    footer_html = '<div style="text-align: center; color: #888; font-size: 13px; margin-top: 2rem;">Brought to you by LaunchX</div>'
    st.markdown(footer_html, unsafe_allow_html=True)


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
        rows.append({
            "Assumption Type": t.title(),
            "Validated": validated,
            "Total": total,
            "Completion %": round(pct, 1),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def screen_round_results(round_idx: int):
    stepper()
    idea = IDEAS.get(st.session_state.idea_key, {})
    st.subheader(f"Round {round_idx} Results: {idea.get('title', '')}")

    res = st.session_state.results[round_idx]
    if not res:
        st.warning("No results recorded. Go back and schedule tests.")
        return

    # Compute round stats for the header
    round_cost = sum(r["cost"] for r in res)
    round_time = max(r["days"] for r in res) if res else 0
    strong_count = sum(1 for r in res if r["signal"] == "strong")
    weak_count = sum(1 for r in res if r["signal"] == "weak")
    no_signal_count = sum(1 for r in res if r["signal"] == "no-signal")

    # Round summary header
    summary_html = f'''
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1.25rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div><span style="font-size: 1.5rem; font-weight: bold;">{len(res)}</span><br><span style="color: #64748b; font-size: 0.85rem;">Experiments Run</span></div>
            <div><span style="font-size: 1.5rem; font-weight: bold;">{round_cost}</span><br><span style="color: #64748b; font-size: 0.85rem;">Tokens Spent</span></div>
            <div><span style="font-size: 1.5rem; font-weight: bold;">{round_time}d</span><br><span style="color: #64748b; font-size: 0.85rem;">Elapsed Time</span></div>
            <div><span style="font-size: 1.5rem; font-weight: bold; color: #16a34a;">{strong_count}</span><br><span style="color: #64748b; font-size: 0.85rem;">Strong Signals</span></div>
            <div><span style="font-size: 1.5rem; font-weight: bold; color: #d97706;">{weak_count}</span><br><span style="color: #64748b; font-size: 0.85rem;">Weak Signals</span></div>
            <div><span style="font-size: 1.5rem; font-weight: bold; color: #dc2626;">{no_signal_count}</span><br><span style="color: #64748b; font-size: 0.85rem;">No Signal</span></div>
        </div>
    </div>
    '''
    st.markdown(summary_html, unsafe_allow_html=True)

    # Show each result card with NARRATIVE
    for r in res:
        a = get_assumption(r["aid"])
        e = EXPERIMENTS[r["experiment"]]

        if r["signal"] == "strong":
            border_color = "#16a34a"
            signal_label = "Strong Signal"
            signal_icon = "✅"
        elif r["signal"] == "weak":
            border_color = "#d97706"
            signal_label = "Weak Signal"
            signal_icon = "🟡"
        else:
            border_color = "#dc2626"
            signal_label = "No Signal"
            signal_icon = "❌"

        box = st.container(border=True)
        with box:
            # Header with assumption + signal badge
            header_html = f'''
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <div><strong>{a['id']}</strong>: {a['text']}</div>
                <span style="padding: 4px 12px; border-radius: 20px; background: {border_color}; color: white; font-size: 0.8rem; white-space: nowrap;">{signal_icon} {signal_label}</span>
            </div>
            '''
            st.markdown(header_html, unsafe_allow_html=True)
            st.caption(f"{e['label']} | Cost: {r['cost']} tokens | Duration: {r['days']} days")

            # The narrative: the heart of the upgrade
            st.markdown(r["narrative"])

    # Cumulative validation progress (table)
    st.divider()
    st.markdown("#### Where You Stand Now")
    st.caption("Cumulative validation across all rounds so far.")
    show_validation_table()

    # Remaining budget reminder
    remaining = pool_remaining()
    if round_idx < 3:
        st.info(f"You have **{remaining} tokens** remaining for {'2 more rounds' if round_idx == 1 else '1 more round'}.")

    st.divider()
    if round_idx < 3:
        st.button(
            f"On to Round {round_idx + 1}",
            type="primary",
            on_click=lambda r=round_idx + 1: next_stage(f"r{r}_select"),
        )
    else:
        st.button(
            "See My Results",
            type="primary",
            on_click=lambda: next_stage("score"),
        )

    footer_html = '<div style="text-align: center; color: #888; font-size: 13px; margin-top: 2rem;">Brought to you by LaunchX</div>'
    st.markdown(footer_html, unsafe_allow_html=True)


# --------------------------------------------------------------------------------------
# Scoring & Feedback screen
# --------------------------------------------------------------------------------------
def screen_score():
    stepper()
    idea = IDEAS.get(st.session_state.idea_key, {})

    total, breakdown, reasons, true_top3, user_top3 = compute_score()
    letter, label = get_letter_grade(total)
    percentile, percentile_desc = get_percentile_estimate(total)

    # Hero score card
    score_color = "#16a34a" if total >= 70 else "#d97706" if total >= 50 else "#dc2626"
    score_html = f'''
    <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); padding: 2.5rem; border-radius: 12px; color: white; text-align: center; margin-bottom: 2rem;">
        <p style="margin: 0; font-size: 1rem; opacity: 0.8;">Your Founder Readiness Score</p>
        <h1 style="margin: 0.5rem 0; font-size: 4rem; color: {score_color};">{total}<span style="font-size: 1.5rem; opacity: 0.6;">/100</span></h1>
        <p style="margin: 0; font-size: 1.4rem;">{letter}: {label}</p>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.95rem; opacity: 0.7;">{percentile_desc} of simulation players</p>
    </div>
    '''
    st.markdown(score_html, unsafe_allow_html=True)

    # Category breakdown
    st.markdown("#### Score Breakdown")
    ordered = [
        "Assumption Quality",
        "Risk Prioritization",
        "Experiment Fit",
        "Resource Efficiency",
        "Learning Outcome",
    ]
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
        rows.append({
            "Category": cat,
            "Score (/100)": out100,
            "Why you scored this way": reasons.get(cat, ""),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # Risk Prioritization Details
    st.markdown("#### Risk Prioritization: Your Ranking vs. Reality")
    def ids_to_texts(ids):
        out = []
        for aid in ids:
            a = get_assumption(aid)
            out.append(f"{aid}: {a['text']}")
        return out

    col_you, col_truth = st.columns(2)
    with col_you:
        st.markdown("**Your Top 3 (riskiest)**")
        for line in ids_to_texts(user_top3):
            st.write(f"- {line}")
    with col_truth:
        st.markdown("**Actual Top 3 (ground truth)**")
        for line in ids_to_texts(true_top3):
            st.write(f"- {line}")

    overlap = len(set(user_top3) & set(true_top3))
    if overlap == 3:
        st.success("You nailed it. All three of your top picks matched the ground truth.")
    elif overlap >= 1:
        st.info(f"You got {overlap} of 3 right. Close, but the ranking order matters too.")
    else:
        st.warning("None of your top 3 matched the ground truth. This is the hardest skill to develop, keep practicing.")

    # Cumulative time & money summary + learning points and CPLP
    eff_score, total_cost, total_time, learning_points, actual_cplp, efficiency_pct, strong, weak = resource_efficiency()

    st.markdown("#### Your Experiment Portfolio")
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    with metrics_col1:
        st.metric("Tokens Spent", f"{st.session_state.tokens_spent}/{st.session_state.tokens_total}")
    with metrics_col2:
        st.metric("Elapsed Time", f"{total_time} days")
    with metrics_col3:
        st.metric("Learning Points", f"{learning_points}")
    with metrics_col4:
        if actual_cplp != float('inf'):
            st.metric("Cost per Learning Point", f"{actual_cplp:.1f}")
        else:
            st.metric("Cost per Learning Point", "N/A")

    # Personalized coaching
    st.divider()
    st.markdown("#### Your Personalized Coaching")
    st.caption("These notes are based on your specific choices, not generic advice.")

    coaching_notes = generate_personalized_coaching(breakdown, total)
    for note in coaching_notes:
        st.markdown(f"- {note}")

    # Peer benchmarks
    st.divider()
    st.markdown("#### How You Compare")
    peer_html = f'''
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 1.5rem; margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-around; text-align: center;">
            <div>
                <span style="font-size: 0.85rem; color: #64748b;">Average Score</span><br>
                <span style="font-size: 1.3rem; font-weight: bold;">58</span>
            </div>
            <div>
                <span style="font-size: 0.85rem; color: #64748b;">Your Score</span><br>
                <span style="font-size: 1.3rem; font-weight: bold; color: {score_color};">{total}</span>
            </div>
            <div>
                <span style="font-size: 0.85rem; color: #64748b;">Top Performers</span><br>
                <span style="font-size: 1.3rem; font-weight: bold;">82+</span>
            </div>
        </div>
        <div style="margin-top: 1rem; text-align: center; color: #64748b; font-size: 0.85rem;">
            Most students overspend in Round 1 and undertest feasibility assumptions. Top performers balance their budget across all 3 rounds and match experiment types precisely to assumption categories.
        </div>
    </div>
    '''
    st.markdown(peer_html, unsafe_allow_html=True)

    st.markdown('<div style="height: 1px; background: #e5e7eb; margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    # CTA
    st.markdown("### What's Next?")
    cta_card = f'''
    <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 2rem; border-radius: 12px; text-align: center;">
        <h3 style="margin-top: 0;">You just practiced the hardest part of being a founder.</h3>
        <p style="margin: 1rem 0; font-size: 1.05rem;">
            Knowing what to test, how to test it, and how to read the results is what separates founders who
            learn fast from those who burn through their runway guessing. LaunchX programs are built around
            exactly these skills.
        </p>
        <a href="https://launchx.com/programs" target="_blank" style="display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: white; color: #6366f1; text-decoration: none; border-radius: 6px; font-weight: bold;">Explore LaunchX Programs</a>
    </div>
    '''
    st.markdown(cta_card, unsafe_allow_html=True)

    st.markdown('<div style="height: 1px; background: #e5e7eb; margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("Play Again", on_click=lambda: next_stage("intro"), use_container_width=True)

    footer_html = '<div style="text-align: center; color: #888; font-size: 13px; margin-top: 2rem;">Brought to you by LaunchX</div>'
    st.markdown(footer_html, unsafe_allow_html=True)


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
