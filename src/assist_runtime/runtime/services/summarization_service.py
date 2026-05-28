"""
summarization_service.py

Hierarchical repository summarization service.

Pipeline:
    scan cache
    → importance filtering
    → file summaries      (concurrent, semaphore-limited, cached)
    → module synthesis    (concurrent, semaphore-limited)
    → repository synthesis (single call, fallback-safe)
    → RepositorySummary

Responsibilities:
    - importance filtering and ranking
    - file content reading (size-gated, truncation-safe)
    - LLM call orchestration with concurrency limits
    - JSON response parsing with graceful degradation
    - trace event emission
    - lightweight content-hash caching

NOT responsible for:
    - workflow orchestration
    - state persistence
    - artifact writing to disk
    - LLM client construction
"""

import asyncio
import hashlib
import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from assist_runtime.runtime.cache import RuntimeCache
from assist_runtime.runtime.prompt_builder import PromptBuilder
from assist_runtime.runtime.tracer import WorkflowTracer

logger = logging.getLogger("assist_runtime.runtime.services.summarization")


# ============================================================
# DOMAIN MODELS
# ============================================================


class ExposedCommand(BaseModel):
    command: str
    description: str


class ImportEntry(BaseModel):
    source: str
    symbols: list[str] = Field(default_factory=list)
    is_external: bool = False


class FileSummary(BaseModel):
    path: str
    module: str
    purpose: str
    file_type: str = "util"
    exposed_commands: list[ExposedCommand] = Field(default_factory=list)
    exports: list[str] = Field(default_factory=list)
    imports: list[ImportEntry] = Field(default_factory=list)
    env_vars: list[str] = Field(default_factory=list)
    ports: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    do_not_modify: bool = False
    notes: str = ""
    importance_score: float = 0.0


class ModuleSummary(BaseModel):
    module_name: str
    mandate: str
    entry_points: list[str] = Field(default_factory=list)
    commands: list[ExposedCommand] = Field(default_factory=list)
    env_vars: list[str] = Field(default_factory=list)
    ports: list[str] = Field(default_factory=list)
    external_dependencies: list[str] = Field(default_factory=list)
    internal_dependencies: list[str] = Field(default_factory=list)
    do_not_modify_paths: list[str] = Field(default_factory=list)
    ascii_tree: str = ""
    important_files: list[str] = Field(default_factory=list)


class RepositorySummary(BaseModel):
    total_files: int
    modules: list[ModuleSummary]
    architecture_summary: str


# ============================================================
# SUMMARIZATION SERVICE
# ============================================================


class SummarizationService:
    """
    Production-oriented hierarchical repository summarization service.

    Concurrency model:
        File summarization  : asyncio.gather + Semaphore(MAX_CONCURRENT_LLM_CALLS)
        Module summarization: asyncio.gather + Semaphore(MAX_CONCURRENT_LLM_CALLS)
        Repo synthesis      : single sequential call (all module context required first)
    """

    MAX_CONCURRENT_LLM_CALLS = 5

    # Token budget: ~12k chars/file × 100 files ≈ 1.2M chars max context input
    MAX_FILES_FOR_SUMMARIZATION = 100

    # Hard file read limits — prevents OOM on huge files
    MAX_FILE_CHARS = 12_000
    MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB

    # ----------------------------------------------------------------
    # IMPORTANCE CLASSIFICATION SETS
    # ----------------------------------------------------------------

    IMPORTANT_FILENAMES = {
        # Core entrypoints
        "main.py", "app.py", "index.ts", "index.js", "main.go", "main.rs", "app.go",
        "server.ts", "server.js", "server.py", "application.py",
        "handler.js", "handler.ts",
        # Next.js / web frameworks
        "layout.tsx", "page.tsx", "route.ts", "middleware.ts",
        # Routing & API declarations
        "routes.py", "urls.py", "router.ts", "router.js", "api.py", "endpoints.py",
        # Structural patterns & domain hubs
        "builder.py", "builder.ts", "factory.py", "factory.ts",
        "workflow.py", "workflows.py", "pipeline.py",
        "agent.py", "agents.py", "registry.py", "registry.ts",
        "service.py", "services.py", "manager.py",
        "controller.ts", "controller.js",
        "runtime.py", "engine.py", "orchestrator.py", "state.py", "machine.py",
        # Database & schema
        "models.py", "schema.prisma", "schema.ts", "schema.sql", "database.py", "db.ts",
        # CLI & task execution
        "cli.py", "cli.ts", "tasks.py", "makefile", "fabfile.py",
        # Config core
        "config.py", "config.ts", "settings.py", "constants.py", "constants.ts",
    }

    IMPORTANT_DIRECTORIES = {
        "core", "src", "app", "lib", "libs", "internal", "pkg", "kernel", "engine",
        "runtime", "workflows", "graph", "graphs", "agents", "chains", "pipelines", "state",
        "services", "service", "modules", "domains", "components", "controllers", "handlers",
        "api", "apis", "routes", "routers", "endpoints", "graphql", "rpc", "proto",
        "db", "database", "models", "repositories", "schema", "store", "memory", "cache",
        "middleware", "middlewares", "auth", "security", "config", "settings",
        "cli", "cmd", "server", "v1", "v2",
    }

    SKIP_DIRECTORIES = {
        ".git", ".github", ".gitlab", ".svn", ".hg",
        "node_modules", "bower_components", "jspm_packages",
        ".venv", "venv", "env", ".env", "virtualenv", "packages", "site-packages",
        "vendor", "third_party", "external",
        "dist", "build", "out", "target", "bin", "obj", "lib-cov",
        "public/build", ".next", ".nuxt", ".docusaurus", "public/bundles",
        "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".pydantic_cache",
        ".turbo", ".nx", ".gradle", ".cargo", ".m2",
        ".eslintcache", ".tsbuildinfo",
        "coverage", ".nyc_output", "htmlcov", "test-results", "playwright-report",
        ".docker", "terraform.tfstate.d", ".serverless",
        ".idea", ".vscode", ".settings",
    }

    SKIP_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif", ".tiff", ".bmp",
        ".mp4", ".mp3", ".wav", ".flac", ".mov", ".avi", ".wmv", ".webm",
        ".pdf", ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".figma", ".sketch", ".psd", ".ai",
        ".lock",
        ".pyc", ".pyo", ".pyd", ".class", ".o", ".obj", ".dll", ".so", ".dylib",
        ".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".bz2", ".xz",
        ".bin", ".exe", ".msi", ".app", ".apk", ".dmg", ".iso", ".jar", ".war",
        ".db", ".sqlite", ".sqlite3", ".sql.gz", ".dump",
        ".pkl", ".pickle", ".pt", ".pth", ".onnx", ".gguf", ".safetensors",
        ".min.js", ".min.css", ".map", ".chunk.js",
    }

    # Specific lock file names that don't end in .lock
    SKIP_FILENAMES = {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "Cargo.lock", "Gemfile.lock", "poetry.lock", "mix.lock", "go.sum",
    }

    # ============================================================
    # PUBLIC ENTRYPOINT
    # ============================================================

    @classmethod
    async def summarize_repository_hierarchy(
        cls,
        scan_ref_id: str,
        llm_client: Any,
        workflow_id: str,
    ) -> RepositorySummary:
        """
        Hierarchical repository summarization.

        Pipeline:
            scan cache load
            → importance filtering
            → heuristic ranking
            → concurrent file summarization (cached + semaphore-limited)
            → concurrent module synthesis
            → repository synthesis (CLAUDE.md)
        """
        scan_data = RuntimeCache.load_json(scan_ref_id)

        if not scan_data:
            raise ValueError(f"Could not load scan data from cache: {scan_ref_id}")

        file_list: list[dict[str, Any]] = scan_data.get("files", [])

        logger.info(
            "Starting repository summarization | workflow_id=%s | total_files=%d",
            workflow_id,
            len(file_list),
        )

        filtered_files = cls._filter_files(file_list)
        ranked_files = cls._rank_files(filtered_files)
        important_files = ranked_files[: cls.MAX_FILES_FOR_SUMMARIZATION]

        logger.info(
            "File selection complete | filtered=%d | ranked_cap=%d | selected=%d",
            len(filtered_files),
            len(ranked_files),
            len(important_files),
        )

        file_summaries = await cls._summarize_files(important_files, llm_client, workflow_id)

        logger.info(
            "File summarization complete | succeeded=%d / %d",
            len(file_summaries),
            len(important_files),
        )

        module_summaries = await cls._summarize_modules(file_summaries, llm_client, workflow_id)

        logger.info(
            "Module synthesis complete | modules=%d",
            len(module_summaries),
        )

        architecture_summary = await cls._synthesize_repository(
            module_summaries, llm_client, workflow_id
        )

        return RepositorySummary(
            total_files=len(file_list),
            modules=module_summaries,
            architecture_summary=architecture_summary,
        )

    # ============================================================
    # FILE FILTERING + IMPORTANCE RANKING
    # ============================================================

    @classmethod
    def _filter_files(cls, file_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Remove files that add noise without architectural signal:
        - paths inside skipped directories
        - skipped extensions
        - known lock/generated filenames
        """
        filtered = []

        for file_meta in file_list:
            path = file_meta.get("path", "")
            path_obj = Path(path)

            if any(part in cls.SKIP_DIRECTORIES for part in path_obj.parts):
                continue

            if path_obj.suffix.lower() in cls.SKIP_EXTENSIONS:
                continue

            if path_obj.name.lower() in cls.SKIP_FILENAMES:
                continue

            filtered.append(file_meta)

        return filtered

    @classmethod
    def _rank_files(cls, file_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Heuristic importance scoring. Higher score = more architecturally relevant.

        Scoring breakdown:
            +10  known entrypoint / hub filename
            +5   lives inside an important directory
            +3   primary source extension (.py, .ts, .tsx, .js, .go, .rs)
            +2   file size in the "meaty but not huge" range (1KB–50KB)
        """
        scored = []

        for file_meta in file_list:
            score = 0.0
            path_obj = Path(file_meta.get("path", ""))

            if path_obj.name.lower() in cls.IMPORTANT_FILENAMES:
                score += 10

            if any(part in cls.IMPORTANT_DIRECTORIES for part in path_obj.parts):
                score += 5

            if path_obj.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".go", ".rs"}:
                score += 3

            size = file_meta.get("size", 0)
            if 1_000 < size < 50_000:
                score += 2

            file_meta["importance_score"] = score
            scored.append(file_meta)

        scored.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

        return scored

    # ============================================================
    # FILE SUMMARIZATION
    # ============================================================

    @classmethod
    async def _summarize_files(
        cls,
        file_list: list[dict[str, Any]],
        llm_client: Any,
        workflow_id: str,
    ) -> list[FileSummary]:
        semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT_LLM_CALLS)

        tasks = [
            cls._summarize_single_file(file_meta, llm_client, semaphore, workflow_id)
            for file_meta in file_list
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        summaries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                path = file_list[i].get("path", "<unknown>")
                logger.error(
                    "File summarization task raised unhandled exception | path=%s | error=%s",
                    path,
                    str(result),
                )
            elif result is not None:
                summaries.append(result)

        return summaries

    @classmethod
    async def _summarize_single_file(
        cls,
        file_meta: dict[str, Any],
        llm_client: Any,
        semaphore: asyncio.Semaphore,
        workflow_id: str,
    ) -> FileSummary | None:
        path = file_meta.get("path", "")

        async with semaphore:
            content = await cls._read_file_safe(path)

            if not content:
                logger.debug("Skipping unreadable or empty file | path=%s", path)
                return None

            cache_key = cls._build_cache_key(path, content)
            cached = RuntimeCache.load_json(cache_key)

            if cached:
                logger.debug("Cache hit for file summary | path=%s", path)
                return FileSummary.model_validate(cached)

            module_name = cls._extract_module_name(path)
            prompt = PromptBuilder.build_file_summary_prompt(
                file_path=path,
                code_content=content,
            )

            loop = asyncio.get_running_loop()
            start = loop.time()

            try:
                response = await llm_client.generate(prompt)

                WorkflowTracer.on_llm_call(
                    workflow_id,
                    duration_ms=(loop.time() - start) * 1000,
                )

                summary = cls._parse_file_summary(
                    path=path,
                    module_name=module_name,
                    response=response,
                    importance_score=file_meta.get("importance_score", 0.0),
                )

                RuntimeCache.save_json(cache_key, summary.model_dump())

                return summary

            except Exception as exc:
                logger.exception(
                    "Failed to summarize file | path=%s | error=%s",
                    path,
                    str(exc),
                )
                return None

    # ============================================================
    # MODULE SYNTHESIS
    # ============================================================

    @classmethod
    async def _summarize_modules(
        cls,
        file_summaries: list[FileSummary],
        llm_client: Any,
        workflow_id: str,
    ) -> list[ModuleSummary]:
        grouped: dict[str, list[FileSummary]] = defaultdict(list)

        for summary in file_summaries:
            grouped[summary.module].append(summary)

        semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT_LLM_CALLS)

        tasks = [
            cls._summarize_single_module(
                module_name=module_name,
                file_summaries=summaries,
                llm_client=llm_client,
                semaphore=semaphore,
                workflow_id=workflow_id,
            )
            for module_name, summaries in grouped.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        modules = []
        for i, result in enumerate(results):
            module_names = list(grouped.keys())
            if isinstance(result, Exception):
                logger.error(
                    "Module summarization task raised unhandled exception | module=%s | error=%s",
                    module_names[i] if i < len(module_names) else "<unknown>",
                    str(result),
                )
            elif result is not None:
                modules.append(result)

        return modules

    @classmethod
    async def _summarize_single_module(
        cls,
        module_name: str,
        file_summaries: list[FileSummary],
        llm_client: Any,
        semaphore: asyncio.Semaphore,
        workflow_id: str,
    ) -> ModuleSummary | None:
        async with semaphore:
            # Build structured JSON context — do NOT pre-stringify to markdown
            file_summaries_json = cls._build_module_context_json(file_summaries)

            prompt = PromptBuilder.build_module_summary_prompt(
                module_name=module_name,
                file_summaries_json=file_summaries_json,
            )

            loop = asyncio.get_running_loop()
            start = loop.time()

            try:
                response = await llm_client.generate(prompt)

                WorkflowTracer.on_llm_call(
                    workflow_id,
                    duration_ms=(loop.time() - start) * 1000,
                )

                return cls._parse_module_summary(
                    module_name=module_name,
                    response=response,
                    file_summaries=file_summaries,
                )

            except Exception as exc:
                logger.exception(
                    "Failed to summarize module | module=%s | error=%s",
                    module_name,
                    str(exc),
                )
                return None

    # ============================================================
    # REPOSITORY SYNTHESIS
    # ============================================================

    @classmethod
    async def _synthesize_repository(
        cls,
        module_summaries: list[ModuleSummary],
        llm_client: Any,
        workflow_id: str,
    ) -> str:
        module_summaries_json = [m.model_dump() for m in module_summaries]
        prompt = PromptBuilder.build_repo_analysis_prompt(module_summaries_json)

        loop = asyncio.get_running_loop()
        start = loop.time()

        try:
            response = await llm_client.generate(prompt)

            WorkflowTracer.on_llm_call(
                workflow_id,
                duration_ms=(loop.time() - start) * 1000,
            )

            return response

        except Exception as exc:
            logger.exception(
                "Repository synthesis failed | workflow_id=%s | error=%s",
                workflow_id,
                str(exc),
            )
            # Graceful degradation: build a minimal summary from already-computed module data
            return cls._build_fallback_repo_summary(module_summaries)

    # ============================================================
    # RESPONSE PARSERS
    # ============================================================

    @staticmethod
    def _parse_json_response(response: str, context_label: str) -> dict:
        """
        Safely parse an LLM JSON response.

        Handles:
        - Bare JSON objects
        - JSON wrapped in ```json ... ``` fences
        - JSON with leading/trailing whitespace

        Returns empty dict on parse failure (caller decides how to degrade).
        """
        # Strip markdown code fences if present
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip(), flags=re.MULTILINE)

        try:
            parsed = json.loads(clean)
            if not isinstance(parsed, dict):
                raise ValueError(f"Expected JSON object, got {type(parsed).__name__}")
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "JSON parse failed | context=%s | error=%s | preview=%s",
                context_label,
                str(exc),
                clean[:200],
            )
            return {}

    @classmethod
    def _parse_file_summary(
        cls,
        path: str,
        module_name: str,
        response: str,
        importance_score: float,
    ) -> FileSummary:
        data = cls._parse_json_response(response, context_label=f"file_summary:{path}")

        raw_imports = data.get("imports", [])
        parsed_imports = []
        for imp in raw_imports:
            if isinstance(imp, dict):
                parsed_imports.append(
                    ImportEntry(
                        source=imp.get("source", ""),
                        symbols=imp.get("symbols", []),
                        is_external=imp.get("is_external", False),
                    )
                )
            elif isinstance(imp, str):
                parsed_imports.append(ImportEntry(source=imp))

        raw_commands = data.get("exposed_commands", [])
        parsed_commands = []
        for cmd in raw_commands:
            if isinstance(cmd, dict):
                parsed_commands.append(
                    ExposedCommand(
                        command=cmd.get("command", ""),
                        description=cmd.get("description", ""),
                    )
                )

        return FileSummary(
            path=path,
            module=module_name,
            purpose=data.get("purpose", response.strip()[:300]),
            file_type=data.get("file_type", "util"),
            exposed_commands=parsed_commands,
            exports=data.get("exports", []),
            imports=parsed_imports,
            env_vars=data.get("env_vars", []),
            ports=data.get("ports", []),
            side_effects=data.get("side_effects", []),
            do_not_modify=bool(data.get("do_not_modify", False)),
            notes=data.get("notes", ""),
            importance_score=importance_score,
        )

    @classmethod
    def _parse_module_summary(
        cls,
        module_name: str,
        response: str,
        file_summaries: list[FileSummary],
    ) -> ModuleSummary:
        data = cls._parse_json_response(response, context_label=f"module_summary:{module_name}")

        raw_commands = data.get("commands", [])
        parsed_commands = []
        for cmd in raw_commands:
            if isinstance(cmd, dict):
                parsed_commands.append(
                    ExposedCommand(
                        command=cmd.get("command", ""),
                        description=cmd.get("description", ""),
                    )
                )

        # Fall back to top-5 files by importance if LLM omits entry_points
        fallback_important = [
            s.path
            for s in sorted(file_summaries, key=lambda x: x.importance_score, reverse=True)[:5]
        ]

        return ModuleSummary(
            module_name=module_name,
            mandate=data.get("mandate", data.get("purpose", f"Module: {module_name}")),
            entry_points=data.get("entry_points", []),
            commands=parsed_commands,
            env_vars=data.get("env_vars", []),
            ports=data.get("ports", []),
            external_dependencies=data.get("external_dependencies", []),
            internal_dependencies=data.get("internal_dependencies", []),
            do_not_modify_paths=data.get("do_not_modify_paths", []),
            ascii_tree=data.get("ascii_tree", ""),
            important_files=data.get("entry_points", fallback_important),
        )

    # ============================================================
    # CONTEXT BUILDERS
    # ============================================================

    @staticmethod
    def _build_module_context_json(summaries: list[FileSummary]) -> list[dict]:
        """
        Serialize file summaries as structured JSON for the module prompt.

        Keeps data structured through tier 2 — avoids premature markdown
        conversion that causes irreversible information loss.
        """
        return [
            {
                "path": s.path,
                "purpose": s.purpose,
                "file_type": s.file_type,
                "exposed_commands": [c.model_dump() for c in s.exposed_commands],
                "exports": s.exports,
                "imports": [i.model_dump() for i in s.imports],
                "env_vars": s.env_vars,
                "ports": s.ports,
                "side_effects": s.side_effects,
                "do_not_modify": s.do_not_modify,
                "notes": s.notes,
                "importance_score": s.importance_score,
            }
            for s in summaries
        ]

    # ============================================================
    # FALLBACK — DEGRADED REPO SUMMARY
    # ============================================================

    @staticmethod
    def _build_fallback_repo_summary(module_summaries: list[ModuleSummary]) -> str:
        """
        Minimal markdown summary built from already-computed module data.

        Used when the LLM call in _synthesize_repository fails — ensures
        the pipeline always returns a usable RepositorySummary rather than
        crashing after all file + module work has completed.
        """
        lines = [
            "# Repository Summary",
            "",
            "> ⚠️ Full synthesis failed — this is a degraded fallback summary.",
            "",
            "## Modules",
            "",
        ]

        for module in module_summaries:
            lines.append(f"### {module.module_name}")
            lines.append(module.mandate or "_No mandate extracted._")
            lines.append("")

            if module.commands:
                lines.append("**Commands:**")
                lines.append("```bash")
                for cmd in module.commands:
                    lines.append(f"{cmd.command}  # {cmd.description}")
                lines.append("```")
                lines.append("")

            if module.important_files:
                lines.append("**Key Files:**")
                for f in module.important_files:
                    lines.append(f"- `{f}`")
                lines.append("")

        return "\n".join(lines)

    # ============================================================
    # FILE I/O HELPERS
    # ============================================================

    @classmethod
    async def _read_file_safe(cls, file_path: str) -> str | None:
        """
        Read file content with size and encoding guards.

        Returns None if:
        - file does not exist
        - file exceeds MAX_FILE_SIZE_BYTES
        - read raises an unexpected exception

        Truncates content at MAX_FILE_CHARS with an explicit marker so
        the LLM knows the file was cut rather than inferring incomplete code.
        """
        path = Path(file_path)

        if not path.exists():
            logger.debug("File not found | path=%s", file_path)
            return None

        try:
            if path.stat().st_size > cls.MAX_FILE_SIZE_BYTES:
                logger.debug(
                    "Skipping oversized file | path=%s | size=%d bytes",
                    file_path,
                    path.stat().st_size,
                )
                return None

            content = path.read_text(encoding="utf-8", errors="ignore")

            if len(content) > cls.MAX_FILE_CHARS:
                content = content[: cls.MAX_FILE_CHARS]
                content += "\n\n# [TRUNCATED — file exceeds token budget]"

            return content

        except Exception as exc:
            logger.exception(
                "Failed to read file | path=%s | error=%s",
                file_path,
                str(exc),
            )
            return None

    # ============================================================
    # MISC HELPERS
    # ============================================================

    @staticmethod
    def _extract_module_name(path: str) -> str:
        """
        Extract a depth-2 module name from the file path.

        Examples:
            "services/auth/login.py"       → "services/auth"
            "src/services/auth/login.py"   → "src/services"
            "login.py"                     → "root"
        """
        parts = Path(path).parts

        if len(parts) >= 3:
            return f"{parts[0]}/{parts[1]}"
        elif len(parts) == 2:
            return parts[0]
        else:
            return "root"

    @staticmethod
    def _build_cache_key(path: str, content: str) -> str:
        """
        Content-hash cache key — invalidates automatically when file changes.

        Format: file_summary_{sanitized_path}_{sha256[:16]}
        """
        digest = hashlib.sha256(content.encode()).hexdigest()[:16]
        safe_path = re.sub(r"[/\\]", "_", path)
        return f"file_summary_{safe_path}_{digest}"