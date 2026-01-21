# 🔄 Synchronizing `molass-library` Subtree with Upstream (`joss-paper` Branch)

To keep your `molass-library` folder up-to-date with the latest changes from the upstream repository's `joss-paper` branch, follow these steps:

## 1. Add the Upstream Remote (if not already added)

```sh
git remote add molass-upstream https://github.com/biosaxs-dev/molass-library.git
```

> Only run this once. If the remote already exists, you can skip this step.

## 2. Fetch the Latest Changes from Upstream

```sh
git fetch molass-upstream
```

## 3. Pull the Latest `joss-paper` Branch into the Subtree

```sh
git subtree pull --prefix=molass-library molass-upstream joss-paper --squash
```

- If you see conflicts, resolve them by overwriting with the incoming changes (unless you have local changes you want to keep).
- After resolving, commit the changes if needed.

## 4. Verify the Update

- Check that `molass-library` now reflects the latest upstream changes.
- Run tests or review files as needed.

---

## 🚀 **IMPORTANT: Pushing Changes Back to Upstream**

### **Critical Understanding:**
The `molass-library/` folder in the **molass-review main branch** is a SUBTREE of the **original molass-library joss-paper branch**.

**Mapping:**
```
molass-review (main branch) / molass-library folder
    = SUBTREE from
original molass-library (joss-paper branch)
```

### **When You Edit Files in molass-library/**

If you edit files like `molass-library/paper.md`, you need to push those changes back to the upstream repository:

```sh
# 1. Make sure you're on the main branch of molass-review
git checkout main

# 2. Commit your changes to molass-review
git add molass-library/paper.md
git commit -m "Update paper.md: [describe your changes]"

# 3. Push the subtree changes to upstream joss-paper branch
git subtree push --prefix=molass-library molass-upstream joss-paper

# 4. Push to molass-review repository
git push origin main
```

### **⚠️ Common Mistake to Avoid:**

**DON'T** try to:
- Create a `joss-paper` branch in molass-review
- Navigate to `molass-library/` and treat it as a separate repository
- Directly push from inside the `molass-library/` folder

**DO:**
- Always work from the **molass-review main branch**
- Edit files in `molass-library/` as part of molass-review
- Use `git subtree push` to sync changes back to upstream

---

**Tip:**  
If you ever need to forcefully overwrite local changes with upstream, you can use the `--squash` option as shown above, and resolve conflicts by accepting incoming changes.
