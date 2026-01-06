# Anticipated JOSS Review Questions

**Purpose**: Proactive preparation for upcoming JOSS review  
**Created**: December 16, 2025  
**Updated**: December 16, 2025 (after analyzing 5 similar JOSS reviews)  
**Status**: Pre-review preparation  

**Based on actual reviews of similar papers**:
- PeakPerformance (#7313) - LC-MS/MS chromatography peak fitting
- hplc-py (#6270) - HPLC chromatography analysis
- DebyeCalculator (#6024) - Small-angle scattering (SAXS-related)
- idpflex (#1007) - SAXS for disordered proteins (2018 - older review format)
- CADET-Core (#7881) - Chromatography simulation (C++ project)

---

## 1. Software Functionality & Scope

### Q1.1: Coverage of SEC-SAXS Workflow
**Question**: The paper states that Molass Library implements steps 3-7 of the 8-step SEC-SAXS workflow. Why were steps 1-2 and 8 excluded? Could these be integrated in the future?

**Answer**: The exclusions resulted from historical reasons. Molass Library is a rewite of MOLASS (the GUI-style predecessor), which was conceived to supplement the poorly cared parts of the tool chain. Expecially,
- for steps 1-2, we already had SAngler;
- for step 8, established ATSAS tools existed and DENSS joined later.

In the near future, we have no integration plan with our tight budget for those excluded steps.

### Q1.2: Comparison with Existing Tools
**Question**: The paper mentions ATSAS and BioXTAS RAW as alternatives. Can you provide a more detailed comparison of features, particularly:
- What specific functionality does Molass Library provide that these tools lack?
- In what scenarios would a user choose Molass Library over these established tools?
- Are there any benchmark comparisons available?

**Answer**: 

### Q1.3: Low-Rank Factorization Implementation
**Question**: The paper describes low-rank factorization as a "central feature." How does your implementation compare to standard matrix factorization methods in scipy or scikit-learn? What makes your approach specialized for SEC-SAXS?

### Q1.4: Elution Curve Models
**Question**: Three elution curve models are mentioned (EGH, SDM, EDM). How does a user choose between these models? Are there guidelines or automated model selection?

---

## 2. Installation & Dependencies

### Q2.1: Python Version Support
**Question**: The pyproject.toml specifies `requires-python = ">=3.12,<3.14"`. 
- Why is Python 3.14 excluded?
- Is Python 3.8 support planned (it's still widely used)?
- Are there specific dependency constraints preventing broader support?

### Q2.2: Dependency on molass_legacy
**Question**: There's a dependency on `molass_legacy>=0.3.2`. What functionality is provided by this legacy package? Is there a plan to eliminate this dependency?

### Q2.3: Platform Support
**Question**: README mentions testing on Windows 11 and Ubuntu 22.04. What about:
- macOS support?
- Other Linux distributions?
- Python 3.9, 3.10, 3.11 testing (only 3.12 mentioned)?

### Q2.4: Optional Dependencies
**Question**: The `excel` extra requires `pywin32` (Windows-only). How critical is this feature? Are there alternatives for non-Windows users?

---

## 3. Documentation

### Q3.1: Documentation Structure
**Question**: Four separate documentation sites are mentioned (Tutorial, Essence, Technical, Reference). Why this separation? Could this be confusing for new users?

### Q3.2: API Documentation
**Question**: Is the API fully documented with docstrings? Are there auto-generated API docs (e.g., using Sphinx)?

### Q3.3: Installation Instructions
**Question**: Are there detailed installation instructions for different platforms? What about troubleshooting common installation issues?

### Q3.4: Example Data
**Question**: Are example datasets provided for users to test the software? Where can users find real SEC-SAXS data to practice with?

### Q3.5: Contribution Guidelines
**Question**: Are there contribution guidelines (CONTRIBUTING.md)? How can the community contribute to the project?

---

## 4. Testing

### Q4.1: Test Coverage
**Question**: What is the test coverage percentage? Are there continuous integration tests?

### Q4.2: Testing Strategy
**Question**: The pyproject.toml shows pytest configuration. What types of tests are included:
- Unit tests?
- Integration tests?
- Validation against known results?
- Cross-platform tests?

### Q4.3: CI/CD Setup
**Question**: Is there a GitHub Actions workflow or other CI system? What Python versions and platforms are tested automatically?

### Q4.4: Validation Studies
**Question**: Have you validated the software against published SEC-SAXS datasets with known results? Can you provide examples?

---

## 5. Community & Sustainability

### Q5.1: Community Building
**Question**: README mentions a "Molass Community." How large is the user base? Are there any publications using this software?

### Q5.2: Issue Tracking
**Question**: How are bugs and feature requests tracked? Is the GitHub issue tracker actively monitored?

### Q5.3: Release Process
**Question**: Current version is 0.7.2. What's the versioning scheme? What's the roadmap to version 1.0?

### Q5.4: Maintenance Plan
**Question**: Who maintains the project? Is there institutional support? What's the long-term sustainability plan?

---

## 6. Research Context

### Q6.1: Novel Contributions
**Question**: Beyond being a rewrite with better tooling, what are the novel algorithmic or methodological contributions compared to the original MOLASS?

### Q6.2: Scientific Validation
**Question**: Are there research papers or case studies demonstrating the use of Molass Library? How has it been validated scientifically?

### Q6.3: Interparticle Interference
**Question**: The paper mentions "interparticle interference effects can be separated by adding row vectors based on quadratic approximation." Can you provide more detail or references for this method?

### Q6.4: Real-World Applications
**Question**: What real-world research problems has Molass Library solved? Can you provide specific use cases or success stories?

---

## 7. Code Quality & Repository

### Q7.1: Code Organization
**Question**: How is the codebase structured? Is it modular? Are there clear separation of concerns?

### Q7.2: Error Handling
**Question**: How does the software handle common errors (e.g., invalid input data, missing files, convergence failures)?

### Q7.3: Logging & Debugging
**Question**: Are there logging capabilities for debugging complex workflows? Can users enable verbose output?

### Q7.4: Performance
**Question**: Have you done any performance profiling? Are there known bottlenecks? How does it scale with large datasets?

### Q7.5: Repository Cleanliness
**Question**: Are there any issues with:
- Large binary files in git history?
- Missing .gitignore entries?
- Outdated or unclear documentation files?

---

## 8. Reproducibility

### Q8.1: Script Reproducibility
**Question**: How do you ensure analyses are reproducible? Can workflows be saved and re-executed?

### Q8.2: Version Pinning
**Question**: Should users pin specific versions of dependencies for reproducibility? Are there known compatibility issues with newer dependency versions?

### Q8.3: Environment Management
**Question**: Do you recommend using conda or venv? Are there environment.yml or requirements.txt files for reproducibility?

---

## 9. Licensing & Attribution

### Q9.1: License Clarity
**Question**: The license is GPL-3.0. Are all dependencies compatible with this license?

### Q9.2: Citation
**Question**: How should users cite Molass Library? Is there a CITATION.cff file?

### Q9.3: Third-Party Code
**Question**: Are there any third-party code snippets or algorithms? Are they properly attributed?

---

## 10. Paper-Specific Questions

### Q10.1: Statement of Need
**Question**: The statement of need could be stronger. Can you elaborate on specific limitations of existing tools that Molass Library addresses?

### Q10.2: Figure Quality
**Question**: Are the figures in the paper high-resolution and clear? Do they effectively illustrate the concepts?

### Q10.3: References
**Question**: Are all software tools and methods properly cited? Are DOIs correct?

### Q10.4: Mathematical Notation
**Question**: Equations (1) and (2) describe the factorization. Are these implementations of standard methods or novel formulations?

---

## 11. Technical Implementation Details

### Q11.1: Moore-Penrose Pseudoinverse
**Question**: Which implementation of the pseudoinverse do you use (numpy.linalg.pinv, scipy.linalg.pinv)? Have you considered numerical stability issues?

### Q11.2: Peak Detection
**Question**: You use `scipy.signal.find_peaks` for peak recognition. Are there customization options or parameter tuning guidance for users?

### Q11.3: Change Point Detection
**Question**: The ruptures package is used for change point detection. How is this integrated into the SEC-SAXS workflow?

### Q11.4: Baseline Correction
**Question**: Multiple baseline correction algorithms are available in pybaselines. Which ones are exposed to users? How do users select the appropriate method?

---

## 12. User Experience

### Q12.1: Learning Curve
**Question**: For users unfamiliar with SEC-SAXS, how steep is the learning curve? Are there guided tutorials?

### Q12.2: GUI vs. Scripting
**Question**: The shift from GUI to Jupyter notebooks is noted. Is there any interactive visualization for users who prefer visual interfaces?

### Q12.3: Error Messages
**Question**: Are error messages user-friendly and informative? Do they guide users toward solutions?

### Q12.4: Workflow Examples
**Question**: Are there complete workflow examples from raw data to final results in the documentation?

---

## Priority Assessment

### **CRITICAL** (Based on actual reviews - WILL be checked):
1. **Installation & Dependencies**
   - Q2.1 (Python version support) - Missing license was caught in hplc-py review
   - Q2.2 (molass_legacy dependency) - Reviewers WILL ask about this
   - Q2.3 (Platform/Python version testing) - Only 3.12 mentioned, not 3.9-3.11

2. **Documentation**
   - Q3.2 (API documentation) - Always checked by reviewers
   - Q3.4 (Example data & running examples) - hplc-py had crysol path issues, idpflex too
   - Q3.5 (Contribution guidelines) - Standard JOSS checklist item

3. **Testing**
   - Q4.1 (Test coverage) - Always verified
   - Q4.3 (CI/CD) - Reviewers run tests themselves
   - Q4.4 (Validation against known results) - Critical for scientific software

4. **Statement of Need**
   - Q10.1 (Statement of need strength) - idpflex was asked to add this to docs
   - Must be in BOTH paper AND documentation (idpflex experience)

### **HIGH Priority** (Based on actual reviews - LIKELY to be asked):
- Q1.2 (Comparison with ATSAS/BioXTAS RAW) - Always requested for similar tools
- Q1.4 (Elution curve model selection guidance) - Technical detail reviewers want
- Q6.2 (Scientific validation with real data) - Core requirement
- Q7.1 (Code organization/modularity) - Reviewers examine repository structure
- Q9.1 (License compatibility) - License check is automated by editorialbot
- Q9.2 (CITATION.cff file) - Now requested after acceptance in recent reviews

### **MEDIUM Priority** (May be asked):
- Q1.3 (Low-rank factorization implementation details)
- Q3.1 (Documentation structure - 4 separate sites)
- Q7.4 (Performance/scaling)
- Q8.2 (Version pinning for reproducibility)
- Q11.1-11.4 (Technical implementation details)

### **LOWER Priority** (Unlikely unless obvious issues):
- Q2.4 (Excel feature - Windows only)
- Q7.3 (Logging capabilities)
- Q12.2 (GUI vs. scripting discussion)

---

## Key Insights from Similar Reviews

### **Pattern 1: Installation Issues Are Common**
- **hplc-py**: Missing LICENSE file caught by editorialbot
- **idpflex**: Example notebooks had path issues (FileNotFoundError for external tool)
- **Lesson**: Test installation on clean system, verify all examples run

### **Pattern 2: Statement of Need Must Be Everywhere**
- **idpflex**: Had statement in paper but reviewers requested it in docs too
- **PeakPerformance**: Enhanced README based on reviewer feedback
- **Lesson**: Include statement of need in README, docs, AND paper

### **Pattern 3: Example Data Is Critical**
- **idpflex**: Had to fetch external tool output when tool not installed
- **DebyeCalculator**: Reviewers tested examples extensively
- **Lesson**: Provide complete, self-contained examples with data

### **Pattern 4: License & Citation Files Now Expected**
- **Recent reviews**: All request CITATION.cff file after acceptance
- **Lesson**: Prepare CITATION.cff file in advance

### **Pattern 5: Reviewers WILL Test Your Software**
- All reviews show reviewers actually installing and running the code
- **Lesson**: Assume reviewers will follow installation instructions exactly

### **Pattern 6: Version Numbers Must Match**
- **idpflex**: Reviewer caught version mismatch (0.1.6 vs 0.1.5)
- **Lesson**: Verify version consistency across paper.md, README, pyproject.toml

---

## Action Items Before Review Starts

### **Must Fix Now:**
1. ✅ Verify version number consistency (currently 0.7.2 in pyproject.toml)
2. ❓ Test examples on clean Python 3.9, 3.10, 3.11, 3.12 environments
3. ❓ Add statement of need to README.md (currently only in paper.md)
4. ❓ Create CITATION.cff file
5. ❓ Verify molass_legacy dependency is properly documented
6. ❓ Test all tutorial notebooks run without errors

### **Should Prepare:**
1. Document why Python 3.13 is excluded
2. Prepare comparison table with ATSAS and BioXTAS RAW
3. Document platform testing matrix
4. Prepare validation examples against known SEC-SAXS results
5. Review API documentation completeness

### **Nice to Have:**
1. Contribution guidelines (CONTRIBUTING.md)
2. Example dataset repository
3. Performance benchmarks
4. Troubleshooting guide

---

## Notes for Preparation

1. **Quick wins**: Questions that can be answered with existing documentation or simple code checks
2. **Requires work**: Questions that may need code changes, additional docs, or new examples
3. **Strategic**: Questions that need careful thought about project positioning and future direction

**Next Steps**:
1. Takahashi attempts to answer these questions
2. Identify gaps that need documentation or code improvements
3. Implement "Must Fix Now" items before review starts
4. Draft responses for Shimizu to review
5. Create tech-info files for complex technical answers
