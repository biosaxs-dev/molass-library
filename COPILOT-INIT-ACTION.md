# COPILOT INIT ACTION WORKFLOW

This document defines the unified initialization steps and expected Copilot behaviors for every session in the molass-review repository.

---

## � **Critical Context for Copilot**

**GitHub Account Mapping** (verify BEFORE analyzing any issues):
- `freesemt` = Takahashi (programmer)
- `nshimizu0721` = Shimizu (domain expert)

**Work Division**:
- **Technical paper sections** (Software Design, AI disclosure) → Takahashi drafts, Shimizu reviews
- **Scientific paper sections** (Statement of Need, Research Impact) → Shimizu drafts, Takahashi reviews
- **Review responses** → Shimizu leads drafting, Takahashi provides technical support
- **JOSS posting** → Always Shimizu (unified voice)

---

## �🚦 Initialization: The Magic Phrase

Start every session by saying:
```
Please read COPILOT-INIT.md to initialize
```
Copilot will recognize the user and load the correct context.

---

## 📝 What Copilot Does at Initialization

**Note**: Copilot batches operations together to minimize "Allow" button clicks!

**Best Practice**: Before each "Allow" prompt, Copilot will explain:
- 📋 **What** it's about to do
- 🎯 **Why** it needs to do it
- 📂 **Which files/resources** will be accessed

This helps you make informed decisions and stay engaged with each approval.

### **Phase 1: Read All Context (Single Batch)**
**What you'll see**: "Loading workspace context and user configuration..."

Files to be read:
- COPILOT-INIT.md
- USER-IDENTIFICATION.md
- CURRENT-STATUS.md
- coordination/GITHUB-ACCOUNTS.md
- coordination/REVIEW-ARCHITECTURE.md
- User's quick-start guide

### **Phase 2: Repository Sync (Takahashi Only)**
**What you'll see**: "Syncing molass-library from joss-paper branch..."

1. **Synchronizes molass-library Subtree (Takahashi Only)**
   - **For Takahashi**: Copilot checks if the molass-library subtree needs updating from the joss-paper branch
     - Uses: `git fetch molass-upstream` and `git subtree pull --prefix=molass-library molass-upstream joss-paper --squash`
     - Reports if updates are available or if the subtree is already up-to-date
     - **This ensures Takahashi always works with the latest version of the library**
   - **For Shimizu**: This step is skipped (Shimizu doesn't need to manage the subtree)

### **Phase 3: External Status Checks (Single Batch)**
**What you'll see**: "Checking GitHub issues and JOSS review status..."

Copilot performs these checks together:

2. **Summarizes all open internal GitHub Issues**
   - Checks and summarizes all open issues in this repository
   - Always review this summary before starting your work

3. **Displays the JOSS Review Issue URL (if available)**
   - If the JOSS review issue URL is set in CURRENT-STATUS.md, displays it for quick access

4. **Checks Current JOSS Review Status (Automated)**
   - Fetches current status from JOSS papers page and review issue
   - Reports current phase: PRE-REVIEW, REVIEW PENDING, UNDER REVIEW, or PUBLISHED
   - Identifies if editor and/or reviewers have been assigned
   - Shows date of last activity on JOSS review issue

5. **Monitors the JOSS Review Issue for Actionable Comments**
    - Checks JOSS review issue for new reviewer or editor comments requiring action
    - If actionable comment found with no corresponding internal issue:
       - Alerts Shimizu (and/or Takahashi) about the new comment
       - Recommends creating internal GitHub Issue to track response
       - May draft issue content summarizing the reviewer/editor request
    - Ensures all reviewer and editor requests are tracked internally

### **Phase 4: Update Status (If Needed)**
**What you'll see**: "Updating CURRENT-STATUS.md with latest review information..."

6. **Updates CURRENT-STATUS.md if Status Changed**
   - If JOSS review status changed since last update, automatically updates CURRENT-STATUS.md
   - Keeps coordination repository in sync with actual JOSS review progress

---

## 💡 **Example: What You'll Actually See**

When you say "Please read COPILOT-INIT.md to initialize", here's what happens:

```
Copilot: "📋 Loading workspace context and user configuration..."
         (reads 6 config files)
You:     [Click "Allow"] ← You know it's reading config

Copilot: "🔄 Syncing molass-library from joss-paper branch..."
         (runs git commands)
You:     [Click "Allow"] ← You know it's syncing code

Copilot: "🔍 Checking GitHub issues and JOSS review status..."
         (makes API calls to GitHub + JOSS)
You:     [Click "Allow"] ← You know it's checking external status

Copilot: "✏️ Updating CURRENT-STATUS.md with latest review information..."
         (writes status file if changed)
You:     [Click "Allow"] ← You know it's updating local file
```

**Result**: 
- Typically requires only **3-4 "Allow" clicks** instead of 6+
- Each click is **informed** (you know what you're approving)
- Maintains **attention** (clear context for each decision)
- Prevents **click fatigue** (fewer but meaningful prompts)

---

## 📌 Why This Workflow?
- Ensures everyone is aware of outstanding tasks and review locations.
- Keeps internal and external review processes in sync.
- Prevents missed actions and confusion.
- Makes onboarding and collaboration easier for all team members.

---

## 🔄 When to Update This File
- When the review workflow changes
- When new Copilot behaviors are added
- When the JOSS review process or repository structure changes

---

**Always follow this initialization workflow at the start of every session!**
