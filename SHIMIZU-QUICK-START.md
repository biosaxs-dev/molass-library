# 🎯 SHIMIZU'S QUICK START GUIDE

**Your simple guide to handling JOSS review responses with Copilot**

---

## 📱 **Before You Start: One-Time Setup**

### **Step 1: Update Your Username**
Open `COPILOT-INIT.md` and find this line:
```markdown
- **User Path Contains**: `shimizu` (case insensitive)
```
Change `shimizu` to match YOUR actual Windows username folder.

### **Step 2: Choose Your Model**
Use **Claude Sonnet 4.5** (same as Takahashi for consistency)

**That's it for setup!**

---

## 💬 **Every Time You Work: The 3-Step Loop**

### **STEP 1: Start Copilot**
Open VS Code and say:
```
Please read COPILOT-INIT.md to initialize
```
Copilot will recognize you as Shimizu and load the right context.

### **STEP 2: Check Status**
Look at `CURRENT-STATUS.md` to see:
- What's happening now
- What you need to do
- What Takahashi is working on

### **STEP 3: Do Your Work**
Follow the workflow below based on the review phase.

---

## 🔄 **The Review Response Workflow**

### **Phase 1: Wait for Review to Start**
✅ Nothing to do yet—relax and wait!

### **Phase 2: When Reviewer Comments Arrive**

**What you do:**
1. Open the JOSS review issue (public GitHub)
2. Find a reviewer comment you want to capture
3. **Copy the comment text** (Ctrl+C)
4. Come to VS Code Copilot chat and say:

```
Copilot, please capture this reviewer comment:

[Paste the comment here]
```

5. Copilot will create a formatted file in `reviewer-comments/`
6. Tell Copilot if you need Takahashi's help:
   - "This needs technical input from Takahashi"
   - "I can handle this myself"

**What happens automatically:**
- If you need Takahashi → Bot creates GitHub issue for him
- If you can handle it → You move to Phase 3

### **Phase 3: Draft Your Response**

**What you do:**
1. Open the template: `review-discussions/response-drafts/template-response-draft.md`
2. Say to Copilot:

```
Copilot, please help me draft a response to [describe the comment]
```

3. Copilot will create a draft file for you
4. Review the draft, edit if needed
5. When ready, say:

```
This draft is ready for Takahashi to review
```

6. Add marker: `READY-FOR-TECH-REVIEW` to your draft file

**What happens automatically:**
- Bot creates GitHub issue asking Takahashi to review

### **Phase 4: Wait for Takahashi's Review**

**What you do:**
- ☕ Take a break, Takahashi is reviewing

**What Takahashi does:**
- Reviews your draft
- Suggests changes or approves
- Closes the GitHub issue when done

### **Phase 5: Post to JOSS**

**What you do:**
1. Open your approved draft file
2. Copy the response text
3. Go to the JOSS issue (public GitHub)
4. Paste and post the comment
5. Come back to VS Code and say:

```
Copilot, I posted the response to JOSS
```

6. Copilot will archive it in `posted-responses/`

**Repeat for each reviewer comment!**

---

## 🆘 **Common Situations & What to Say**

### **Situation 1: New Reviewer Comment**
👉 Say:
```
Copilot, please capture this reviewer comment:
[paste comment]
```

### **Situation 2: Need Technical Info from Takahashi**
👉 Say:
```
I need Takahashi's help with this. Please create a technical input request.
```

### **Situation 3: Ready to Draft a Response**
👉 Say:
```
Copilot, help me draft a response to [describe the issue]
```

### **Situation 4: My Draft is Ready for Review**
👉 Say:
```
This draft is ready for Takahashi to review
```
Then add `READY-FOR-TECH-REVIEW` to the draft file.

### **Situation 5: I Posted the Response**
👉 Say:
```
I posted this response to JOSS
```

### **Situation 6: I'm Confused!**
👉 Say:
```
I'm stuck. What should I do next?
```

---

## 📂 **The Files You'll Use**

### **Files You NEED to Know:**
1. **`CURRENT-STATUS.md`** ← Always check this first
2. **`reviewer-comments/`** ← Captured reviewer comments go here
3. **`response-drafts/`** ← Your draft responses go here
4. **`posted-responses/`** ← Archive of what you posted

### **Files You Can IGNORE:**
- Everything in `.github/workflows/` (bot automation)
- Everything in `coordination/` (background documentation)
- Most other files (unless Copilot tells you otherwise)

---

## 💡 **Simple Rules to Remember**

### ✅ **DO:**
- Always initialize Copilot first (read COPILOT-INIT.md)
- Copy-paste reviewer comments instead of typing
- Ask Copilot for help anytime
- Use simple language when talking to Copilot
- Let the bot handle notifications to Takahashi
- Check `CURRENT-STATUS.md` regularly

### ❌ **DON'T:**
- Post directly to JOSS without Takahashi reviewing
- Worry about GitHub Actions or technical setup
- Edit workflow files in `.github/`
- Stress about "doing it perfectly"
- Forget to archive posted responses

---

## 🎪 **Two Repositories = Two Purposes**

### **Private Repository (molass-review)** ← You're here now
- Draft responses
- Coordinate with Takahashi
- Practice and prepare
- **NEVER POST THESE TO JOSS!**

### **Public JOSS Issue** ← Where final responses go
- Only post APPROVED responses here
- This is what reviewers and editors see
- Be professional and polite

---

## 🤝 **Your Role as Lead Responder**

You are the **primary author of all responses**, both scientific and technical.

**You draft**:
- Responses to scientific questions → *You know the domain!*
- Responses to technical questions → *Ask Takahashi for details, then you write*

**Takahashi supports**:
- Provides technical information when you ask
- Reviews your drafts for accuracy
- Implements code/doc changes
- But YOU write the actual response text

**Why this approach?**
- You understand the scientific context best
- Unified voice in responses (sounds like one team)
- Takahashi helps but doesn't need to write everything

---

## 📞 **Getting Help**

### **From Copilot:**
Just ask! Say things like:
- "What should I do next?"
- "Help me understand this comment"
- "Is this draft good?"

### **From Takahashi:**
The bot will automatically notify him when you:
- Add `NEEDS-TECH-INPUT` to a reviewer comment file
- Add `READY-FOR-TECH-REVIEW` to a draft file

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
| New reviewer comment | "Copilot, capture this comment: [paste]" |
| Need tech help | "I need Takahashi's input on this" |
| Want to draft | "Help me draft a response to [topic]" |
| Draft ready | "This is ready for Takahashi to review" |
| Posted to JOSS | "I posted this response to JOSS" |
| Confused | "What should I do next?" |

---

## 🚀 **Your First Session (When Review Starts)**

1. Open VS Code
2. Say: `"Please read COPILOT-INIT.md to initialize"`
3. Say: `"What's my current status?"`
4. Wait for Copilot to explain the situation
5. Follow Copilot's guidance step-by-step

**You've got this!** 🎉

---

**Last updated**: October 16, 2025  
**Questions?** Ask Copilot or contact Takahashi
