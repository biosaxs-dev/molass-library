# USER IDENTIFICATION SYSTEM

**Hybrid approach for recognizing team members**

---

## 🎯 How Copilot Identifies You

### **Method 1: Automatic Detection (Primary)**
Copilot will try to identify you from:
- **Windows username** in file paths (e.g., `c:\Users\takahashi\`)
- **Repository context** and system information
- **Previous session patterns**

### **Method 2: Explicit Confirmation (Backup)**
If unsure, Copilot will ask, or you can simply mention:
- "This is Takahashi"
- "Shimizu here"
- "Working with Shimizu today"

---

## 👥 Expected Patterns

### **Takahashi**
- **Windows path**: `c:\Users\takahashi\`
- **Likely tasks**: Technical work, programming, repository management
- **Communication style**: Technical language, code discussions

### **Shimizu**
- **Windows path**: `c:\Users\[shimizu-username]\` (TBD)
- **Likely tasks**: Scientific review, methodology questions
- **Communication style**: Non-technical, scientific focus

---

## 🔄 How This Works in Practice

### **Session Start:**
1. **Copilot checks**: Windows username and context clues
2. **Copilot assumes**: Most likely identity based on available info
3. **Copilot adjusts**: Communication style and task focus accordingly
4. **If uncertain**: Copilot asks for confirmation

### **Example:**
```
Copilot: "I see you're working from the takahashi account. Hi Takahashi! 
I'm ready to help with technical tasks. What are you working on today?"
```

**Or if uncertain:**
```
Copilot: "Hi! Could you let me know who's working today so I can 
adjust my assistance appropriately?"
```

---

## 📋 Fallback Rules

### **If Detection Fails:**
- **Default to**: Asking for identification
- **Safe assumption**: More beginner-friendly language until confirmed
- **Always confirm**: Before diving into technical details

### **For Joint Sessions:**
- **Both present**: Mention "Takahashi and Shimizu here"
- **Helping setup**: "This is Takahashi helping Shimizu get started"

---

## 🎯 Benefits

✅ **Seamless**: When detection works, no extra steps needed  
✅ **Reliable**: Fallback ensures correct identification  
✅ **Flexible**: Works for individual or joint sessions  
✅ **Safe**: Defaults to asking rather than assuming wrong  

---

## 📝 Team Notes

**Takahashi's system**: `c:\Users\takahashi\`  
**Shimizu's system**: [To be updated when known]  
**Shared systems**: [Document if any shared computers used]

---

**Created:** October 15, 2025  
**Status:** Active hybrid identification system