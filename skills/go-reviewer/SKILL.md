---
name: go-reviewer
description: Review Go code and Go tests for idiomatic style, correctness, maintainability, and usefulness.
---

# go-reviewer

Review Go source files and their tests for idiomatic Go, correctness, clarity, and usefulness.

## How to invoke

```
/go-reviewer
```

## What You Must Do

Follow these steps exactly. Do not skip steps or combine them.

### Step 1: Gather context

- Read the Go files under review, including related `_test.go` files.
- Find the package and primary API surface being changed.
- Identify the intent of each file: feature, bug fix, refactor, helper, utility, or test support.
- If tests are present, treat them as first-class code: they must be correct, readable, and valuable.

### Step 2: Review idiomatic Go usage

For production code, check:

- Naming
  - Types: `PascalCase`
  - Functions/methods/variables/constants: `camelCase` or `UPPER_SNAKE_CASE` for constants
  - Exported names should be clear and package-appropriate
- Zero values and defaults
  - Prefer zero-value initialization over explicit `new` or empty literals when safe
  - Use `var x T` for zero values when needed, not `x := T{}` if zero value suffices
- Error handling
  - Return errors early and clearly
  - Wrap context only when it adds value
  - Avoid `fmt.Errorf` without `%w` on propagated errors
- Control flow and branching
  - Keep functions short and focused
  - Prefer guard clauses and early returns over deep nesting
  - Use `switch` over long `if/else if` chains when appropriate
- Slices, maps, and loops
  - Use `for i, v := range` idiomatically
  - Avoid modifying slice length during iteration unless intentional
  - Preallocate capacity when the length is known and it matters
- Interfaces and abstractions
  - Accept interfaces, return concrete types unless abstraction is needed
  - Prefer small interfaces and keep them consumer-oriented
  - Avoid unnecessary interface plumbing or empty `interface{}` use
- Concurrency
  - Validate goroutine safety and correct channel usage
  - Avoid race-prone shared state when possible
  - Prefer `sync.Once`, `sync.Mutex`, or channels only when clearly required
- Standard library and packages
  - Prefer standard library helpers over hand-rolled equivalents when idiomatic
  - Use `errors.Is` and `errors.As` for error comparisons
  - Favor `strings.Builder` for repeated string concatenation
- Documentation and comments
  - Exported identifiers should have doc comments when public API semantics matter
  - Comments should explain why, not what
  - Remove stale or redundant comments

### Step 3: Review tests for correctness and usefulness

For Go tests, check:

- Test intent
  - Each test should exercise a behavior or edge case, not implementation details
  - Test names should describe the scenario and expected result
- Structure
  - Prefer table-driven tests for repeated cases
  - Ensure setup/teardown is minimal and easy to read
  - Avoid logic inside tests beyond what is needed to express expectations
- Assertions
  - Compare meaningful values, not just non-nil or error existence unless that is the goal
  - Use `t.Fatalf`, `t.Errorf`, and helper assertions consistently and clearly
  - Avoid brittle string matching where structured comparison is better
- Coverage
  - Check that happy path and failure paths are covered
  - Validate boundary and edge cases for inputs, nils, empty slices/maps, and invalid config
- Independence
  - Tests should not depend on external systems unless explicitly integration tests
  - Avoid global state mutation across tests
  - Ensure deterministic outcomes and stable ordering where applicable
- Usefulness
  - Flag tests that only assert that code runs without panicking if they should verify behavior
  - Flag duplicated or near-duplicate tests instead of consolidating
  - Identify missing tests for new behavior, bug fixes, or critical regression paths

### Step 4: Produce the review

- Summarize strengths first, then issues.
- Group findings by category: idiomatic Go, readability, correctness, error handling, tests.
- Give concrete suggestions, e.g.:
  - "Use `errors.Is` instead of string comparison for wrapped errors."
  - "Make this helper return a concrete type, not `io.Reader`, unless callers need the abstraction."
  - "Convert these repeated cases into a table-driven test."
- If there is no problem, say the code is idiomatic and the tests are correct and useful.

### Step 5: When not to proceed

If the file is not Go code or the tests are not Go tests, do not apply this skill. Instead, say the request is outside this skill's scope.

## Rules

- Prioritize idiomatic Go over cleverness.
- Prefer explicitness and readability over terse one-liners.
- Do not suggest broad formatting fixes; focus on correctness, style, and test quality.
- If a test uses a non-standard testing harness, ensure the review still evaluates behavior and maintainability.
- Never rewrite code unless you can point to a specific idiomatic improvement.

## Architecture

- `SKILL.md` — This file defines the skill and its invocation.
