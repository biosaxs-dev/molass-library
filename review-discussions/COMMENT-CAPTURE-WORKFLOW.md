# JOSS Comment Capture Workflow

**Simple process for getting reviewer comments from JOSS issue into our private repo**

---

## 🎯 **Quick Start**

When reviewer comments appear on the JOSS issue:

### **Option 1: Manual Copy-Paste** (Start with this - simplest)

1. Open the JOSS review issue in browser
2. Read through new comments
3. Copy each reviewer comment
4. Paste into `reviewer-comments/` using the template
5. Update SIMPLE-RESPONSE-PLAN.md with assignments

**Time**: ~5 minutes per reviewer comment set

---

### **Option 2: GitHub CLI Script** (For later, when you're comfortable)

```powershell
# Fetch comments from JOSS issue (future enhancement)
# gh issue view [ISSUE-NUMBER] --repo openjournals/joss-reviews --json comments
```

---

## 📝 **Step-by-Step Manual Process**

### **Step 1: Navigate to JOSS Issue**
Your JOSS review will be at:
`https://github.com/openjournals/joss-reviews/issues/[YOUR-NUMBER]`

(You'll get this URL when JOSS review begins)

### **Step 2: Identify New Comments**
Look for:
- Comments from reviewers (usernames starting with @)
- Checklist updates
- Questions or feedback

### **Step 3: Copy to Template**
For each reviewer:
1. Copy the template: `reviewer-comments/template-reviewer-comments.md`
2. Rename: `reviewer-1-[date]-comments.md`
3. Fill in the reviewer's comments
4. Save in `reviewer-comments/` folder

### **Step 4: Initial Assignment**
Update `SIMPLE-RESPONSE-PLAN.md`:
- Mark technical comments for Takahashi
- Mark scientific comments for Shimizu
- Mark mixed comments for both

### **Step 5: Notify Your Partner**
Let the other person know new comments arrived:
- Commit the files
- Or mention directly if working together

---

## 🔗 **Tracking Connection**

**Maintain the link between:**
```
JOSS Issue Comment
    ↓ (captured in)
reviewer-comments/reviewer-1-comments.md
    ↓ (assigned in)
SIMPLE-RESPONSE-PLAN.md
    ↓ (draft created in)
response-drafts/[topic]-draft.md
    ↓ (posted back to)
JOSS Issue Comment (your response)
    ↓ (archived in)
posted-responses/[date]-[topic].md
```

---

## 💡 **Tips for Efficiency**

✅ **DO:**
- Capture comments in batches (once or twice a day)
- Include the JOSS issue URL in every captured comment file
- Add your initial thoughts while capturing
- Keep original formatting/links from reviewer

❌ **DON'T:**
- Wait too long to capture (comments pile up)
- Modify reviewer's words (copy exactly)
- Forget to link back to JOSS issue URL
- Skip the assignment step

---

## 🚀 **Future Automation Ideas**

Once you're comfortable with manual process, could automate:
- GitHub CLI script to fetch new comments
- Browser bookmarklet to copy comment with metadata
- GitHub API integration to monitor for new comments
- Auto-notification when new reviewer comments appear

**For now: Keep it simple with manual copy-paste**

---

## 📋 **Checklist After Capturing Comments**

- [ ] All new reviewer comments copied to `reviewer-comments/`
- [ ] JOSS issue URL included in each file
- [ ] Reviewer names identified
- [ ] Initial technical/scientific categorization done
- [ ] SIMPLE-RESPONSE-PLAN.md updated with assignments
- [ ] Partner notified about new comments
- [ ] Files committed to repository

---

**Start simple, improve as you learn what works for your workflow!**
