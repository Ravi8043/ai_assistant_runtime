import asyncio
import hashlib
import json
import logging
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


class FileSummary(BaseModel):
    path: str
    module: str
    purpose: str
    exports: list[str] = Field(default_factory=list)
    env_vars: list[str] = Field(default_factory=list)
    commands: list[dict[str, str]] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    importance_score: float = 0.0


class ModuleSummary(BaseModel):
    module_name: str
    purpose: str
    responsibilities: list[str] = Field(default_factory=list)
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

    Responsibilities:
    - importance filtering
    - file summarization
    - module synthesis
    - repository synthesis
    - concurrency limiting
    - tracing integration
    - lightweight caching

    NOT responsible for:
    - workflow orchestration
    - state management
    - artifact writing
    """

    MAX_CONCURRENT_LLM_CALLS = 5
    MAX_FILE_CHARS = 12000
    MAX_FILE_SIZE_BYTES = 512 * 1024

    # Most critical entrypoints, orchestrators, and architectural hubs across stacks
    IMPORTANT_FILENAMES = {
        # Core Entrypoints & Apps
        "main.py", "app.py", "index.ts", "index.js", "main.go", "main.rs", "app.go",
        "server.ts", "server.js", "server.py", "application.py", "handler.js", "handler.ts",
        
        # Web Frameworks / Next.js Entrypoints
        "layout.tsx", "page.tsx", "route.ts", "middleware.ts",
        
        # Routing & API Declarations
        "routes.py", "urls.py", "router.ts", "router.js", "api.py", "endpoints.py",
        
        # Structural Patterns & Domain Hubs
        "builder.py", "builder.ts", "factory.py", "factory.ts",
        "workflow.py", "workflows.py", "pipeline.py", "agent.py", "agents.py",
        "registry.py", "registry.ts", "hub.py",
        "service.py", "services.py", "manager.py", "controller.ts", "controller.js",
        "runtime.py", "engine.py", "orchestrator.py", "state.py", "machine.py",
        
        # Database Core & Schemas
        "models.py", "schema.prisma", "schema.ts", "schema.sql", "database.py", "db.ts",
        
        # CLI & Task Execution
        "cli.py", "cli.ts", "tasks.py", "makefile", "fabfile.py",
        
        # Configuration Core (Excluding heavy data/lock files)
        "config.py", "config.ts", "settings.py", "constants.py", "constants.ts"
    }

    # Core architectural folders where the business logic or system engine lives
    IMPORTANT_DIRECTORIES = {
        # System Core & Brain
        "core", "src", "app", "lib", "libs", "internal", "pkg", "kernel", "engine",
        
        # Orchestration, Graphs, & Agents
        "runtime", "workflows", "graph", "graphs", "agents", "chains", "pipelines", "state",
        
        # Business Logic & Infrastructure
        "services", "service", "modules", "domains", "components", "controllers", "handlers",
        
        # API, Protocols, & Contracts
        "api", "apis", "routes", "routers", "endpoints", "graphql", "rpc", "proto",
        
        # Storage, Caching, & State
        "db", "database", "models", "repositories", "schema", "store", "memory", "cache",
        
        # Operations, Access Control, & Security
        "middleware", "middlewares", "auth", "security", "config", "settings",
        
        # Client Interface / Delivery Mechanisms
        "cli", "cmd", "server", "v1", "v2"
    }

    # Directories containing third-party code, auto-generated builds, cache noise, or data dumps
    SKIP_DIRECTORIES = {
        # Version Control System internals
        ".git", ".github", ".gitlab", ".svn", ".hg",
        
        # Package Manager / Third-Party Dependency Nodes
        "node_modules", "bower_components", "jspm_packages",
        ".venv", "venv", "env", ".env", "virtualenv", "packages", "site-packages",
        "vendor", "third_party", "external",
        
        # Build Targets, Distribution Outputs, & Compiled Bundles
        "dist", "build", "out", "target", "bin", "obj", "lib-cov", 
        "public/build", ".next", ".nuxt", ".docusaurus", "public/bundles",
        
        # Language & Testing Caches
        "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".pydantic_cache",
        ".turbo", ".nx", ".gradle", ".cargo", ".m2", "GlowCaches",
        ".eslintcache", ".tsbuildinfo", 
        
        # Test Coverage & Report Dumps
        "coverage", ".nyc_output", "htmlcov", "test-results", "playwright-report",
        
        # Container / DevOps Engine Internals
        ".docker", "terraform.tfstate.d", ".serverless",
        
        # Local IDE Settings (Optional, but keeps things high-level code focused)
        ".idea", ".vscode", ".settings"
    }

    # Extensions for raw binary assets, compiled files, system locks, or heavy media formats
    SKIP_EXTENSIONS = {
        # Heavy Media & Graphic Formats
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif", ".tiff", ".bmp",
        ".mp4", ".mp3", ".wav", ".flac", ".mov", ".avi", ".wmv", ".webm",
        
        # Document & Static Design Formats
        ".pdf", ".docx", ".xlsx", ".pptx", ".odt", ".ods", ".figma", ".sketch", ".psd", ".ai",
        
        # Dependency & Version Locking Configurations
        ".lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock", "Gemfile.lock",
        "poetry.lock", "mix.lock", "go.sum",
        
        # Compiled Bytecode & Compressed Archive Bundles
        ".pyc", ".pyo", ".pyd", ".class", ".o", ".obj", ".dll", ".so", ".dylib",
        ".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".bz2", ".xz",
        
        # Executables & Production Hard Binaries
        ".bin", ".exe", ".msi", ".app", ".apk", ".dmg", ".iso", ".jar", ".war",
        
        # Database Dumps / Big Machine Learning Model Weights
        ".db", ".sqlite", ".sqlite3", ".sql.gz", ".dump", 
        ".pkl", ".pickle", ".pt", ".pth", ".onnx", ".gguf", ".safetensors",
        
        # Minified / Transpiled Frontend Assets
        ".min.js", ".min.css", ".map", ".chunk.js"
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
        scan
        → importance filtering
        → file summaries
        → module summaries
        → repository synthesis
        """

        scan_data = RuntimeCache.load_json(scan_ref_id)

        if not scan_data:
            raise ValueError(
                f"Could not load scan data from cache: {scan_ref_id}"
            )

        file_list = scan_data.get("files", [])

        logger.info(
            "Starting repository summarization | workflow_id=%s | files=%s",
            workflow_id,
            len(file_list),
        )

        filtered_files = cls._filter_files(file_list)

        ranked_files = cls._rank_files(filtered_files)

        important_files = ranked_files[:100]

        logger.info(
            "Selected important files for semantic analysis | count=%s",
            len(important_files),
        )

        file_summaries = await cls._summarize_files(
            important_files,
            llm_client,
            workflow_id,
        )

        module_summaries = await cls._summarize_modules(
            file_summaries,
            llm_client,
            workflow_id,
        )

        architecture_summary = await cls._synthesize_repository(
            module_summaries,
            llm_client,
            workflow_id,
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
    def _filter_files(
        cls,
        file_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove noisy/unimportant files before semantic analysis."""

        filtered = []

        for file_meta in file_list:
            path = file_meta.get("path", "")

            path_obj = Path(path)

            if any(part in cls.SKIP_DIRECTORIES for part in path_obj.parts):
                continue

            if path_obj.suffix.lower() in cls.SKIP_EXTENSIONS:
                continue

            filtered.append(file_meta)

        return filtered

    @classmethod
    def _rank_files(
        cls,
        file_list: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Heuristic importance ranking.

        Prevents:
        - summarizing every tiny utility file
        - excessive token costs
        - noisy architecture summaries
        """

        ranked = []

        for file_meta in file_list:
            score = 0.0

            path = file_meta.get("path", "")
            path_obj = Path(path)

            filename = path_obj.name

            if filename in cls.IMPORTANT_FILENAMES:
                score += 10

            if any(
                part in cls.IMPORTANT_DIRECTORIES
                for part in path_obj.parts
            ):
                score += 5

            ext = path_obj.suffix.lower()

            if ext in {".py", ".ts", ".tsx", ".js", ".go", ".rs"}:
                score += 3

            size = file_meta.get("size", 0)

            if 1000 < size < 50000:
                score += 2

            file_meta["importance_score"] = score
            ranked.append(file_meta)

        ranked.sort(
            key=lambda x: x.get("importance_score", 0),
            reverse=True,
        )

        return ranked

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
            cls._summarize_single_file(
                file_meta,
                llm_client,
                semaphore,
                workflow_id,
            )
            for file_meta in file_list
        ]

        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    @classmethod
    async def _summarize_single_file(
        cls,
        file_meta: dict[str, Any],
        llm_client: Any,
        semaphore: asyncio.Semaphore,
        workflow_id: str,
    ) -> FileSummary | None:
        path = file_meta.get("path", "")
        abs_path = file_meta.get("absolute_path", path)

        async with semaphore:
            content = await cls._read_file_safe(abs_path)

            if not content:
                return None

            cache_key = cls._build_cache_key(path, content)

            cached_summary = RuntimeCache.load_json(cache_key)

            if cached_summary:
                return FileSummary.model_validate(cached_summary)

            module_name = cls._extract_module_name(path)

            prompt = PromptBuilder.build_file_summary_prompt(
                file_path=path,
                code_content=content,
            )

            start_time = asyncio.get_event_loop().time()

            try:
                response = await cls._generate_with_retry(llm_client, prompt)

                duration_ms = (
                    asyncio.get_event_loop().time() - start_time
                ) * 1000

                WorkflowTracer.on_llm_call(
                    workflow_id,
                    duration_ms=duration_ms,
                )

                parsed = cls._parse_file_summary_response(
                    path,
                    module_name,
                    response,
                    file_meta.get("importance_score", 0.0),
                )

                RuntimeCache.save_json(
                    cache_key,
                    parsed.model_dump(),
                )

                return parsed

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

        module_summaries = []

        for module_name, summaries in grouped.items():
            context = cls._build_module_context(summaries)

            prompt = PromptBuilder.build_module_summary_prompt(
                module_name=module_name,
                context=context,
            )

            start_time = asyncio.get_event_loop().time()

            try:
                response = await cls._generate_with_retry(llm_client, prompt)

                duration_ms = (
                    asyncio.get_event_loop().time() - start_time
                ) * 1000

                WorkflowTracer.on_llm_call(
                    workflow_id,
                    duration_ms=duration_ms,
                )

                module_summary = ModuleSummary(
                    module_name=module_name,
                    purpose=response,
                    responsibilities=[
                        s.purpose for s in summaries[:5]
                    ],
                    important_files=[
                        s.path
                        for s in sorted(
                            summaries,
                            key=lambda x: x.importance_score,
                            reverse=True,
                        )[:5]
                    ],
                )

                module_summaries.append(module_summary)

            except Exception as exc:
                logger.exception(
                    "Failed to summarize module | module=%s | error=%s",
                    module_name,
                    str(exc),
                )

        return module_summaries

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
        context = cls._build_repository_context(module_summaries)

        prompt = PromptBuilder.build_repo_analysis_prompt(context)

        start_time = asyncio.get_event_loop().time()

        response = await cls._generate_with_retry(llm_client, prompt)

        duration_ms = (
            asyncio.get_event_loop().time() - start_time
        ) * 1000

        WorkflowTracer.on_llm_call(
            workflow_id,
            duration_ms=duration_ms,
        )

        return response

    # ============================================================
    # HELPERS
    # ============================================================

    @classmethod
    async def _generate_with_retry(cls, llm_client: Any, prompt: str, timeout: int = 30) -> str:
        for attempt in range(3):
            try:
                return await asyncio.wait_for(llm_client.generate(prompt), timeout=timeout)
            except asyncio.TimeoutError:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
        return ""

    @classmethod
    async def _read_file_safe(
        cls,
        file_path: str,
    ) -> str | None:
        path = Path(file_path)

        if not path.exists():
            return None

        try:
            if path.stat().st_size > cls.MAX_FILE_SIZE_BYTES:
                return None

            content = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            if len(content) > cls.MAX_FILE_CHARS:
                content = content[: cls.MAX_FILE_CHARS]
                content += "\n\n[TRUNCATED FOR TOKEN LIMITS]"

            return content

        except Exception as exc:
            logger.exception(
                "Failed to read file | path=%s | error=%s",
                file_path,
                str(exc),
            )

            return None

    @staticmethod
    def _extract_module_name(path: str) -> str:
        path_obj = Path(path)

        return path_obj.parts[0] if len(path_obj.parts) > 1 else "root"

    @staticmethod
    def _build_cache_key(path: str, content: str) -> str:
        digest = hashlib.sha256(content.encode()).hexdigest()[:16]

        safe_path = path.replace("/", "_").replace("\\", "_")

        return f"file_summary_{safe_path}_{digest}"

    @staticmethod
    def _parse_file_summary_response(
        path: str,
        module_name: str,
        response: str,
        importance_score: float,
    ) -> FileSummary:
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            data = json.loads(cleaned)
            return FileSummary(
                path=path,
                module=module_name,
                purpose=data.get("purpose", ""),
                exports=data.get("exports", []),
                env_vars=data.get("env_vars", []),
                commands=data.get("commands", []),
                dependencies=data.get("dependencies", []),
                side_effects=data.get("side_effects", []),
                importance_score=importance_score,
            )
        except Exception:
            return FileSummary(
                path=path,
                module=module_name,
                purpose=cleaned,
                importance_score=importance_score,
            )

    @staticmethod
    def _build_module_context(summaries: list[FileSummary]) -> str:
        lines = []
        for summary in summaries:
            data = summary.model_dump(exclude={'path', 'module', 'importance_score'})
            lines.append(f"Asset Path: {summary.path}\nTelemetry Metadata:\n{json.dumps(data, indent=2)}")
        return "\n\n---\n\n".join(lines)

    @staticmethod
    def _build_repository_context(
        module_summaries: list[ModuleSummary],
    ) -> str:
        lines = []

        for module in module_summaries:
            lines.append(
                f"""
Module: {module.module_name}
Purpose: {module.purpose}
Important Files:
{chr(10).join(f'- {f}' for f in module.important_files)}
""".strip()
            )

        return "\n\n".join(lines)