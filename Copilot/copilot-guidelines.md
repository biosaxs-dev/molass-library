## Project Goal

The goal of this project is to make it easy for researchers—regardless of their programming experience—to maintain, improve, and contribute to the library. All guidelines and advice are designed to support both scientific users and programmers, fostering an inclusive and collaborative development environment.

## How to Start a Chat Session

Before starting a chat session, use this magic phrase:

> “Please follow the Copilot guidelines in this project for all advice and responses.”

# Copilot Guidelines (Axiomatic Draft)

1. **User Types:** Copilot distinguishes two types of persons: programmers and researchers.
2. **Programmer Guidance:** For programmers, Copilot advises mainly how to code.
3. **Researcher Guidance:** For researchers, Copilot advises mainly how to ask questions and use the library.
4. **Usage Examples:** When demonstrating how the library is used, Copilot must first refer to the test scripts in `tests/tutorial` and `tests/essence` as primary resources for practical examples and usage guidance, since these reside in the repository and reflect real usage.
	Internal usage examples in the tests folder and related external (molass) usage codes are considered equivalent and should be prioritized for usage advice, as they provide practical, user-friendly examples. If no suitable usage example exists, Copilot should then refer to internal implementation code, and only use general external resources as a last resort. This prioritization ensures advice is practical and accessible for users.
5. **Knowledge Base:** All information Copilot needs for these purposes will be stored in the "Copilot" folder (preferably as markdown texts).
6. **Contextual Replies:** Copilot replies are based on what is stored in the "Copilot" folder.
7. **Library Preference:** Copilot will always prefer and recommend solutions, code, and documentation that are part of this library (including the Copilot folder). External resources or generic advice will only be suggested if no suitable internal solution exists.
8. **Explicit Guidance:** Copilot should always follow explicit rules and documented project policies when advising users, and is expected to identify solutions or implementations that can be reused. Copilot should actively advise or propose saving such solutions in the codebase or Copilot folder for future use, to ensure consistent and predictable support.
9. **Rule Evolution:** If Copilot identifies a practice, policy, or workflow that should be formalized as a rule to improve the project, Copilot should propose a new rule or update to this file, with a clear explanation and suggested wording.
10. **Session Continuity:** After chat history is summarized or the session context changes, Copilot should automatically re-apply the Copilot guidelines and continue to follow project rules, without requiring users to restate the magic phrase.

---

## Notes
- The "Copilot" folder serves as a centralized, updatable knowledge base for both user types.
- Markdown format is recommended for clarity and ease of editing.
- Content should be periodically reviewed and expanded as needed.

## Environment Assumption

- All users are assumed to work in Visual Studio Code (VS Code) with Agent mode enabled.
- Instructions, examples, and Copilot guidance are tailored for this environment.

## Attribution

These guidelines were developed in collaboration with GitHub Copilot (GPT-4.1), which assisted in drafting, refining, and organizing the content for this project.
