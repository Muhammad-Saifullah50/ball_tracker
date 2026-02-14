<!--
  SYNC IMPACT REPORT
  ==================
  Version change: 0.0.0 (template) -> 1.0.0
  Bump rationale: MAJOR - initial constitution replacing all template
                  placeholders with project-specific principles.

  Modified principles (template placeholder -> concrete):
    [PRINCIPLE_1_NAME] -> I. Accuracy-First
    [PRINCIPLE_2_NAME] -> II. Fairness & Transparency
    [PRINCIPLE_3_NAME] -> III. Real-Time Performance
    [PRINCIPLE_4_NAME] -> IV. Simplicity & Accessibility
    [PRINCIPLE_5_NAME] -> V. Modularity
    [PRINCIPLE_6_NAME] -> VI. Offline-First
    (new)              -> VII. Configurable Rules Engine
    (new)              -> VIII. Graceful Degradation

  Added sections:
    - Test-Driven Development (NON-NEGOTIABLE)
      - Red-Green-Refactor Cycle
      - Testing Requirements (Unit, Integration, CV Model, Decision Engine)
      - Test Coverage
      - Test Data
    - Coding Standards
      - Language & Style
      - Naming Conventions
      - Documentation
      - Code Organization
      - Error Handling
      - Version Control
      - Performance Standards
    - Data & Privacy

  Removed sections:
    - [SECTION_2_NAME] placeholder (replaced by TDD + Coding Standards)
    - [SECTION_3_NAME] placeholder (replaced by Coding Standards subsections)

  Templates requiring updates:
    - .specify/templates/plan-template.md         -> OK (no changes needed)
    - .specify/templates/spec-template.md          -> OK (no changes needed)
    - .specify/templates/tasks-template.md         -> OK (no changes needed)
    - .specify/templates/checklist-template.md     -> OK (no changes needed)
    - .specify/templates/adr-template.md           -> OK (no changes needed)
    - .claude/commands/*.md                        -> OK (no changes needed)

  Deferred items: None
-->

# Cricket Ball Tracker Constitution

## Core Principles

### I. Accuracy-First
- Ball detection accuracy is the foundation — if tracking is wrong, decisions are wrong.
- False positives (detecting wrong objects as ball) are worse than false negatives (missing a frame).
- Decision confidence scores must be transparent — never present uncertain results as definitive.
- All trajectory predictions must include margin of error.

### II. Fairness & Transparency
- Every decision must be explainable with visual evidence (trajectory overlay, impact point, predicted path).
- No "black box" decisions — players must see *why* a decision was made.
- All custom rules must be agreed upon *before* a match starts.
- The app provides evidence; players can override any automated decision.

### III. Real-Time Performance
- Ball tracking must run at minimum 30fps, ideally 60fps.
- Replay must be available within seconds of an appeal.
- Prioritize processing speed over visual polish.
- System must not introduce lag that disrupts gameplay flow.

### IV. Simplicity & Accessibility
- This is a home cricket setup, not a professional stadium.
- Minimal hardware requirements (1-2 consumer cameras).
- Easy setup — should take minutes, not hours.
- Non-technical users must be able to operate the app without training.

### V. Modularity
- Detection, tracking, decision engine, and replay are independent modules.
- Custom rules engine must be pluggable — different groups can define different rules.
- Camera configurations must be flexible and support different setups.
- Each module must have a clear interface contract.

### VI. Offline-First
- Must work without internet connection (home/backyard setting).
- All processing done locally on the user's machine.
- No cloud dependency for core features.
- Optional cloud sync for sharing replays is acceptable but never required.

### VII. Configurable Rules Engine
- LBW parameters must be adjustable (impact zone tolerance, height threshold).
- Caught behind detection sensitivity must be tunable.
- Rule presets available for different skill levels (kids, adults, competitive).
- Rules are saved per-session and can be exported/imported.

### VIII. Graceful Degradation
- If one camera fails, system continues with reduced accuracy and a clear warning.
- If tracking loses the ball, indicate uncertainty rather than guessing.
- Poor lighting or conditions trigger warnings, not wrong decisions.
- System never crashes silently — all failures are surfaced to the user.

## Test-Driven Development (NON-NEGOTIABLE)

### Red-Green-Refactor Cycle
- **Red**: Tests are written FIRST and must fail before any implementation begins.
- **Green**: Write the minimum code necessary to make the failing tests pass.
- **Refactor**: Clean up code while keeping all tests green.
- This cycle is strictly enforced for every feature and bug fix.

### Testing Requirements
- **Unit Tests**: Every function and module must have unit tests covering:
  - Happy path (expected inputs produce expected outputs)
  - Edge cases (boundary values, empty inputs, extreme values)
  - Error paths (invalid inputs, failure conditions)
- **Integration Tests**: Required for:
  - Camera feed ingestion pipeline
  - Detection-to-tracking handoff
  - Decision engine rule evaluation
  - Replay system video processing
  - Multi-module interactions
- **CV Model Validation Tests**: Ball detection and tracking models must be validated against:
  - Known ball trajectories with ground truth data
  - Different lighting conditions
  - Different ball colors and speeds
  - Occlusion scenarios
- **Decision Engine Tests**: Every rule in the decision engine must have test cases with:
  - Known input trajectories and expected outcomes (OUT/NOT OUT)
  - Edge cases near decision boundaries
  - Confidence threshold verification

### Test Coverage
- Minimum 80% code coverage for all modules.
- 100% coverage for the decision engine and rules logic.
- Coverage reports generated on every build.

### Test Data
- Maintain a curated set of test fixtures (sample frames, trajectories, match scenarios).
- Test data must be version-controlled alongside code.
- No test should depend on external resources or network access.

## Coding Standards

### Language & Style
- Python as the primary language for CV processing and backend logic.
- Follow PEP 8 strictly — enforced via linting (ruff or flake8).
- Type hints required on all function signatures.
- Maximum function length: 30 lines. If longer, refactor into smaller functions.
- Maximum file length: 300 lines. Split into modules if exceeded.

### Naming Conventions
- Variables and functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Modules and files: `snake_case`
- Names must be descriptive — no single-letter variables except loop counters.

### Documentation
- Every module must have a docstring explaining its purpose.
- Every public function must have a docstring with: description, parameters, return value, and exceptions.
- Complex algorithms (trajectory prediction, spin calculation) must have inline comments explaining the math.
- No documentation for self-explanatory code — avoid noise.

### Code Organization
- One responsibility per module — no god classes or god files.
- Dependencies flow inward: UI -> Services -> Core -> Models.
- No circular imports.
- Configuration separated from logic — use config files or environment variables.
- Secrets and tokens must never be hardcoded; use `.env` files.

### Error Handling
- Use specific exception types, not bare `except`.
- All errors must be logged with context (what was happening, what input caused it).
- User-facing errors must be human-readable.
- Internal errors must include stack traces in debug mode.
- Never swallow exceptions silently.

### Version Control
- Atomic commits — one logical change per commit.
- Descriptive commit messages following conventional commits format.
- Feature branches for all new work.
- No direct commits to main branch.
- All merges require passing tests.

### Performance Standards
- Ball detection must process frames within 33ms (30fps target).
- Replay generation must complete within 3 seconds of request.
- Memory usage must stay under 2GB during active tracking.
- No memory leaks — all resources (camera feeds, video buffers) must be properly released.

## Data & Privacy

- Video recordings stay local by default.
- No facial recognition or player identification beyond position tracking.
- Users control what gets saved and what gets deleted.
- Match data can be exported in open formats (JSON, CSV).

## Governance

- This constitution supersedes all other development practices.
- Amendments require documentation, team discussion, and explicit approval.
- All code reviews must verify compliance with these principles.
- Complexity must be justified — default to the simplest solution that works.

**Version**: 1.0.0 | **Ratified**: 2026-02-14 | **Last Amended**: 2026-02-14
