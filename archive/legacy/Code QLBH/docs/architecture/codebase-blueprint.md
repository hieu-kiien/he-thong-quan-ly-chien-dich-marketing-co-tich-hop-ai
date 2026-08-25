# Django Codebase Blueprint

## Module principle

Each Django app is a module with a small interface and internal implementation.
Views call services for write use cases and selectors for read use cases.

## Dependency direction

```text
views/forms/templates -> services -> selectors/repositories -> models/ORM
```

Reports should read through selectors. Sales and purchases should update stock
through inventory services instead of writing inventory models directly.
