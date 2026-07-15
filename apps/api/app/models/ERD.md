# SalesPilot AI — Entity Relationship Diagram

```mermaid
erDiagram

    %% ─── IDENTITY ───────────────────────────────────────────────────────────

    Organization {
        uuid id PK
        string name
        string slug UK
        string domain
        string timezone
        boolean is_active
        jsonb metadata
        datetime created_at
        datetime deleted_at
    }

    Team {
        uuid id PK
        uuid organization_id FK
        string name
        boolean is_active
    }

    User {
        uuid id PK
        uuid organization_id FK
        string email UK
        boolean email_verified
        string first_name
        string last_name
        string password_hash
        string status
        string google_id UK
        jsonb preferences
        datetime last_login_at
    }

    Role {
        uuid id PK
        uuid organization_id FK
        string name
        boolean is_system
    }

    Permission {
        uuid id PK
        string resource
        string action
    }

    UserRole {
        uuid user_id FK
        uuid role_id FK
        uuid organization_id FK
        datetime assigned_at
    }

    RolePermission {
        uuid role_id FK
        uuid permission_id FK
    }

    TeamMember {
        uuid team_id FK
        uuid user_id FK
        boolean is_team_lead
    }

    Session {
        uuid id PK
        uuid user_id FK
        uuid organization_id FK
        boolean is_active
        datetime expires_at
    }

    RefreshToken {
        uuid id PK
        uuid user_id FK
        string token_hash UK
        datetime expires_at
        datetime revoked_at
    }

    %% ─── CRM ────────────────────────────────────────────────────────────────

    Company {
        uuid id PK
        uuid organization_id FK
        string name
        string website
        string domain UK
        string industry
        string country
        integer employee_count
        array technologies
        jsonb metadata
    }

    Contact {
        uuid id PK
        uuid organization_id FK
        uuid company_id FK
        string first_name
        string last_name
        string email
        string job_title
        string linkedin_url
        boolean is_decision_maker
    }

    Lead {
        uuid id PK
        uuid organization_id FK
        uuid contact_id FK
        uuid company_id FK
        uuid owner_id FK
        string status
        string source
        integer priority
        string email
        float icp_match_score
        float buying_intent_score
        jsonb custom_fields
        datetime contacted_at
        datetime converted_at
    }

    LeadScore {
        uuid id PK
        uuid lead_id FK
        float overall_score
        float icp_score
        float buying_intent_score
        string reasoning
        datetime scored_at
    }

    Tag {
        uuid id PK
        uuid organization_id FK
        string name
        string color
    }

    LeadTag {
        uuid lead_id FK
        uuid tag_id FK
        datetime tagged_at
    }

    Note {
        uuid id PK
        uuid lead_id FK
        uuid author_id FK
        text content
        boolean is_pinned
    }

    Activity {
        uuid id PK
        uuid lead_id FK
        uuid actor_id FK
        string activity_type
        string summary
        string entity_type
        uuid entity_id
        datetime occurred_at
    }

    Attachment {
        uuid id PK
        uuid lead_id FK
        string filename
        string file_key
        string mime_type
    }

    %% ─── CAMPAIGNS ──────────────────────────────────────────────────────────

    Campaign {
        uuid id PK
        uuid organization_id FK
        uuid owner_id FK
        string name
        string status
        string goal
        integer daily_send_limit
        string timezone
    }

    Sequence {
        uuid id PK
        uuid campaign_id FK
        string name
        boolean is_active
    }

    SequenceStep {
        uuid id PK
        uuid sequence_id FK
        uuid email_template_id FK
        string step_type
        integer step_order
        integer delay_days
        jsonb condition
    }

    EmailTemplate {
        uuid id PK
        uuid organization_id FK
        string name
        string template_type
        string tone
        string subject
        text body_html
        text ai_reasoning
        boolean is_ai_generated
        integer total_sent
        integer total_opened
        integer total_replied
    }

    CampaignLead {
        uuid id PK
        uuid campaign_id FK
        uuid lead_id FK
        uuid sequence_id FK
        string status
        integer current_step_order
        uuid next_step_id FK
        datetime next_action_at
    }

    %% ─── COMMUNICATION ──────────────────────────────────────────────────────

    Email {
        uuid id PK
        uuid organization_id FK
        uuid lead_id FK
        uuid campaign_lead_id FK
        uuid sequence_step_id FK
        uuid conversation_id FK
        string from_email
        string to_email
        string subject
        text body_html
        string current_status
        string tracking_pixel_id UK
        boolean ai_generated
        datetime sent_at
    }

    EmailEvent {
        uuid id PK
        uuid email_id FK
        string event_type
        datetime occurred_at
        string provider
        string provider_event_id UK
        string ip_address
        string click_url
        string bounce_reason
    }

    Conversation {
        uuid id PK
        uuid lead_id FK
        string subject
        boolean is_active
        datetime last_message_at
        integer message_count
    }

    Message {
        uuid id PK
        uuid conversation_id FK
        uuid lead_id FK
        string from_email
        text body_text
        string reply_classification
        text ai_suggested_action
        datetime received_at
        boolean is_read
    }

    Meeting {
        uuid id PK
        uuid organization_id FK
        uuid lead_id FK
        uuid owner_id FK
        uuid calendar_event_id FK
        string title
        string status
        datetime scheduled_start
        datetime scheduled_end
        integer duration_minutes
    }

    CalendarEvent {
        uuid id PK
        string provider
        string provider_event_id UK
        datetime start_time
        datetime end_time
        string meet_link
        jsonb attendees
    }

    %% ─── AI ─────────────────────────────────────────────────────────────────

    AIAgent {
        uuid id PK
        uuid organization_id FK
        string name
        string agent_type
        string provider
        string model_name
        float temperature
        uuid prompt_template_id FK
    }

    AIJob {
        uuid id PK
        uuid organization_id FK
        uuid agent_id FK
        uuid parent_job_id FK
        string entity_type
        uuid entity_id
        string job_type
        string status
        integer input_tokens
        integer output_tokens
        float cost_usd
        integer latency_ms
    }

    AIOutput {
        uuid id PK
        uuid job_id FK
        string output_type
        text content_text
        jsonb content_json
        boolean is_approved
        float quality_score
    }

    CompanyResearch {
        uuid id PK
        uuid company_id UK FK
        uuid ai_job_id FK
        text summary
        jsonb products_services
        jsonb pain_points
        jsonb competitors
        jsonb recent_news
        datetime researched_at
    }

    ProspectAnalysis {
        uuid id PK
        uuid lead_id UK FK
        uuid ai_job_id FK
        string buying_intent
        float priority_score
        text recommended_approach
        jsonb predicted_objections
        datetime analysed_at
    }

    PromptTemplate {
        uuid id PK
        uuid organization_id FK
        string name
        string agent_type
        boolean is_system
        uuid active_version_id
    }

    PromptVersion {
        uuid id PK
        uuid template_id FK
        integer version_number
        text system_prompt
        text user_prompt_template
        string model_name
        float avg_quality_score
    }

    AIMemory {
        uuid id PK
        uuid organization_id FK
        string entity_type
        uuid entity_id
        string memory_type
        text content
        float importance_score
        string chroma_doc_id
    }

    %% ─── AUTOMATION ─────────────────────────────────────────────────────────

    Workflow {
        uuid id PK
        uuid organization_id FK
        string name
        string status
        string trigger_event
        jsonb trigger_conditions
        jsonb steps
    }

    WorkflowExecution {
        uuid id PK
        uuid workflow_id FK
        string status
        uuid trigger_entity_id
        datetime started_at
        datetime completed_at
    }

    ScheduledJob {
        uuid id PK
        uuid organization_id FK
        string name
        string job_type
        string cron_expression
        datetime next_run_at
    }

    %% ─── ANALYTICS ──────────────────────────────────────────────────────────

    Event {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string event_name
        string entity_type
        uuid entity_id
        jsonb properties
        datetime occurred_at
    }

    Metric {
        uuid id PK
        uuid organization_id FK
        uuid campaign_id FK
        string metric_name
        datetime metric_date
        string period
        float value
        jsonb dimensions
    }

    %% ─── ADMINISTRATION ─────────────────────────────────────────────────────

    Notification {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string notification_type
        string title
        boolean is_read
        datetime read_at
    }

    APIKey {
        uuid id PK
        uuid organization_id FK
        string name
        string key_prefix
        string key_hash UK
        jsonb scopes
        boolean is_active
    }

    Integration {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string integration_type
        string access_token_encrypted
        datetime token_expires_at
        datetime last_synced_at
    }

    AuditLog {
        uuid id PK
        uuid organization_id FK
        uuid actor_id FK
        string action
        string resource_type
        uuid resource_id
        jsonb changes
        datetime occurred_at
    }

    %% ─── BILLING ────────────────────────────────────────────────────────────

    Plan {
        uuid id PK
        string name UK
        string slug UK
        float price_monthly
        float price_annual
        jsonb features
        string stripe_price_id_monthly
    }

    Subscription {
        uuid id PK
        uuid organization_id FK
        uuid plan_id FK
        string status
        string interval
        string stripe_subscription_id UK
        datetime trial_ends_at
        datetime current_period_end
        integer seats
    }

    Invoice {
        uuid id PK
        uuid organization_id FK
        uuid subscription_id FK
        string status
        float amount_due
        float amount_paid
        datetime paid_at
    }

    Payment {
        uuid id PK
        uuid invoice_id FK
        float amount
        string status
        datetime paid_at
    }

    UsageRecord {
        uuid id PK
        uuid organization_id FK
        uuid subscription_id FK
        string metric_name
        integer quantity
        datetime period_start
        datetime period_end
    }

    %% ─── RELATIONSHIPS ───────────────────────────────────────────────────────

    Organization ||--o{ Team : "has"
    Organization ||--o{ User : "has"
    Organization ||--o{ Role : "has"
    Organization ||--o| Subscription : "has one"
    Organization ||--o{ APIKey : "has"
    Organization ||--o{ Integration : "has"
    Organization ||--o{ Campaign : "runs"
    Organization ||--o{ Company : "tracks"

    Team }o--o{ User : "TeamMember"
    User }o--o{ Role : "UserRole"
    Role }o--o{ Permission : "RolePermission"

    Company ||--o{ Contact : "employs"
    Company ||--o{ Lead : "sourced from"
    Company ||--o| CompanyResearch : "has research"

    Contact ||--o{ Lead : "becomes"
    Lead ||--o| ProspectAnalysis : "has analysis"
    Lead ||--o{ LeadScore : "scored by"
    Lead }o--o{ Tag : "LeadTag"
    Lead ||--o{ Note : "has"
    Lead ||--o{ Activity : "logs"
    Lead ||--o{ Attachment : "has"
    Lead ||--o{ CampaignLead : "enrolled in"
    Lead ||--o{ Email : "receives"
    Lead ||--o{ Meeting : "has"
    Lead ||--o{ Conversation : "has"

    Campaign ||--o{ Sequence : "uses"
    Campaign ||--o{ CampaignLead : "contains"
    Sequence ||--o{ SequenceStep : "has"
    SequenceStep }o--o| EmailTemplate : "uses"
    CampaignLead ||--o{ Email : "generates"

    Email ||--o{ EmailEvent : "has events"
    Conversation ||--o{ Message : "contains"
    Meeting ||--o| CalendarEvent : "linked to"

    AIAgent ||--o{ AIJob : "executes"
    AIJob ||--o{ AIOutput : "produces"
    AIJob }o--o{ AIJob : "child of"
    PromptTemplate ||--o{ PromptVersion : "versions"
    AIJob }o--o| PromptVersion : "used"

    Subscription ||--o{ Invoice : "generates"
    Subscription ||--o{ UsageRecord : "tracks"
    Invoice ||--o{ Payment : "paid by"
    Plan ||--o{ Subscription : "subscribed to"

    Workflow ||--o{ WorkflowExecution : "runs"
```
