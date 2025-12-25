# COPILOT INIT ACTION WORKFLOW

This document defines the unified initialization steps and expected Copilot behaviors for every session in the molass-review repository.

---

## 🚦 Initialization: The Magic Phrase

Start every session by saying:
```
Please read COPILOT-INIT.md to initialize
```
Copilot will recognize the user and load the correct context.

---

## 📝 What Copilot Does at Initialization

1. **Synchronizes molass-library Subtree (Takahashi Only)**
   - **For Takahashi**: Copilot checks if the molass-library subtree needs updating from the joss-paper branch
     - Uses: `git fetch molass-upstream` and `git subtree pull --prefix=molass-library molass-upstream joss-paper --squash`
     - Reports if updates are available or if the subtree is already up-to-date
     - **This ensures Takahashi always works with the latest version of the library**
   - **For Shimizu**: This step is skipped (Shimizu doesn't need to manage the subtree)

2. **Summarizes all open internal GitHub Issues**
   - Copilot will check and summarize all open issues in this repository.
   - Always review this summary before starting your work.

3. **Displays the JOSS Review Issue URL (if available)**
   - If the JOSS review issue URL is set in CURRENT-STATUS.md, Copilot will display it for quick access to the official review thread.

4. **Checks Current JOSS Review Status (Automated)**
   - Copilot will fetch the current status from the JOSS papers page and the review issue
   - Reports the current phase: PRE-REVIEW, REVIEW PENDING, UNDER REVIEW, or PUBLISHED
   - Identifies if editor and/or reviewers have been assigned
   - Shows the date of last activity on the JOSS review issue
   - **This happens automatically at every initialization to keep you informed**

5. **Monitors the JOSS Review Issue for Actionable Comments**
    - Copilot checks the JOSS review issue for new reviewer or editor comments that require action from the authors (such as requests for clarification, documentation changes, bug fixes, or additional information).
    - If such a comment appears and there is no corresponding internal issue in this repository:
       - Copilot will alert Shimizu (and/or Takahashi) that a new actionable comment has been posted in the JOSS review thread.
       - Copilot will recommend creating a new internal GitHub Issue to track and coordinate the response.
       - Copilot may draft the issue content, summarizing the reviewer/editor request for easy tracking and assignment.
    - This ensures that all reviewer and editor requests are tracked internally and nothing is missed during the review process.

6. **Updates CURRENT-STATUS.md if Status Changed**
   - If the JOSS review status has changed since the last update, Copilot will automatically update CURRENT-STATUS.md
   - This keeps the coordination repository in sync with the actual JOSS review progress

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
