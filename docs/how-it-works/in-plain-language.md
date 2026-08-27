# In plain language

You type a question, like *"why are payment-service requests timing out?"*
The copilot then, one step at a time:

1. **Searches the logs** for anything relevant — by service, error level, time
   window, or a specific trace id.
2. **Checks a curated known-issue knowledge base** for vendor-specific
   patterns (Postgres connection exhaustion, Redis cache stampedes, JWT key
   rotation bugs, and so on) that match what it found.
3. Repeats step 1-2 as needed, up to a budget (at most 15 tool calls, at
   most 120 seconds) so an unproductive investigation can't run forever.
4. **Drafts a structured incident report**: a title, a severity, a root
   cause, the specific evidence backing that root cause, recommended
   actions, and a confidence score.
5. **Checks its own work** before showing it to you. Every piece of
   evidence in the report must trace back to something it actually
   retrieved in step 1-2 — never something it only inferred or guessed.
   If the evidence doesn't hold up, or the report makes a serious claim
   (like "this looks like an attack") without anomalous log lines or a
   known-issue match to back it up, the report is downgraded: marked
   `insufficient_evidence` with a note explaining what's missing, instead
   of being published as a confident (and possibly wrong) answer.

You watch all five steps happen live, streamed to the browser as they
happen, then see the final report — or the honest refusal.

See [a real incident](a-real-incident.md) for a full walkthrough with an
actual seeded example, or the [architecture overview](../architecture/overview.md)
for how the pieces above are wired together in code.
