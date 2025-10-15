# COPILOT INITIALIZATION CONFIG

**🤖 Pure configuration file for Copilot initialization system**

---

## 👥 USER DETECTION PATTERNS

### **Takahashi (Programmer)**
- **Path pattern**: `c:\Users\takahashi\`
- **Skills**: Programming, technical implementation, repository management
- **Communication**: Technical language, code details, implementation focus
- **Typical tasks**: Code changes, GitHub Actions, technical responses

### **Shimizu (Domain Expert)**
- **Path pattern**: `c:\Users\[shimizu-username]\` (TBD - update on first session)
- **Skills**: SEC-SAXS expertise, scientific methodology, research context
- **Communication**: Simple language, scientific focus, avoid technical complexity
- **Typical tasks**: Scientific accuracy review, methodology explanations

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
- **Takahashi**: Technical lead, handles programming tasks
- **Shimizu**: Scientific lead, handles domain expertise  
- **Collaboration style**: Skill-based task distribution

### **Communication Protocols**
- **Session start**: Auto-detect user, adjust communication style
- **Task assignment**: Based on skill matrix (see SKILL-BASED-TASKS.md)
- **Handoffs**: Update status files, document progress

---

## 🤖 COPILOT BEHAVIOR CONFIG

### **For Takahashi:**
- Technical communication style
- Code analysis and programming focus
- Detailed explanations
- Repository/workflow management

### **For Shimizu:**
- Simple, accessible language
- Scientific content focus
- Domain expertise support
- Avoid technical complexity

### **For Unknown User:**
- Ask for identification
- Default to beginner-friendly approach
- Update patterns when learned

---

## 🔄 DYNAMIC CONTEXT LOADING

### **Always Check These Files:**
1. **CURRENT-STATUS.md** - Current project state
2. **SIMPLE-TASKS.md** - Active task assignments
3. **USER-IDENTIFICATION.md** - Latest identification patterns

### **Load Appropriate Context:**
- **Recent decisions**: From coordination/decision-log.md
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
✅ Use appropriate communication style  
✅ Be ready for skill-based collaboration  

---

**File version**: 1.0  
**Last updated**: October 15, 2025  
**Status**: Active initialization system