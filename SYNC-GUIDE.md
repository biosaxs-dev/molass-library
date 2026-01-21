# 🔄 Synchronization Guide

**Automatic synchronization is now integrated into Takahashi's initialization process!**

---

## 🚀 Quick Start: Automatic Sync (Takahashi Only)

**Note**: This synchronization process is **only for Takahashi**. Shimizu doesn't need to manage the molass-library subtree.

Every time Takahashi initializes Copilot, synchronization happens automatically:

```
Please read COPILOT-INIT.md to initialize
```

Copilot will:
1. ✅ Sync molass-library subtree with joss-paper branch
2. ✅ Check JOSS review issue for new comments
3. ✅ Report status changes
4. ✅ Alert you to any actionable items

**You don't need to do anything manually!**

---

## 📦 What Gets Synchronized

### 1. molass-library Subtree
- **Source**: biosaxs-dev/molass-library (joss-paper branch)
- **Destination**: molass-library/ folder in this repo
- **Method**: git subtree pull (squashed)
- **Frequency**: Every initialization

### 2. JOSS Review Issue
- **Source**: openjournals/joss-reviews#9424
- **What's checked**: New reviewer/editor comments
- **Action**: Alert if actionable comments found
- **Frequency**: Every initialization

---

## 🛠️ Manual Synchronization (If Needed)

### Option 1: Direct Git Commands (Always Works) ⭐

This is the most reliable method and works on all systems:

```powershell
# Fetch latest changes
git fetch molass-upstream

# Check what's new (optional)
git log HEAD..molass-upstream/joss-paper --oneline

# Pull updates
git subtree pull --prefix=molass-library molass-upstream joss-paper --squash
```

**Recommended**: Use these commands directly. They're simple and always work.

### Option 2: PowerShell Script (Optional Convenience)

The script provides nice formatting and error checking, but requires PowerShell execution policy setup:

```powershell
# Dry run (preview only)
.\scripts\sync-molass-library.ps1 -DryRun

# Actual sync
.\scripts\sync-molass-library.ps1
```

**⚠️ PowerShell Execution Policy Issue**

If you get an error like:
```
このシステムではスクリプトの実行が無効になっているため...
(Script execution is disabled on this system...)
```

You have 3 choices:

**A) Use Option 1 instead** (easiest - just use git commands)

**B) Enable execution policy** (one-time setup):
```powershell
# Requires administrator rights
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**C) Bypass policy for this script only**:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-molass-library.ps1
```

**Note**: Copilot's automatic sync uses git commands directly (Option 1), so it's not affected by execution policy.

---

## 🔍 Understanding the Sync Process

### Git Subtree Basics

The `molass-library/` folder is a **subtree**, not a submodule:

- ✅ **Pros**: 
  - Files are part of this repo (no separate clone needed)
  - Simpler for most workflows
  - Can make changes here and push back to source

- ⚠️ **Important**:
  - Changes in this repo need manual sync with source
  - Must use git subtree commands (not regular git pull)

### Remote Configuration

The remote `molass-upstream` points to:
```
https://github.com/biosaxs-dev/molass-library.git
```

This is automatically configured. You can verify with:
```bash
git remote -v | Select-String "molass"
```

---

## 📊 Sync Status Indicators

After initialization, Copilot reports:

### ✅ Up-to-date
```
✅ molass-library is already up-to-date!
   No synchronization needed.
```

### 🔄 Updates Applied
```
✅ Synchronization completed successfully!
   molass-library has been updated with latest changes from joss-paper branch.
   
   Changes:
   - 16 files changed
   - 4945 insertions
```

### ⚠️ Conflicts Detected
```
⚠️  Synchronization encountered conflicts.
   Please resolve conflicts manually and commit.
```

---

## 🔄 Workflow Integration

### Typical Session Flow

1. **Open VS Code**
2. **Say**: "Please read COPILOT-INIT.md to initialize"
3. **Copilot does**:
   - Syncs molass-library subtree ← **Automatic!**
   - Checks JOSS review for updates ← **Automatic!**
   - Reports current status ← **Automatic!**
4. **You continue** with your work on synchronized code

---

## 📝 When to Push Changes Back to molass-library

### **⚠️ CRITICAL: Understanding the Subtree Mapping**

```
molass-review (main branch) / molass-library folder
    = SUBTREE from
original molass-library (joss-paper branch)
```

**This means**: When you edit files in `molass-library/` (like `paper.md`), you're editing the **main branch of molass-review**, NOT a separate joss-paper branch!

### **Correct Workflow for Pushing Changes:**

If you make changes in `molass-library/` that should go back to the source repo:

```bash
# 1. Make sure you're on the main branch of molass-review
git checkout main

# 2. Edit files in molass-library/ as normal
# (e.g., molass-library/paper.md)

# 3. Commit your changes to molass-review
git add molass-library/paper.md
git commit -m "Update paper.md: [describe changes]"

# 4. Push subtree changes to upstream joss-paper branch
git subtree push --prefix=molass-library molass-upstream joss-paper

# 5. Push to molass-review repository
git push origin main
```

### **❌ Common Mistakes to AVOID:**

1. **DON'T** create a `joss-paper` branch in molass-review
2. **DON'T** try to `cd molass-library/` and treat it as a separate git repository
3. **DON'T** try to push from inside the `molass-library/` folder directly

### **✅ Correct Approach:**

- Always work from the **molass-review main branch**
- Edit files in `molass-library/` as part of this repository
- Use `git subtree push` to sync changes to upstream
- The subtree system handles the branch mapping automatically

**Best Practice**: For paper edits (paper.md, paper.bib), use this subtree workflow. For significant code development, you may also work directly in a separate clone of molass-library.

---

## 🆘 Troubleshooting

### Problem: "working tree has modifications"

**Solution**: Commit your changes first
```bash
git add .
git commit -m "Your commit message"
# Then retry sync
git subtree pull --prefix=molass-library molass-upstream joss-paper --squash
```

### Problem: Merge conflicts during sync

**Solution**: Resolve conflicts manually
```bash
# After conflict appears:
# 1. Edit conflicted files
# 2. Mark as resolved
git add molass-library/
git commit -m "Merge molass-library updates"
```

### Problem: "remote molass-upstream does not exist"

**Solution**: Add the remote
```bash
git remote add molass-upstream https://github.com/biosaxs-dev/molass-library.git
```

### Problem: PowerShell script won't run

**Error**: "このシステムではスクリプトの実行が無効になっている" or "execution of scripts is disabled"

**Why**: Windows PowerShell execution policy blocks `.ps1` scripts by default for security.

**Solutions** (pick one):

**1. Use git commands directly** (easiest, always works):
```powershell
git fetch molass-upstream
git subtree pull --prefix=molass-library molass-upstream joss-paper --squash
```

**2. Enable execution policy** (one-time, requires admin):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**3. Bypass for this script only**:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync-molass-library.ps1
```

**Important**: The script is optional. Copilot's automatic sync uses git commands directly and is not affected by this issue.

---

## 📋 Verification Checklist

After synchronization, verify:

- [ ] molass-library folder exists
- [ ] No git conflicts remain
- [ ] All files are committed
- [ ] `git status` shows clean working tree
- [ ] Latest changes from joss-paper branch are visible

---

## 🎯 Benefits of Automatic Sync (For Takahashi)

### Before (Manual Process):
1. Remember to check for updates
2. Run multiple git commands
3. Handle merge conflicts
4. Forget to sync = work on outdated code

### After (Automatic Process):
1. Say "Please read COPILOT-INIT.md to initialize"
2. Everything syncs automatically (Takahashi only)
3. Always working with latest code
4. Zero mental overhead

**Why Takahashi only?**: Takahashi is responsible for code implementation and repository management, so he needs the latest molass-library code. Shimizu focuses on responses and scientific content, so he doesn't need to manage the subtree.

---

## 📚 Related Documentation

- **Setup**: [molass-library-subtree-sync.md](molass-library-subtree-sync.md) - Original setup guide
- **Workflow**: [COPILOT-INIT-ACTION.md](COPILOT-INIT-ACTION.md) - What happens at initialization
- **Quick Start**: [TAKAHASHI-QUICK-START.md](TAKAHASHI-QUICK-START.md) - Your main guide

---

**Last Updated**: December 25, 2025  
**Status**: Active - Automatic sync enabled  
**Next Review**: After first real JOSS review session
