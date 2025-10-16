# 🛠️ TAKAHASHI'S QUICK START GUIDE

**Your guide to supporting JOSS review responses with Copilot**

---

## 📱 **Before You Start: One-Time Setup**

### **Already Done! ✅**
- Username path configured in `COPILOT-INIT.md`
- Using Claude Sonnet 4.5
- Repository structure ready
- GitHub Actions bot deployed

**You're all set!**

---

## 💬 **Every Time You Work: The 3-Step Loop**

### **STEP 1: Start Copilot**
Open VS Code and say:
```
Please read COPILOT-INIT.md to initialize
```
Copilot will recognize you as Takahashi and load the right context.

### **STEP 2: Check Status**
Look at `CURRENT-STATUS.md` to see:
- What's happening now
- What you need to do
- What Shimizu is working on

### **STEP 3: Do Your Work**
Follow the workflow below based on what's needed.

---

## 🔄 **Your Support Workflow**

### **Phase 1: Wait for Review to Start**
✅ Nothing to do yet—system is ready!

### **Phase 2: When Shimizu Captures Comments**
✅ No action needed—Shimizu handles this phase.

### **Phase 3: When Shimizu Needs Technical Input**

**What triggers this:**
- Shimizu adds `NEEDS-TECH-INPUT` marker to a reviewer comment file
- Bot automatically creates a GitHub issue tagged with `tech-input-needed` and `takahashi`

**What you do:**
1. **Check GitHub Issues** (you'll get notified)
2. **Read the reviewer comment** (link in the issue)
3. **Provide technical information**:
   - Create a file in `review-discussions/tech-info/`
   - Answer Shimizu's questions
   - Include code examples, file locations, or technical details
4. **Say to Copilot:**

```
Copilot, I've provided technical info for [issue topic]
```

5. **Remove** `NEEDS-TECH-INPUT` marker from the comment file
6. **Close** the GitHub issue

**What happens next:**
- Shimizu uses your info to draft a response

### **Phase 4: When Shimizu's Draft Needs Review**

**What triggers this:**
- Shimizu adds `READY-FOR-TECH-REVIEW` marker to a draft file
- Bot automatically creates a GitHub issue tagged with `tech-review-needed` and `takahashi`

**What you do:**
1. **Check GitHub Issues** (you'll get notified)
2. **Read the draft response** (link in the issue)
3. **Review for technical accuracy**:
   - ✅ Are the technical details correct?
   - ✅ Are promises feasible to implement?
   - ✅ Is the tone professional?
4. **Provide feedback**:
   - Add comments directly in the draft file
   - Or create a review file in `review-discussions/tech-info/`
5. **If approved**, say to Copilot:

```
This draft is approved and ready to post
```

6. **Remove** `READY-FOR-TECH-REVIEW` marker
7. **Close** the GitHub issue

**What happens next:**
- Shimizu posts the approved response to JOSS

### **Phase 5: After Response is Posted**

**What triggers this:**
- Shimizu posts response to JOSS
- Response archived in `posted-responses/`

**What you might need to do:**
- Implement code changes mentioned in the response
- Update documentation
- Create examples or tests
- Commit and push changes to molass-library

---

## 🆘 **Common Situations & What to Say**

### **Situation 1: Got a Technical Input Request**
👉 Say:
```
Copilot, help me create a technical info file for [topic]
```

### **Situation 2: Need to Explain Technical Details**
👉 Say:
```
Copilot, help me explain [technical concept] in simple terms for Shimizu
```

### **Situation 3: Reviewing Shimizu's Draft**
👉 Say:
```
Copilot, help me review this draft for technical accuracy
```

### **Situation 4: Need to Implement Code Changes**
👉 Say:
```
Based on our response, I need to implement [describe change]
```

### **Situation 5: I'm Not Sure About Something**
👉 Say:
```
I need clarification on [topic]. What does Shimizu need from me?
```

---

## 📂 **The Files You'll Use**

### **Files You NEED to Know:**
1. **`CURRENT-STATUS.md`** ← Always check this first
2. **`reviewer-comments/`** ← Read these to understand issues
3. **`tech-info/`** ← Create your technical explanations here
4. **`response-drafts/`** ← Review Shimizu's drafts here
5. **GitHub Issues** ← Your notification system

### **Files You Can IGNORE:**
- `posted-responses/` (archives only, Shimizu manages)
- Most coordination docs (unless specific question)

---

## 💡 **Simple Rules to Remember**

### ✅ **DO:**
- Always initialize Copilot first (read COPILOT-INIT.md)
- Check GitHub Issues regularly for notifications
- Provide clear, simple technical explanations
- Be honest if something is not feasible
- Close issues after completing your part
- Update `CURRENT-STATUS.md` when you finish work

### ❌ **DON'T:**
- Post directly to JOSS (that's Shimizu's role)
- Skip reviewing drafts (your technical expertise is crucial)
- Make promises in responses you can't keep
- Forget to remove markers after completing tasks
- Leave GitHub issues open indefinitely

---

## 🎪 **Two Repositories = Two Purposes**

### **Private Repository (molass-review)** ← You're here now
- Coordinate with Shimizu
- Draft responses together
- Provide technical information
- **NEVER POST THESE TO JOSS!**

### **Public Repository (molass-library)** ← The actual code
- Implement code changes
- Update documentation
- Fix bugs mentioned in review
- This is what reviewers are evaluating

---

## 🤝 **Your Role as Technical Support**

You are the **technical expert supporting Shimizu's responses**.

**You provide**:
- Technical information when Shimizu asks
- Code implementation details
- Feasibility assessments
- Technical accuracy review
- Actual code/doc changes

**You DON'T**:
- Draft most responses (Shimizu does this)
- Post to JOSS (Shimizu does this)
- Make final decisions on response strategy (Shimizu leads)

**Why this approach?**
- Shimizu understands scientific context better
- You focus on what you're best at (code & technical details)
- Unified voice from Shimizu (clearer for reviewers)
- Division of labor = more efficient

---

## 📞 **Getting Help**

### **From Copilot:**
Just ask! Say things like:
- "What technical info does Shimizu need?"
- "Help me review this draft"
- "How should I explain [technical concept]?"

### **From Shimizu:**
- He'll ask questions in the GitHub issues
- Or add comments in the reviewer comment files
- Bot notifications will alert you

### **Emergency:**
If something breaks, just ask Copilot:
```
Something is wrong. Please help me understand what happened.
```

---

## 🎯 **Quick Cheat Sheet**

| **When...** | **You Say...** |
|---|---|
| Starting work | "Please read COPILOT-INIT.md to initialize" |
| Got tech input request | "Help me create technical info for [topic]" |
| Explaining technical details | "Help me explain [concept] simply" |
| Reviewing draft | "Help me review this draft for accuracy" |
| Task complete | "I've completed [task], mark it done" |
| Need implementation help | "I need to implement [change from response]" |
| Confused | "What does Shimizu need from me?" |

---

## 🚀 **Your First Task (When It Comes)**

1. Open VS Code
2. Say: `"Please read COPILOT-INIT.md to initialize"`
3. Check GitHub Issues for `takahashi` label
4. Open the linked reviewer comment or draft
5. Say: `"Help me understand what I need to do here"`
6. Follow Copilot's guidance step-by-step

**You've got this!** 🔧

---

## 🎓 **GitHub Issues Workflow**

### **Issue Type 1: `tech-input-needed`**
**Means**: Shimizu needs technical information from you

**Your actions**:
1. Read the linked reviewer comment
2. Create file in `tech-info/` with your explanation
3. Remove `NEEDS-TECH-INPUT` marker from comment file
4. Close the issue

### **Issue Type 2: `tech-review-needed`**
**Means**: Shimizu's draft needs your technical review

**Your actions**:
1. Read the draft response
2. Check technical accuracy
3. Suggest changes OR approve
4. Remove `READY-FOR-TECH-REVIEW` marker
5. Close the issue

### **Issue Type 3: `review-required`**
**Means**: General review coordination (rare)

**Your actions**:
1. Read the issue description
2. Follow specific instructions
3. Update as needed

---

## 🔍 **How to Check GitHub Issues**

### **Option 1: Web Browser**
1. Go to: `https://github.com/freesemt/molass-review/issues`
2. Look for issues with your name (`takahashi` label)
3. Click to read details

### **Option 2: VS Code (if GitHub extension installed)**
1. Click GitHub icon in sidebar
2. Check "Issues" section
3. Look for assigned issues

### **Option 3: Email Notifications**
- GitHub sends emails when issues are created
- Click link in email to see details

---

## 📝 **Example: Providing Technical Info**

**Shimizu asks**: "Can we support Python 3.13?"

**You create**: `tech-info/python-3.13-support.md`

```markdown
# Python 3.13 Support

**Status**: Yes, we can support it with minor changes.

## Current Situation
- Currently tested: Python 3.8 - 3.12
- Dependencies: All support 3.13

## What Needs to Change
1. Update `pyproject.toml` line 23: `python = "^3.8,<3.14"`
2. Add 3.13 to GitHub Actions testing matrix
3. Test locally (I can do this today)

## Estimated Work
- Time: 2 hours
- Risk: Low

## My Recommendation
We should add this. It's easy and shows we're up-to-date.

---
**Created by**: Takahashi  
**Date**: [Today]
```

Then say to Copilot:
```
I've answered Shimizu's Python 3.13 question
```

---

## 📋 **Example: Reviewing a Draft**

**Shimizu's draft says**: "We will add GPU acceleration support"

**If you think**: "That's too much work for this review"

**You say to Copilot**:
```
This draft promises GPU support, but that's not feasible right now.
Help me suggest a better response.
```

**Copilot will help you** suggest realistic alternatives.

---

**Last updated**: October 16, 2025  
**Questions?** Ask Copilot or contact Shimizu
