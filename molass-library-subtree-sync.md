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

**Tip:**  
If you ever need to forcefully overwrite local changes with upstream, you can use the `--squash` option as shown above, and resolve conflicts by accepting incoming changes.
