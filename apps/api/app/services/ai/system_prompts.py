"""
Seed definitions for the system prompt templates every organization gets.

These are deliberately generic scaffolds: the Research / Email Generation /
Reply Analysis / Meeting modules will refine the actual prompt content by
creating new PromptVersions when they are implemented. This module only
guarantees that a working (template, active version) pair exists per agent
type so AIJobService never 404s on "no active prompt version".

Seeded at organization creation (alongside DEFAULT_ROLE_PERMISSIONS) and
lazily backfilled for pre-existing organizations the first time a template
is resolved — see PromptService.ensure_system_templates.
"""

from app.models.enums import AIAgentTypeEnum

# name -> (agent_type, description, system_prompt, user_prompt_template, variables)
SYSTEM_PROMPT_TEMPLATES: dict[str, tuple[AIAgentTypeEnum, str, str, str, list[str]]] = {
    "research_company": (
        AIAgentTypeEnum.RESEARCH,
        "Researches a company and produces a structured sales-intelligence profile.",
        "You are a B2B sales research analyst. You produce accurate, concise, "
        "structured research about companies. Respond with valid JSON only — no "
        "markdown fences, no commentary.",
        "Research the company '{{ company_name }}'.\n\n"
        "Known context:\n{{ context }}\n\n"
        "Return a JSON object with keys: summary, products_services, "
        "target_customers, business_model, technologies, competitors, "
        "recent_news, pain_points, sales_opportunities, estimated_revenue, "
        "funding_stage, growth_signals.",
        ["company_name", "context"],
    ),
    "analyze_prospect": (
        AIAgentTypeEnum.PROSPECT_ANALYSIS,
        "Analyzes a lead as a sales prospect: buying intent, objections, and recommended approach.",
        "You are a B2B sales strategist. You analyze individual prospects to help "
        "reps prioritize outreach and tailor their pitch. Respond with valid JSON only — "
        "no markdown fences, no commentary.",
        "Analyze {{ lead_first_name }} ({{ lead_job_title }}) at {{ lead_company_name }} "
        "as a sales prospect.\n\n"
        "Company research summary:\n{{ company_research_summary }}\n\n"
        "Return a JSON object with keys: buying_intent (one of: high, medium, low), "
        "priority_score (a number 0-100), recommended_approach, value_proposition, "
        "predicted_objections (array of strings), likely_goals (array of strings), "
        "decision_authority (one of: decision_maker, influencer, evaluator, end_user), "
        "best_contact_time.",
        ["lead_first_name", "lead_job_title", "lead_company_name", "company_research_summary"],
    ),
    "generate_email": (
        AIAgentTypeEnum.EMAIL_GENERATION,
        "Writes a personalized outreach email for a lead.",
        "You are an expert sales development representative. You write short, "
        "specific, personalized outreach emails. Never use generic filler like "
        "'I hope this email finds you well'. Respond with valid JSON only.",
        "Write {{ variant_count }} email variant(s) for {{ lead_first_name }} "
        "({{ lead_job_title }}) at {{ company_name }}.\n\n"
        "Context:\n{{ context }}\n\n"
        "Tone: {{ tone }}.\n"
        "Return a JSON array of objects with keys: subject, body_html, body_text, reasoning.",
        ["lead_first_name", "lead_job_title", "company_name", "context", "tone", "variant_count"],
    ),
    "classify_reply": (
        AIAgentTypeEnum.REPLY_ANALYSIS,
        "Classifies an inbound prospect reply by intent.",
        "You are a sales reply classifier. Classify the intent of inbound "
        "replies precisely. Respond with valid JSON only.",
        "Classify this reply from {{ lead_first_name }} (original subject: "
        "'{{ original_subject }}'):\n\n{{ reply_body }}\n\n"
        "Return a JSON object with keys: classification (one of: interested, "
        "not_interested, meeting_requested, needs_follow_up, referral, "
        "out_of_office, spam, unsubscribe_request, unknown), confidence "
        "(0.0-1.0), suggested_action (short actionable text).",
        ["lead_first_name", "original_subject", "reply_body"],
    ),
    "detect_meeting": (
        AIAgentTypeEnum.MEETING,
        "Extracts meeting intent and proposed times from a prospect message.",
        "You are a scheduling assistant. Extract meeting intent and any "
        "concrete time/date mentions from messages. Respond with valid JSON only.",
        "Extract meeting details from this message:\n\n{{ message_body }}\n\n"
        "Return a JSON object with keys: wants_meeting (boolean), "
        "proposed_times (array of ISO-8601 strings or natural-language "
        "phrases), duration_minutes (number or null), notes (string).",
        ["message_body"],
    ),
}
