Consolidate FRIDAY to a single branded AI model ("friday Cyber Pro") on Ollama, update payment pricing to a single tier at 3,500 monthly with yearly discount calculation while grandfathering existing active subscriptions, add an engaging tactical progress animation during slow generation, and audit and fix bugs and security vulnerabilities across the codebase and live VPS.

Integrity mode: development

## Requirements

### R1. Ollama Model Cleanup and Rebranding
Remove the two older models (`hf.co/RavichandranJ/Dolphin3-Cyber-8B-GGUF:Q8_0` and `huihui_ai/baronllm-abliterated:latest`) from Ollama and retain only `orcasaq-cyber-27b:latest`. Rebrand and display this model exclusively as "friday Cyber Pro" throughout the application. Ensure strict branding adherence: never reveal underlying model names, vendors, or raw system names in greetings, UI elements, or error messages.

### R2. Payment Plan Consolidation and Existing Subscriber Preservation
Remove all older payment plans from being offered for purchase and offer only the new single tier updated to 3,500 monthly, with the yearly rate calculated based on the existing discount structure in the codebase (e.g., standard annual discount or 2 months free). Apply updates across the frontend (such as `index.html` and pricing sections) and backend payment processing routes. Crucially, preserve existing subscriptions for all current customers: active subscriptions must remain valid and honored through their current expiration/end date period without interruption or premature termination.

### R3. Chat UX Long-Wait Progress State
Implement a tactical scanning radar/pulse animation with dynamic multi-stage status updates (such as "Analyzing target architecture...", "Synthesizing exploit payload...", "Compiling neural response...") during model inference (~2.5–3 minutes) to keep users engaged and prevent page refreshes or repeated retry requests.

### R4. Security Audit, Bug Fixes, and Live VPS Deployment
Perform a comprehensive audit across application code, dependencies, and VPS services (213.133.97.141) to identify and remediate security vulnerabilities and bugs. Verify changes locally with automated verification tests and execute model removals and deployment directly on the live VPS environment.

## Acceptance Criteria

### Model Consolidation & Branding
- [ ] Only `orcasaq-cyber-27b:latest` is active on Ollama, branded as "friday Cyber Pro".
- [ ] The two older models (`Dolphin3-Cyber-8B-GGUF:Q8_0` and `baronllm-abliterated:latest`) are removed from the Ollama host.
- [ ] No underlying model identifiers, raw vendor names, or system tags are exposed in the user interface, greetings, or error outputs.

### Pricing, Payments & Existing Subscriptions
- [ ] The frontend displays only the single new pricing tier at 3,500 monthly, with the yearly rate calculated according to existing discount logic; older plans are removed from new purchase offerings.
- [ ] Backend payment routes process new subscriptions and checkouts exclusively under the updated pricing.
- [ ] Existing subscribers retain uninterrupted access and their current subscription end date / expiration period remains intact and honored.

### Chat UX & Waiting State
- [ ] During long generation cycles (~2.5–3 minutes), the chat interface displays an animated tactical radar/pulse indicator with rotating progress messages.
- [ ] The waiting state prevents users from triggering concurrent duplicate requests or queue spikes via retry buttons.

### Security, Stability & Verification
- [ ] Codebase and server vulnerabilities, security flaws, and functional bugs identified during audit are patched.
- [ ] Automated tests verify the payment updates, chat UI state transitions, and server endpoints without regressions.
- [ ] Updates and model removals are deployed and verified live on the VPS (213.133.97.141).
