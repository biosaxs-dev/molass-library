# Practice Scenario: Copilot Agent 3-Step Loop

## 1. Preparation
- Both users open VS Code in Agent mode (Claude Sonnet 4.5).
- Confirm you are in the `molass-review` private repo.

## 2. Simulated Workflow Steps

### Step 1: Reviewer Comment (Shimizu)
- Shimizu creates or selects a reviewer comment file (e.g., `reviewer-comments/test-python-support.md`).
- Shimizu adds the marker: `NEEDS-TECH-INPUT`.

### Step 2: Technical Input (Takahashi)
- Takahashi asks Copilot Agent:
  > Help me provide technical info for Python 3.8 support.
- Copilot Agent creates a file in `tech-info/` (e.g., `python-3.8-support.md`) with the technical explanation.
- Copilot Agent updates the reviewer comment file, changing the marker to `TECH-INFO-PROVIDED`.

### Step 3: Draft Response (Shimizu)
- Shimizu reads the technical info file.
- Shimizu drafts a response in `response-drafts/` (e.g., `python-3.8-support-response.md`).

### (Optional) Step 4: Review (Takahashi)
- Takahashi reviews the draft for technical accuracy and suggests edits if needed.

## 3. What to Focus On
- Use Copilot Agent for all steps (file creation, marker updates, drafting).
- Check that files and markers are updated as expected.
- Practice clear communication and file navigation.

## 4. Reset for Next Practice
- After practicing, delete or reset the files and markers so you can repeat the scenario.

---

*Use this summary as a checklist or script for your joint practice session.*
