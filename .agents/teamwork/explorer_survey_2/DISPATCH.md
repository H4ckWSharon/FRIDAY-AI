## Task Assignment: Survey Explorer 2 — Payment Plans, Pricing Structure & Active Subscriptions

### Working Directory
`c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_2\`

### Inputs
- `c:\Users\sharo\Desktop\friday\.agents\teamwork\ORIGINAL_REQUEST.md` (Read this first!)
- Project Root: `c:\Users\sharo\Desktop\friday`
- VPS Host: `213.133.97.141` (SSH: root / AfjbCUvqgdpST8)

### Objective
Conduct an in-depth codebase and architecture survey focused on Requirement R2 (Payment Plan Consolidation and Existing Subscriber Preservation).

### Specific Questions to Investigate
1. What payment processing integration exists? (Stripe, PayPal, Razorpay, custom, or mock)?
2. Where are the current payment plans and tiers defined? Look in frontend files (`index.html`, pricing sections, checkout JS), backend routes, configuration files, and database models.
3. What is the current pricing structure and how is the yearly/annual discount currently calculated in the codebase (e.g. percentage discount, fixed amount, 2 months free)?
4. How should the new single tier at 3,500 monthly be structured, and what is the exact resulting yearly price under the existing discount calculation?
5. How are user subscriptions stored, queried, and verified? (Database schema, user session, tokens, status fields, end_date/expiration dates)?
6. How to guarantee that existing subscribers retain uninterrupted access through their current expiration/end date period without premature termination or interruption?
7. What backend routes and frontend UI elements must be updated to remove older purchase options and allow purchasing only the new 3,500 monthly tier (+ calculated yearly)?
8. What automated tests exist for payment and subscription flows?

### Rules & Deliverables
- DO NOT modify or write source code.
- Write your findings, verified evidence (file paths, line numbers, code snippets), and recommendations to `c:\Users\sharo\Desktop\friday\.agents\teamwork\explorer_survey_2\handoff.md`.
- Keep `progress.md` updated with timestamp heartbeats.
- When finished, send a message to the orchestrator with your summary and handoff path.
