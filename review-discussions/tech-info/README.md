# Technical Information Folder

**This folder stores technical details provided by Takahashi for Shimizu's responses**

---

## 📂 **Purpose**

When Shimizu needs technical information to draft a response:
1. Shimizu marks reviewer comment with `NEEDS-TECH-INPUT`
2. Bot creates issue for Takahashi
3. Takahashi creates file HERE with technical details
4. Bot notifies Shimizu that info is ready

---

## 📝 **File Naming**

Use descriptive names that match the topic:
- `windows-compatibility.md`
- `python-38-support.md`
- `installation-macos-arm.md`
- `performance-benchmarks.md`

---

## 📋 **What to Include**

Each tech info file should have:
- **Question/Issue**: What Shimizu needs to know
- **Technical Answer**: Your detailed response
- **Feasibility**: Can we do this? Any limitations?
- **Implementation Notes**: If changes needed, what/where/how
- **Links**: Relevant code, docs, or external resources

---

## 🔄 **Workflow**

```
Shimizu: "Is Python 3.8 supported?"
   ↓
Shimizu marks comment: NEEDS-TECH-INPUT
   ↓
Bot creates issue for Takahashi
   ↓
Takahashi creates: tech-info/python-38-support.md
   ↓
Bot notifies Shimizu: "Tech info ready!"
   ↓
Shimizu uses info in response draft
```

---

**Files will appear here as technical information is provided**
