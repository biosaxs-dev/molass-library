# JOSS REVIEW RESPONSE ARCHITECTURE

**How the review process actually works - Read this first!**

---

## 🏗️ **Two-Repository System**

### **Repository 1: JOSS Reviews (Public)**
**Location**: `https://github.com/openjournals/joss-reviews/issues/[YOUR-NUMBER]`

**Who has access**: Everyone (public)
- JOSS reviewers
- JOSS editors
- Anyone on the internet

**What happens there**:
- ✅ Reviewers post their comments and questions
- ✅ We (Takahashi + Shimizu) post public responses
- ✅ Reviewers check off their checklist items
- ✅ EditorialBot manages automation (PDF generation, etc.)
- ✅ Final acceptance decision happens here

**⚠️ Important**: Everything posted here is **public and permanent**

---

### **Repository 2: molass-review (Private - THIS REPO)**
**Location**: `https://github.com/freesemt/molass-review`

**Who has access**: Only us
- Takahashi (Programmer)
- Shimizu (Domain Expert)
- GitHub Copilot (Claude Sonnet 4.5)

**What happens here**:
- ✅ **Private strategy discussions**
- ✅ **Draft responses** before posting publicly
- ✅ **Coordination files** (who does what)
- ✅ **Context preservation** across sessions
- ✅ **Internal task tracking**

**⚠️ Important**: Nothing here is visible to JOSS reviewers

---

## 🔄 **Complete Workflow**

### **Phase 1: Reviewer Comments Arrive** (Public JOSS Repo)

```
[JOSS Reviews Issue]
├── Reviewer 1 posts: "Can you clarify the installation process?"
├── Reviewer 2 posts: "Explain the baseline methodology better"
└── EditorialBot posts: "PDF regenerated"
```

### **Phase 2: Internal Strategy Session** (Private molass-review Repo)

**Step 1: Capture Comments**
```
Takahashi or Shimizu:
1. Copy reviewer comments from JOSS issue
2. Paste into review-discussions/reviewer-comments/
3. Use template to organize
```

**Step 2: Coordination**
```
Both team members:
1. Read SIMPLE-RESPONSE-PLAN.md
2. Assign comments based on expertise:
   - Technical (installation) → Takahashi
   - Scientific (methodology) → Shimizu
3. Update tracking file with assignments
```

**Step 3: Draft Responses** (Private, in this repo)
```
Individual work:
- Takahashi drafts technical responses
- Shimizu drafts scientific responses
- Save drafts in review-discussions/response-drafts/
```

**Step 4: Internal Review**
```
Collaboration:
- Takahashi reviews Shimizu's drafts (technical feasibility)
- Shimizu reviews Takahashi's drafts (scientific accuracy)
- Iterate until both approve
- Use Copilot for assistance (Claude Sonnet 4.5)
```

### **Phase 3: Public Response** (Back to Public JOSS Repo)

```
[JOSS Reviews Issue]
├── Takahashi posts: "Thank you for the feedback on installation..."
├── Shimizu posts: "Regarding the baseline methodology..."
└── Reviewers respond and check off items
```

**Step 5: Track Progress**
```
Back in private repo:
- Update SIMPLE-RESPONSE-PLAN.md (mark items complete)
- Update CURRENT-STATUS.md
- Document any new actions needed
```

---

## 📁 **File Flow Example**

### **In Private Repo (molass-review):**

```
review-discussions/
├── reviewer-comments/
│   └── reviewer-1-comments.md          # Copied from JOSS issue
├── response-drafts/
│   ├── takahashi-installation.md       # Draft before posting
│   └── shimizu-methodology.md          # Draft before posting
└── posted-responses/
    ├── 2025-10-20-installation.md      # Copy of what was posted
    └── 2025-10-20-methodology.md       # Archive of public response
```

### **In Public JOSS Issue:**
```
Just the final polished responses
(No drafts, no internal discussion visible)
```

---

## 👥 **Team Member Roles**

### **Takahashi (Programmer)**
**Public JOSS interactions:**
- Support Shimizu's responses with technical details
- Update code/documentation based on feedback
- Handle GitHub repository issues
- Post only when specifically needed for technical implementation details

**Private coordination:**
- Review Shimizu's drafts for technical accuracy and feasibility
- Provide technical information for Shimizu's responses
- Implement code/documentation changes
- Manage repository infrastructure

### **Shimizu (Domain Expert)**
**Public JOSS interactions:**
- **PRIMARY RESPONDER** - Leads all responses to JOSS reviewers
- Draft and post most responses (both scientific and technical)
- Explain methodology, research context, and domain expertise
- Provide literature references
- Coordinate overall response strategy

**Private coordination:**
- Lead all response drafting (with Takahashi's support)
- Gather technical details from Takahashi for responses
- Ensure scientific accuracy and clarity
- Decide when Takahashi should post directly vs provide info

### **GitHub Copilot (Claude Sonnet 4.5)**
**Never posts publicly** (only assists privately)

**Private assistance:**
- Help draft responses
- Suggest improvements
- Maintain context across sessions
- Provide JOSS review insights

---

## 🚨 **Critical Rules**

### **DO:**
✅ Draft everything privately first
✅ Both review before posting publicly
✅ Keep JOSS responses professional and polite
✅ Update private tracking files after public posts
✅ Use Copilot for private drafting and review

### **DON'T:**
❌ Post unreviewed drafts to JOSS issue
❌ Discuss strategy in public JOSS issue
❌ Copy-paste Copilot responses without review
❌ Forget to update private coordination files
❌ Let JOSS reviewers see internal discussions

---

## 🤖 **Bot Considerations**

**What could be automated in THIS private repo:**
- Status updates when drafts are committed
- Reminders about pending reviewer comments
- Cross-references between drafts and JOSS issue
- Tracking completion of response assignments

**What CANNOT be automated:**
- Nothing should auto-post to public JOSS issue
- All public responses must be human-reviewed
- Final decision to post is always manual

---

## 📊 **Information Flow Diagram**

```
JOSS PUBLIC ISSUE (openjournals/joss-reviews)
     ↓ (read reviewer comments)
     ↓
PRIVATE REPO (molass-review)
     ├─→ Capture comments
     ├─→ Assign to Takahashi/Shimizu
     ├─→ Draft responses privately
     ├─→ Internal review + Copilot assistance
     └─→ Finalize response
     ↓ (copy-paste final response)
     ↓
JOSS PUBLIC ISSUE (openjournals/joss-reviews)
     ↓ (reviewers respond)
     ↓
PRIVATE REPO (update tracking)
```

---

## 💡 **Key Insight**

**This is a "war room" architecture:**
- **Public battlefield** = JOSS issue (polished, professional)
- **Private war room** = This repo (strategy, drafts, coordination)
- **Intelligence** = Copilot (helps plan, never seen publicly)

---

## 📝 **Questions to Address**

1. **How do we efficiently copy comments from JOSS issue to private repo?**
   - Manual copy-paste?
   - Script to fetch via GitHub API?
   - Browser extension?

2. **How do we prevent accidentally posting drafts publicly?**
   - Naming convention (DRAFT prefix)?
   - Review checklist before posting?
   - Two-person approval required?

3. **How do we keep track of which comments have been addressed?**
   - Checkbox in SIMPLE-RESPONSE-PLAN.md?
   - Link to posted response?
   - Copy of JOSS checklist?

4. **How do both team members know when the other has finished a draft?**
   - Commit message convention?
   - Issue in this repo?
   - External notification (email, Slack)?

---

**Status**: Architecture documented - ready for team input and automation design

**Next step**: Team review and address the questions above
