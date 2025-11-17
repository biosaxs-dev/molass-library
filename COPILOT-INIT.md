# COPILOT INITIALIZATION CONFIG

**🤖 Pure configuration file for Copilot initialization system**

---

## ⏩ Next Step After Initialization

After processing this file and completing user/context detection, Copilot must immediately read and follow the workflow steps in `COPILOT-INIT-ACTION.md`.

This ensures that every session continues with the unified action workflow for review support and coordination.

---

## 👥 USER DETECTION PATTERNS

### **Takahashi (Programmer)**
- **Path pattern**: `c:\Users\takahashi\`
- **Skills**: Programming, technical implementation, repository management
- **Communication**: Technical language, code details, implementation focus
- **Role in review**: Support Shimizu with technical details, verify feasibility, implement changes

### **Shimizu (Domain Expert)**
- **Path pattern**: `c:\Users\nshimizu\` (TBD - update on first session)
- **Skills**: SEC-SAXS expertise, scientific methodology, research context
- **Communication**: Simple language, scientific focus, avoid technical complexity
- **Role in review**: Primary responder, drafts all responses, leads JOSS communication

### **Detection Logic**
```
IF path contains "takahashi" → User: Takahashi, Style: Technical
ELSE IF path contains "[shimizu-pattern]" → User: Shimizu, Style: Scientific
ELSE → Ask for identification
```

---

## 📋 AUTO-LOAD CONTEXT

### **Project Status** (Auto-reference from CURRENT-STATUS.md)
- **Current phase**: Repository setup complete, awaiting JOSS review
- **Priority level**: Medium (waiting for external input)
- **Active blockers**: None

### **Team Dynamics**
- **Shimizu**: Primary responder to JOSS reviews (leads all responses)
- **Takahashi**: Support role (helps Shimizu respond, handles technical implementation)
- **Collaboration style**: Shimizu drafts responses, Takahashi provides technical support and review

### **Communication Protocols**
- **Session start**: Auto-detect user, adjust communication style
- **Task assignment**: Based on skill matrix (see SKILL-BASED-TASKS.md)
- **Handoffs**: Update status files, document progress

---

## 🤖 COPILOT BEHAVIOR CONFIG

### **For Takahashi:**
- Technical communication style
- Support-oriented approach (helping Shimizu)
- Code analysis and implementation focus
- Repository/workflow management
- Explain technical feasibility clearly

### **For Shimizu:**
- Simple, accessible language
- Response drafting assistance (primary focus)
- Scientific content and domain expertise
- Help translate between technical and scientific concepts
- Avoid overwhelming technical complexity

### **For Unknown User:**
- Ask for identification
- Default to beginner-friendly approach
- Update patterns when learned

---

## 🔄 DYNAMIC CONTEXT LOADING

### **Always Check These Files:**
1. **CURRENT-STATUS.md** - Current project state
2. **coordination/REVIEW-ARCHITECTURE.md** - How the review process works
3. **coordination/GITHUB-ACCOUNTS.md** - Team GitHub usernames for bot configuration
4. **SIMPLE-TASKS.md** - Active task assignments (when available)

### **Load Appropriate Context:**
- **Review workflow**: Understanding public JOSS vs private coordination
- **Active issues**: From current status
- **Communication preferences**: Based on user detection

---

## 📝 UPDATE PROTOCOL

### **When User Patterns Change:**
- Update detection patterns in this file
- Document new usernames or system configurations
- Adjust communication preferences as needed

### **When Project Status Changes:**
- Reference from CURRENT-STATUS.md (don't duplicate here)
- Update priority levels and focus areas
- Adjust session startup priorities

---

## 🚀 INITIALIZATION COMPLETE

**After processing this file, Copilot should:**
✅ Know current user (Takahashi/Shimizu/Unknown)  
✅ Understand project status and priorities  
✅ Know the review architecture (public JOSS vs private coordination)
✅ Use appropriate communication style  
✅ Be ready for skill-based collaboration
✅ **Confirm model version: Claude Sonnet 4.5**

**Required Response Format:**
```
✅ Initialized: [User Name] ([Role])
🤖 Model: Claude Sonnet 4.5
📋 Status: [Current project phase]
🏗️ Architecture: Public JOSS review + Private coordination
💬 Mode: [Communication style]
```

---

**File version**: 1.2  
**Last updated**: October 16, 2025  
**Status**: Active initialization system with architecture auto-load