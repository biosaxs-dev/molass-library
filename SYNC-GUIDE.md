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

### Option 1: PowerShell Script (Recommended)

```powershell
# Dry run (preview only)
.\scripts\sync-molass-library.ps1 -DryRun

# Actual sync
.\scripts\sync-molass-library.ps1
```

**Note**: If you get an execution policy error, use Option 2 instead.

### Option 2: Direct Git Commands

```bash
# Fetch latest changes
git fetch molass-upstream

# Check what's new (optional)
git log HEAD..molass-upstream/joss-paper --oneline

# Pull updates
git subtree pull --prefix=molass-library molass-upstream joss-paper --squash
```

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

If you make changes in `molass-library/` that should go back to the source repo:

```bash
# Option 1: Push subtree changes back to upstream
git subtree push --prefix=molass-library molass-upstream joss-paper

# Option 2: Work directly in the molass-library repo
# (Navigate to separate clone of biosaxs-dev/molass-library)
```

**Best Practice**: For significant development work, use a separate clone of molass-library. Use the subtree here for reference and small fixes.

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

**Error**: "execution of scripts is disabled"

**Solution**: Use direct git commands (Option 2) or enable scripts:
```powershell
# One-time: Allow scripts for current user (requires admin)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

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
