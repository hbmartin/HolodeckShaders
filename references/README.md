# References

Preserve permissively licensed originals here with a deliberate file inventory and SHA-256 checksums. Scaffold with `python3 tools/library.py new reference`, then follow the manual reference workflow in [the shader library](../docs/shader-library.md). Validation checks original bytes without copying, staging, or rewriting them.

Existing repository shaders remain their own canonical examples. References are never delivered to the app. Sources whose license does not permit redistributing originals remain metadata-only with URL, author, license, and adaptation notes.

Each reference keeps its documentation in `reference.json`, including optional Markdown `notes` for credits, tables, and porting guidance. Read it with `python3 tools/library.py show reference <id>` or add `--json` for structured metadata and generated documentation.
