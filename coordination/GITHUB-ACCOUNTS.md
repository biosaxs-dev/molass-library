# GitHub Account Configuration

**Purpose**: Document GitHub account IDs for bot automation and mentions

---

## 👥 Team GitHub Accounts

### **Takahashi (Programmer)**
- **GitHub Username**: `freesemt`
- **Used in**: Bot assignees, issue assignments
- **Confirmed**: ✅ October 16, 2025

### **Shimizu (Domain Expert)**
- **GitHub Username**: `[TO_BE_UPDATED]`
- **Used in**: Bot mentions, notifications
- **Status**: ⚠️ Pending - Shimizu is considering renaming account

---

## 🔧 Where These Are Used

### **In Bot Workflow** (`.github/workflows/collaboration-bot.yml`)
- **Line 82**: `assignees: ['freesemt']` - Technical input requests
- **Line 166**: `assignees: ['freesemt']` - Draft review requests
- **Line 217**: `@shimizu` - Tech info completion notifications
- **Line 282**: `@shimizu` - Review completion notifications

### **Manual Updates Needed When Shimizu's Account is Confirmed:**
1. Update this file with Shimizu's GitHub username
2. Update bot workflow mentions from `@shimizu` to `@[actual_username]`
3. Test bot notifications

---

## 📝 How to Update

### **Step 1: When Shimizu Confirms Username**
Tell Copilot:
```
Shimizu's GitHub username is [username]
```

### **Step 2: Copilot Will Update**
- This configuration file
- Bot workflow mentions
- Any other references

### **Step 3: Test**
- Create a test file with marker
- Verify bot creates issue
- Verify mentions work correctly

---

## 🆘 Current Workaround

**Until Shimizu's account is confirmed:**
- Bot will mention `@shimizu` (won't notify anyone)
- Takahashi will need to manually notify Shimizu
- Issues will still be created correctly
- Functionality mostly works, just notifications incomplete

**This is OK for now** - the private repo means only you two will see these mentions anyway.

---

## 📌 Notes

- **Repository Owner**: `freesemt` (Takahashi)
- **Repository Name**: `molass-review`
- **Organization**: None (personal repository)
- **Visibility**: Private

---

**Last Updated**: October 16, 2025  
**Next Update**: When Shimizu confirms GitHub username
