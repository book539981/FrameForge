# AGENTS.md

# FrameForge Repository Agent Instructions

This repository is intentionally NOT specification-complete.

Missing Rules are intentional.

DO NOT complete them.

---

# Before Coding

Before any implementation:

1. Read:
   Proto/FF_Constitution.md

2. Read:
   Proto/FF_Dev_Workflow.md

3. Read:
   Proto/FF_Project_Reference.md

4. Confirm:

 - Problem Definition
 - Current Milestone
 - Required Rules

If any Rule is missing:

STOP.

Do not write code first.

---

# File Encoding

All project documents are UTF-8.

When reading Markdown or text files on Windows:

Always explicitly specify UTF-8 encoding.

Never infer requirements from garbled text.

If encoding is incorrect:

STOP.

Fix encoding first.

Then continue.

---

# Rule Authority

Only Bryan can approve a Rule.

Coding Agent must never invent one.

Coding Agent implements Rules.

If implementation requires a Rule that has not been explicitly confirmed:

STOP.

Output:

UNDEFINED RULE

Explain:

- which Rule is missing
- why implementation cannot continue

Do NOT infer.

Do NOT guess.

Do NOT implement placeholder behavior.

---

# Forbidden Behaviors

Never:

- infer missing Rules
- complete unfinished architecture
- implement undefined behavior
- add "reasonable defaults"
- silently expand project scope
- couple multiple assumptions into one implementation
- hide assumptions inside Processor, State Machine or Config

Missing Rules are NOT bugs.

They are waiting for Bryan.

---

# Coding Scope

Implement only the requested task.

Do not:

- optimize
- future-proof
- generalize
- redesign
- add architecture
- clean unrelated code

unless explicitly requested.

---

# Existing Code

Existing code is an implementation,

not the source of truth.

When code conflicts with repository documents:

Follow repository documents.

Do not preserve incorrect implementation because it already exists.

---

# If Unsure

STOP.

Report the gap.

Wait for Bryan.