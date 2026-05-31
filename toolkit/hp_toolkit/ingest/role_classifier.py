# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""HP role hint classifier — the per-file architectural-role tagger.

The single most decision-shaping signal hp-ingest gives to downstream agents.
Computed deterministically (no LLM): from file path, extension, and a few
content regexes. Cheap, runnable on millions of files.

The six categories (defined in `schema.py`):

  - `boundary`      — HTTP/gRPC/CLI/cron entry points, message-bus consumers
  - `pure-logic`    — domain types + functions, no I/O imports
  - `state-machine` — state-enum + transition-table or saga patterns
  - `data-store`    — DB/cache/queue clients, ORM model declarations
  - `infra`         — Dockerfile / k8s / terraform / CI / Ansible
  - `config`        — TOML/YAML/JSON config (not package manifests)

The classifier returns `None` when no role matches (file is likely not
architecturally significant — handled by the significance filter).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .schema import HpRoleHint


# ─────────────────────────────────────────────────────────────────────
# Filename / path patterns
# ─────────────────────────────────────────────────────────────────────

# Filenames that always classify as infrastructure.
_INFRA_FILENAMES = {
    "Dockerfile", "dockerfile",
    "docker-compose.yml", "docker-compose.yaml",
    "compose.yml", "compose.yaml",
    "Makefile", "makefile",
    "Tiltfile", "Procfile",
    ".dockerignore", ".gitlab-ci.yml",
    # ── Embedded build / config (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding E) ──
    "CMakeLists.txt", "Kconfig", "defconfig",
    "platformio.ini", "west.yml",
    "prj.conf",                       # Zephyr app config
}

# Path-prefix patterns for infra.
_INFRA_PATH_PATTERNS = [
    re.compile(r"\.github/workflows/.*\.ya?ml$"),
    re.compile(r"\.gitlab/.*\.ya?ml$"),
    re.compile(r"\.circleci/.*\.ya?ml$"),
    re.compile(r"helm/.*\.ya?ml$"),
    re.compile(r"charts?/.*\.ya?ml$"),
    re.compile(r"k8s/.*\.ya?ml$"),
    re.compile(r"kubernetes/.*\.ya?ml$"),
    re.compile(r"manifests?/.*\.ya?ml$"),
    re.compile(r"terraform/.*\.tf$"),
    re.compile(r"\.tf$"),
    re.compile(r"ansible/.*\.ya?ml$"),
    re.compile(r"playbooks?/.*\.ya?ml$"),
    # ── Embedded artifacts ──
    re.compile(r"\.ioc$"),            # STM32CubeMX project file
    re.compile(r"\.ld$"),             # Linker script
    re.compile(r"\.px4board$"),       # PX4 board config
    re.compile(r"\.overlay$"),        # Zephyr DTS overlay
    re.compile(r"boards/[^/]+/[^/]+/(?:nuttx-config|defconfig)"),  # NuttX board config
]

# Filenames that are config (package manifests excluded — handled separately).
_CONFIG_EXTENSIONS = {".toml", ".ini", ".cfg", ".conf", ".env"}
_PACKAGE_MANIFESTS = {
    "package.json", "package-lock.json", "pnpm-lock.yaml",
    "Cargo.toml", "Cargo.lock",
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock", "requirements.txt",
    "go.mod", "go.sum",
}

# Filename hints for CLI entry / boundary files.
_BOUNDARY_FILENAMES = {"main.py", "main.rs", "main.go", "main.ts", "cli.py", "cli.ts", "app.py", "server.py"}


# ─────────────────────────────────────────────────────────────────────
# Content patterns — regex-based; cheap; not 100% accurate
# ─────────────────────────────────────────────────────────────────────

_BOUNDARY_PATTERNS = [
    # HTTP servers across frameworks
    re.compile(r"\b(FastAPI|fastapi)\s*\("),
    re.compile(r"\bflask\.Flask\s*\("),
    re.compile(r"\b(Express|express)\s*\(\)"),
    re.compile(r"\bAxum::Server|axum::Router|axum::serve"),
    re.compile(r"\b(actix_web|rocket)::"),
    re.compile(r"\bgin\.(New|Default)\s*\(\)"),
    re.compile(r"\bhttp\.HandleFunc|http\.ListenAndServe"),
    # gRPC servers
    re.compile(r"\bgrpc\.NewServer|tonic::transport::Server"),
    # CLI entry points
    re.compile(r"\b(clap::Parser|argparse\.ArgumentParser|click\.command)\b"),
    re.compile(r"\bcobra\.(Command|Execute)\b"),
    # Message bus consumers
    re.compile(r"\b(KafkaConsumer|AIOKafkaConsumer|kafka_consumer)\b"),
    re.compile(r"\b(SQS|sqs)\.receive_message|@sqs_listener"),
    re.compile(r"\b(nats|NATS)\.subscribe"),
    # File / cron entries
    re.compile(r"\b(cron|schedule|APScheduler)\.|@cron|@scheduled\b"),
    re.compile(r"\binotify\.|fs\.watch|fsnotify\.NewWatcher"),
    # WebSocket servers
    re.compile(r"\bWebSocketServer|ws\.Server|tokio_tungstenite::accept_async"),
    # ── Embedded / firmware boundaries (per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding E + B) ──
    # ROS 2 + Micro-ROS topic surfaces (pub/sub = external comm boundary)
    re.compile(r"\b(rclcpp::create_(publisher|subscription|service|client)|rcl_(publisher|subscription|service|client)_init|rclc_(publisher|subscription|service|client)_init)\b"),
    # uORB (PX4 internal pub/sub treated as boundary because it's the
    # cross-module middleware that flow definitions ride on)
    re.compile(r"\b(orb_advertise|orb_subscribe|ORB_ID\s*\(|ORB_DECLARE)\b"),
    # MAVLink — off-vehicle by definition
    re.compile(r"\bmavlink_msg_[a-z0-9_]+_(pack|encode|decode)\b"),
    # DDS endpoints
    re.compile(r"\bdds_create_(writer|reader|topic|participant)\b"),
    # NSH / command-line shell registration on NuttX
    re.compile(r"\b(NSH_DECLARE_BUILTIN|nsh_builtin)\b"),
    # Hardware peripheral inits — STM32 HAL family (Tx PWM out, GPIO interrupts in, etc.)
    re.compile(r"\bHAL_(TIM_PWM|TIM_OC|GPIO_EXTI|UART|USART|I2C|SPI|CAN|ADC|DAC|DMA)_(Start|Init|Receive_IT|Transmit_IT|Receive_DMA|Transmit_DMA|MspInit|GetValue|Start_IT|Start_DMA|IRQHandler)\b"),
    re.compile(r"\bHAL_GPIO_EXTI_Callback\b"),
    # Zephyr / device-tree-style hardware acquisition
    re.compile(r"\bdevice_get_binding\s*\(|DEVICE_DT_GET\s*\("),
    # NuttX / PX4 board-arch entry points
    re.compile(r"\b(px4_arch_[a-z_]+|board_app_initialize)\b"),
]

_STATE_MACHINE_PATTERNS = [
    # State enum + match/switch coupling
    re.compile(r"\b(enum|class)\s+\w*(State|Mode|Phase|Status)\b"),
    re.compile(r"\b(state_machine|StateMachine|FSM|StatefulWidget)\b"),
    re.compile(r"\bsaga\.(start|execute)|@saga\b"),
    # Transition tables
    re.compile(r"\b(transitions|TRANSITIONS|state_transitions)\s*[:=]\s*[\[\{]"),
    # XState / statemachine.js style
    re.compile(r"\b(createMachine|interpret|Machine\()"),
    # Rust enum used as state with `impl` of `match self { … }`
    re.compile(r"match\s+self\s*\{[^}]*=>"),
    # C/C++ switch on a *_state variable → strong FSM signal
    re.compile(r"switch\s*\(\s*\w*(state|mode|phase|status)\w*\s*\)", re.IGNORECASE),
    # C enum with all-caps STATE_* members → state enum convention
    re.compile(r"\benum\s+(?:class\s+)?\w*\s*\{[^}]*\b(STATE|MODE|PHASE|ST)_[A-Z_]+\s*[,=}]"),
]

# DB / cache / queue / object-store client detection. Per tuning H.A: must
# require IMPORT context, not bare-token presence — otherwise comments,
# docstrings, system-prompt strings, and `.gitignore` entries all false-fire.
#
# Pattern shape per language:
#   Python: `import X` / `from X import …` / `from X.Y import …`
#   Rust:   `use X::…` / `use X;`
#   TS/JS:  `import X from 'X'` / `from 'X'` / `require('X')`
#   Go:     `"github.com/<vendor>/<lib>"` (in import block, between quotes)
# Plus explicit ORM-model declarations + client-construction patterns that
# are themselves unambiguous in any context.

_DATA_STORE_PATTERNS = [
    # Python imports — relational
    re.compile(r"^\s*(import|from)\s+(psycopg2|psycopg|asyncpg|sqlalchemy|sqlmodel|pony|peewee)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(aiomysql|mysql|pymysql|mysqlclient)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(sqlite3|aiosqlite)\b", re.MULTILINE),
    # Python imports — k/v + queue + nosql
    re.compile(r"^\s*(import|from)\s+(redis|aioredis|fakeredis)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(motor|pymongo)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(boto3|aioboto3)\b.*?(dynamodb|s3)?", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(clickhouse_driver|clickhouse_connect|aiochclient)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+pydgraph\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(kafka|aiokafka|confluent_kafka)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(minio|google\.cloud\.storage)\b", re.MULTILINE),
    re.compile(r"^\s*(import|from)\s+(elasticsearch|opensearchpy)\b", re.MULTILINE),
    # Rust use-clauses
    re.compile(r"^\s*use\s+(sqlx|diesel|sea_orm|tokio_postgres|deadpool_postgres|deadpool_redis|redis|mongodb|clickhouse|kafka|rdkafka|aws_sdk_dynamodb|aws_sdk_s3)\b", re.MULTILINE),
    # TS/JS imports
    re.compile(r"""(?:from|require\()\s*['"](pg|pg-pool|mysql2?|sqlite3|better-sqlite3|ioredis|redis|mongodb|mongoose|@aws-sdk/client-dynamodb|@aws-sdk/client-s3|@clickhouse/client|kafkajs|elasticsearch|@elastic/elasticsearch|dgraph-js)['"]"""),
    re.compile(r"""(?:from|require\()\s*['"](prisma|@prisma/client|typeorm|knex|sequelize|drizzle-orm)['"]"""),
    # Go imports (inside import-block quotes)
    re.compile(r'"github\.com/(jackc/pg(x|conn|pool)|lib/pq|go-redis/redis|go-sql-driver/mysql|gorm\.io/gorm|mongodb/mongo-go-driver|aws/aws-sdk-go/service/(dynamodb|s3)|ClickHouse/clickhouse-go|segmentio/kafka-go|olivere/elastic|dgraph-io/dgo)'),
    re.compile(r'"go\.mongodb\.org/mongo-driver'),
    # ORM / declarative-model markers (unambiguous regardless of context)
    re.compile(r"\b(SQLModel|DeclarativeBase)\b"),
    re.compile(r"Base\s*=\s*declarative_base\("),
    re.compile(r"#\[derive\([^)]*sqlx::FromRow"),
    re.compile(r"#\[derive\([^)]*(Queryable|Insertable)"),  # diesel
    # Client construction (explicit factory calls — also unambiguous)
    re.compile(r"\b(PgPool|MySqlPool|SqlitePool)::(connect|new)\b"),
    re.compile(r"\bredis::Client::open\b"),
    re.compile(r"\bMongoClient\s*\("),
    re.compile(r"\bnew\s+(Pool|Client|MongoClient|Redis)\s*\("),
]

_PURE_LOGIC_HINTS = [
    # Dataclasses / domain types
    re.compile(r"\b@dataclass\b|class\s+\w+\(BaseModel\)|#\[derive\(.*Deserialize"),
    re.compile(r"\b(struct|enum|interface|type)\s+\w+"),
]


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def classify_file(path: Path, content: Optional[str] = None) -> Optional[HpRoleHint]:
    """Classify a single file's HP role hint.

    `path` is the file path (used for filename / extension / directory checks).
    `content` is the file text (sniffed for content patterns). If None, only
    path-based rules fire — useful for binary files or when content sniffing
    is too expensive."""
    name = path.name
    suffix = path.suffix.lower()
    posix = path.as_posix()

    # 1. Infra — strongest filename / path signal, no content needed
    if name in _INFRA_FILENAMES or any(p.search(posix) for p in _INFRA_PATH_PATTERNS):
        return HpRoleHint.INFRA

    # 2. Package manifest = infra-adjacent; treat as config-light, not a role node
    if name in _PACKAGE_MANIFESTS:
        return HpRoleHint.CONFIG

    # 3. Generic config files (TOML / INI / etc.)
    if suffix in _CONFIG_EXTENSIONS:
        return HpRoleHint.CONFIG

    # 4. YAML/JSON files in known config directories
    if suffix in (".yml", ".yaml", ".json") and not _is_in_source_tree(path):
        return HpRoleHint.CONFIG

    # 5. Content-pattern checks — require content
    if content is None:
        # If we only have the filename, the boundary-filename hint is best-effort.
        if name in _BOUNDARY_FILENAMES:
            return HpRoleHint.BOUNDARY
        return None

    # 6. State-machine before boundary — a state-rich HTTP handler is still a
    # state machine for HP purposes; the handler is one of many implementing
    # files of the same Stage-3 entity.
    if _matches_any(_STATE_MACHINE_PATTERNS, content):
        return HpRoleHint.STATE_MACHINE

    if _matches_any(_BOUNDARY_PATTERNS, content):
        return HpRoleHint.BOUNDARY

    if _matches_any(_DATA_STORE_PATTERNS, content):
        return HpRoleHint.DATA_STORE

    # 7. Pure-logic fallback for source files with no I/O signals
    if _is_source_file(suffix) and _matches_any(_PURE_LOGIC_HINTS, content):
        return HpRoleHint.PURE_LOGIC

    # 8. No match — let the significance filter decide if it stays
    return None


def _matches_any(patterns: list[re.Pattern[str]], content: str) -> bool:
    return any(p.search(content) for p in patterns)


def _is_in_source_tree(path: Path) -> bool:
    """Return True if the path is under a known source directory.

    Used to disambiguate `.yaml` files: an OpenAPI spec under `src/` is config
    in the architectural sense, but a Helm chart's `values.yaml` under
    `helm/` is infra."""
    parts = {p.lower() for p in path.parts}
    return bool(parts & {"src", "lib", "app", "internal", "pkg"})


_SOURCE_SUFFIXES = {
    ".py", ".pyi",
    ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".rs", ".go",
    ".java", ".kt", ".scala",
    ".c", ".cc", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift",
}


def _is_source_file(suffix: str) -> bool:
    return suffix.lower() in _SOURCE_SUFFIXES


def detect_language(path: Path) -> Optional[str]:
    """Friendly language label derived from file suffix."""
    mapping = {
        ".py": "python", ".pyi": "python",
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".kt": "kotlin",
        ".c": "c", ".h": "c",
        ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp",
        ".rb": "ruby",
        ".swift": "swift",
        ".php": "php",
        ".sh": "bash", ".bash": "bash",
        ".yml": "yaml", ".yaml": "yaml",
        ".toml": "toml",
        ".json": "json",
        ".md": "markdown",
    }
    return mapping.get(path.suffix.lower())
