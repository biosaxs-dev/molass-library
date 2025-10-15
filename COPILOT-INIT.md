# COPILOT INITIALIZATION

**🤖 This file serves as Copilot's "initialization script" - MUST be manually triggered each session**

## ⚡ REQUIRED TRIGGER
**To start any session, say:** "Please read COPILOT-INIT.md to initialize"
*Note: This is required until GitHub Copilot implements automatic .copilotrc functionality*

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

## 🎯 SESSION STARTUP CHECKLIST

### **For Any User:**
1. **Detect user** from file path patterns
2. **Greet appropriately** for their skill level
3. **Reference** `CURRENT-STATUS.md` for current priorities
4. **Check** for any urgent updates or changes

### **For Takahashi:**
- Focus on technical implementation
- Offer code analysis and programming support
- Use detailed technical explanations
- Handle repository and workflow management

### **For Shimizu:**
- Focus on scientific content
- Use accessible, non-technical language
- Offer domain expertise support
- Avoid overwhelming with technical details

### **For Unknown User:**
- Ask for identification politely
- Default to beginner-friendly language
- Update this file with new user patterns

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