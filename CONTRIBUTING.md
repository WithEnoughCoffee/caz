# Contributing to Caz

Thank you for your interest in helping Caz grow! 🌱

## Principles for Contributions

All contributions must align with Caz's core principles:

1. **Security first** — No PR should weaken the security model
2. **Truly open** — No closed-source dependencies or models
3. **Readable** — Code should be clear enough that someone learning can understand it
4. **Minimal** — Avoid adding dependencies unless absolutely necessary
5. **Tested** — New features need tests; bug fixes need regression tests

## How to Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes with clear, descriptive commits
4. Ensure tests pass
5. Submit a pull request with a clear description of what and why

## Code Style

- Clean Python with type hints
- Docstrings on all public functions
- Descriptive variable names (no abbreviations unless universally understood)
- Comments explain *why*, not *what*

## Upstream Contributions

We maintain `upstream-notes/` to track improvements we want to give back to projects Caz depends on. If you find a bug or improvement opportunity in a dependency while working on Caz:

1. Document it in `upstream-notes/`
2. If you have a fix, submit a PR to the upstream project
3. Link the upstream PR in your Caz PR

## Security Vulnerabilities

If you find a security vulnerability, please do NOT open a public issue. Email the maintainers directly.

## License

By contributing, you agree that your contributions will be licensed under Apache 2.0.
