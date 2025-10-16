# Collaboration Bot - User Guide

**How to use the collaboration bots for Shimizu-Takahashi workflow**

---

## 🤖 **What the Bots Do**

The collaboration bot system automates coordination between Shimizu (primary responder) and Takahashi (technical support).

**Four automated workflows:**
1. **Technical Input Request** - Shimizu requests tech info from Takahashi
2. **Draft Review Request** - Shimizu requests tech accuracy review
3. **Tech Info Notification** - Alerts when Takahashi provides info
4. **Review Completion** - Confirms when Takahashi approves draft

---

## 🔄 **Workflow 1: Technical Input Request**

### **When Shimizu Needs Technical Info:**

**Step 1**: Capture reviewer comment in `reviewer-comments/`

**Step 2**: Add this marker somewhere in the file:
```
Status: NEEDS-TECH-INPUT
```

**Step 3**: Commit and push the file

**Step 4**: Bot automatically:
- Creates GitHub issue: "🔧 Technical Input Needed: [topic]"
- Assigns to @takahashi
- Adds label: `tech-input-needed`

**Step 5**: Takahashi gets notification, provides info

**Step 6**: Bot notifies Shimizu when info is ready

---

## 📋 **Workflow 2: Draft Review Request**

### **When Shimizu Finishes a Draft:**

**Step 1**: Complete your draft in `response-drafts/`

**Step 2**: Add this to the draft file:
```
**Post Status**: READY-FOR-TECH-REVIEW
```

**Step 3**: Commit and push

**Step 4**: Bot automatically:
- Creates GitHub issue: "📋 Technical Review Needed: [topic]"
- Assigns to @takahashi
- Adds label: `tech-review-needed`
- Warns Shimizu not to post yet

**Step 5**: Takahashi reviews draft, checks accuracy box

**Step 6**: Bot confirms review complete, closes issue

**Step 7**: Shimizu can safely post to JOSS

---

## ✅ **For Takahashi: Responding to Bot Requests**

### **When Bot Requests Technical Input:**

1. You'll get GitHub issue notification
2. Read the reviewer comment file mentioned
3. Create file in `review-discussions/tech-info/[topic].md`
4. Include:
   - Technical answer
   - Feasibility assessment
   - Implementation notes if needed
5. Commit and push
6. Bot automatically notifies Shimizu

### **When Bot Requests Draft Review:**

1. You'll get GitHub issue notification
2. Read the draft file mentioned
3. Check for technical accuracy
4. In the draft file, check this box:
   ```
   - [x] **Technical accuracy verified** (Reviewed by: Takahashi)
   ```
5. Commit and push
6. Bot automatically notifies Shimizu and closes issue

---

## 🏷️ **Required GitHub Labels**

Create these labels in your repository:
- `tech-input-needed` (Color: `#0366d6` blue)
- `tech-review-needed` (Color: `#d73a4a` red)
- `takahashi` (Color: `#fbca04` yellow)
- `review-required` (Color: `#e99695` pink)

**Create labels:**
```powershell
gh label create "tech-input-needed" --color "0366d6" --description "Shimizu needs technical information"
gh label create "tech-review-needed" --color "d73a4a" --description "Draft needs Takahashi review"
gh label create "takahashi" --color "fbca04" --description "Assigned to Takahashi"
gh label create "review-required" --color "e99695" --description "Review required before posting"
```

---

## 💡 **Tips for Success**

✅ **DO:**
- Use exact markers: `NEEDS-TECH-INPUT` and `READY-FOR-TECH-REVIEW`
- Commit and push to trigger bots
- Respond to bot-created issues promptly
- Close issues when complete

❌ **DON'T:**
- Misspell the trigger markers
- Forget to commit/push changes
- Post to JOSS without bot approval
- Delete bot-created issues (close them instead)

---

## 🔧 **Troubleshooting**

**Bot didn't create an issue:**
- Check if marker is spelled correctly
- Verify file is in correct folder
- Check GitHub Actions tab for errors
- Make sure you committed and pushed

**Bot created duplicate issues:**
- This shouldn't happen (bot checks for existing issues)
- If it does, close duplicates manually

**Need to cancel a request:**
- Just close the bot-created issue
- Add comment explaining why

---

## 📊 **Workflow Summary**

```
Shimizu needs tech info
    ↓
Mark file: NEEDS-TECH-INPUT
    ↓
Bot creates issue for Takahashi
    ↓
Takahashi provides info in tech-info/
    ↓
Bot notifies Shimizu
    ↓
Shimizu drafts response
    ↓
Mark draft: READY-FOR-TECH-REVIEW
    ↓
Bot creates review issue for Takahashi
    ↓
Takahashi reviews, checks accuracy box
    ↓
Bot confirms complete, closes issue
    ↓
Shimizu posts to JOSS
```

---

**Status**: Bot system ready to use!
**Next Step**: Create the required GitHub labels
