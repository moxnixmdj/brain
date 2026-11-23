"""Write the bench's help programs into this repository.

These are the *documents* the planner's tests read. They used to live in a scratch directory, so
a clean checkout could not re-run 8 of 55 tests -- a test that only runs on the machine that wrote
it is not evidence. Each program is a tiny help-text dispatcher in the dialect the benchmark's own
stubs use (`USAGE:` / `AVAILABLE COMMANDS:` / `FLAGS:` with `(required)` and `EXAMPLES:`), which is
also the dialect several real programs use.

Writes `bin/<tool>` and `bin3/<tool>`. Page content is the benchmark's published help, kept here
so the tests state what they read.
"""
from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

TEMPLATE = (HERE / "program_template.py").read_text()


def write(directory: pathlib.Path, name: str, pages: dict[str, str]) -> None:
    """One program: the shared executor with this program's own pages baked in."""
    directory.mkdir(parents=True, exist_ok=True)
    rendered = "{\n" + "".join(
        f"    {json.dumps(k)}: {json.dumps(v)},\n" for k, v in pages.items()) + "}"
    text = (TEMPLATE.replace("PAGES = {}", f"PAGES = {rendered}")
            .replace("__UPPER___STATE", f"{name.upper()}_STATE")
            .replace("__NAME___STATE", f"{name.upper()}_STATE")
            .replace("__NAME__", name))
    path = directory / name
    path.write_text(text)
    path.chmod(0o755)


def root(tool: str, summary: str, commands: list[tuple[str, str]]) -> str:
    lines = [f"{tool} - {summary}", "", "USAGE:", f"  {tool} <command> [flags]", "",
             "AVAILABLE COMMANDS:"]
    lines += [f"  {name:<20}{about}" for name, about in commands]
    lines += ["", "FLAGS:", "  -h, --help          Show help for a command", "",
              f'Use "{tool} <command> --help" for more information.']
    return "\n".join(lines)


def group(tool: str, summary: str, route: str, commands: list[tuple[str, str]]) -> str:
    lines = [summary, "", "USAGE:", f"  {tool} {route} <command> [flags]", "",
             "AVAILABLE COMMANDS:"]
    lines += [f"  {name:<20}{about}" for name, about in commands]
    lines += ["", "FLAGS:", "  -h, --help          Show help for a command", "",
              f'Use "{tool} <command> --help" for more information.']
    return "\n".join(lines)


def leaf(tool: str, route: str, summary: str, flags: list[tuple[str, str, bool, str]],
         example: str = "") -> str:
    lines = [summary, "", "USAGE:", f"  {tool} {route} [flags]", "", "FLAGS:"]
    for flag, kind, required, about in flags:
        mark = " (required)" if required else ""
        lines.append(f"  {flag} <{kind}>{mark}\t{about}")
    lines += ["", "  -h, --help\tShow help for this command"]
    if example:
        lines += ["", "EXAMPLES:", f"  {example}"]
    return "\n".join(lines)


# ---------------------------------------------------------------- gh
GH = {
    "": root("gh", "GitHub CLI for issues, pull requests, and repositories",
             [("issue", "Manage issue"), ("pr", "Manage pull request"),
              ("repo", "Manage repository")]),
    "issue": group("gh", "Manage issue", "issue", [("list", "List issues"),
                                          ("create", "Create a new issue in a repository"),
                                          ("view", "View an issue")]),
    "issue list": leaf("gh", "issue list", "List issues", [
        ("--repo", "string", True, "Repository in owner/repo format"),
        ("--state", "enum", False, "Filter by state (values: open, closed, all)"),
        ("--label", "string", False, "Filter by label"),
        ("--limit", "int", False, "Maximum number of issues")],
        "gh issue list --repo owner/repo --state open"),
    "issue create": leaf("gh", "issue create", "Create a new issue in a repository", [
        ("--repo", "string", True, "Repository in owner/repo format"),
        ("--title", "string", True, "Issue title"),
        ("--body", "string", False, "Issue body text"),
        ("--label", "string", False, "Label to apply (can be repeated)"),
        ("--assignee", "string", False, "Username to assign")],
        "gh issue create --repo owner/repo --title 'Bug report' --body 'Details here'"),
    "issue view": leaf("gh", "issue view", "View an issue", [
        ("--repo", "string", True, "Repository in owner/repo format"),
        ("--id", "int", True, "Issue number")],
        "gh issue view --repo owner/repo --id 12"),
    "pr": group("gh", "Manage pull request", "pr", [("list", "List pull requests"),
                                             ("create", "Create a pull request")]),
    "pr list": leaf("gh", "pr list", "List pull requests", [
        ("--repo", "string", True, "Repository in owner/repo format"),
        ("--state", "enum", False, "Filter by state (values: open, closed, merged)")],
        "gh pr list --repo owner/repo --state open"),
    "pr create": leaf("gh", "pr create", "Create a pull request", [
        ("--repo", "string", True, "Repository in owner/repo format"),
        ("--title", "string", True, "Pull request title"),
        ("--body", "string", False, "Pull request body"),
        ("--base", "string", False, "Base branch")],
        "gh pr create --repo owner/repo --title 'Add tests'"),
    "repo": group("gh", "Manage repository", "repo", [("list", "List repositories"),
                                             ("view", "View a repository")]),
    "repo list": leaf("gh", "repo list", "List repositories", [
        ("--limit", "int", False, "Maximum number of repositories")], "gh repo list"),
    "repo view": leaf("gh", "repo view", "View a repository", [
        ("--repo", "string", True, "Repository in owner/repo format")],
        "gh repo view --repo owner/repo"),
}

# ---------------------------------------------------------------- slack
SLACK = {
    "": root("slack", "Slack CLI for managing channels, messages, direct messages, and users",
             [("channel", "Manage channel"), ("message", "Manage message"),
              ("dm", "Manage dm"), ("search", "Manage search"), ("user", "Manage user")]),
    "channel": group("slack", "Manage channel", "channel", [("list", "List channels"),
                                                ("info", "Show channel information"),
                                                ("message", "List messages in a channel")]),
    "channel list": leaf("slack", "channel list", "List channels", [
        ("--limit", "int", False, "Maximum number of channels")], "slack channel list"),
    "channel info": leaf("slack", "channel info", "Show channel information", [
        ("--channel", "string", True, "Channel name")],
        "slack channel info --channel engineering"),
    "channel message": leaf("slack", "channel message", "List messages in a channel", [
        ("--channel", "string", True, "Channel name"),
        ("--limit", "int", False, "Maximum number of messages")],
        "slack channel message --channel engineering --limit 10"),
    "message": group("slack", "Manage message", "message", [("send", "Post a message to a channel")]),
    "message send": leaf("slack", "message send", "Post a message to a channel", [
        ("--channel", "string", True, "Channel name"),
        ("--text", "string", True, "Message text content")],
        "slack message send --channel engineering --text 'Deploy complete'"),
    "dm": group("slack", "Manage dm", "dm", [("send", "Send a direct message to a user")]),
    "dm send": leaf("slack", "dm send", "Send a direct message to a user", [
        ("--user", "string", True, "Username of the recipient"),
        ("--text", "string", True, "Message text content")],
        "slack dm send --user alice --text 'on my way'"),
    "search": group("slack", "Manage search", "search", [("message", "Search messages")]),
    "search message": leaf("slack", "search message", "Search messages", [
        ("--query", "string", True, "Search query"),
        ("--channel", "string", False, "Limit to a channel")],
        "slack search message --query outage"),
    "user": group("slack", "Manage user", "user", [("list", "List users")]),
    "user list": leaf("slack", "user list", "List users", [], "slack user list"),
}

# ---------------------------------------------------------------- linear
LINEAR = {
    "": root("linear", "Linear CLI for issues, projects, and teams",
             [("issue", "Manage issue"), ("project", "Manage project"), ("team", "Manage team")]),
    "issue": group("linear", "Manage issue", "issue", [("list", "List issues"),
                                             ("create", "Create an issue"),
                                             ("update", "Update an issue")]),
    "issue list": leaf("linear", "issue list", "List issues", [
        ("--team", "string", False, "Filter by team"),
        ("--project", "string", False, "Filter by project"),
        ("--status", "enum", False,
         "Filter by issue status (values: Todo, In Progress, Done, Cancelled)"),
        ("--assignee", "string", False, "Filter by assignee username"),
        ("--limit", "int", False, "Maximum number of issues")],
        "linear issue list --team Platform"),
    "issue create": leaf("linear", "issue create", "Create an issue", [
        ("--team", "string", True, "Team name"),
        ("--title", "string", True, "Issue title"),
        ("--description", "string", False, "Issue description"),
        ("--priority", "int", False, "Priority level (0=none, 1=urgent, 2=high)"),
        ("--assignee", "string", False, "Username to assign")],
        "linear issue create --team Platform --title 'Add retries'"),
    "issue update": leaf("linear", "issue update", "Update an issue", [
        ("--id", "string", True, "Issue identifier"),
        ("--status", "enum", False, "New status (values: Todo, In Progress, Done, Cancelled)"),
        ("--assignee", "string", False, "New assignee username"),
        ("--title", "string", False, "New title")],
        "linear issue update --id ISS-42 --status Done"),
    "project": group("linear", "Manage project", "project", [("list", "List projects"),
                                                 ("view", "View a project")]),
    "project list": leaf("linear", "project list", "List projects", [
        ("--team", "string", False, "Filter by team"),
        ("--status", "enum", False, "Filter by project status (values: Planned, Started, Done)")],
        "linear project list"),
    "project view": leaf("linear", "project view", "View a project", [
        ("--name", "string", True, "Project name")], "linear project view --name 'Q1 Migration'"),
    "team": group("linear", "Manage team", "team", [("list", "List teams")]),
    "team list": leaf("linear", "team list", "List teams", [], "linear team list"),
}

# ---------------------------------------------------------------- datapipe (recorded verbatim)
DATAPIPE = {
    "": ("datapipe - Data pipeline orchestrator for connecting sources, applying transformations, "
         "and routing to sinks on configurable schedules\n\nUSAGE:\n  datapipe <command> [flags]\n\n"
         "AVAILABLE COMMANDS:\n  source              Manage source\n  transform           Manage transform\n"
         "  sink                Manage sink\n  pipeline            Manage pipeline\n\nFLAGS:\n"
         "  -h, --help          Show help for a command\n\n"
         'Use "datapipe <command> --help" for more information.'),
    "source": ("Manage source\n\nUSAGE:\n  datapipe source <command> [flags]\n\nAVAILABLE COMMANDS:\n"
               "  list                List all configured data sources\n"
               "  connect             Register a new data source connection\n\nFLAGS:\n"
               "  -h, --help          Show help for a command\n\n"
               'Use "datapipe source <command> --help" for more information.'),
    "source list": ("List all configured data sources\n\nUSAGE:\n  datapipe source list [flags]\n\n"
                    "FLAGS:\n  --type <enum>\tFilter by source type "
                    "(values: postgres, mysql, s3, api, kafka, mongodb)\n\n"
                    "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                    "  datapipe source list --type postgres"),
    "source connect": ("Register a new data source connection\n\nUSAGE:\n"
                       "  datapipe source connect [flags]\n\nFLAGS:\n"
                       "  --name <string> (required)\tSource name (unique identifier)\n"
                       "  --type <enum> (required)\tSource type "
                       "(values: postgres, mysql, s3, api, kafka, mongodb)\n"
                       "  --config <json> (required)\tConnection configuration as JSON "
                       '(e.g. {"host": "db.example.com", "port": 5432, "database": "analytics"})\n\n'
                       "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                       "  datapipe source connect --name prod-db --type postgres "
                       "--config '{\"host\": \"db.example.com\", \"port\": 5432, "
                       "\"database\": \"analytics\"}'"),
    "transform": ("Manage transform\n\nUSAGE:\n  datapipe transform <command> [flags]\n\n"
                  "AVAILABLE COMMANDS:\n"
                  "  create              Create a named transformation step with SQL logic\n"
                  "  run                 Execute a transformation step\n\nFLAGS:\n"
                  "  -h, --help          Show help for a command\n\n"
                  'Use "datapipe transform <command> --help" for more information.'),
    "transform create": ("Create a named transformation step with SQL logic\n\nUSAGE:\n"
                         "  datapipe transform create [flags]\n\nFLAGS:\n"
                         "  --name <string> (required)\tTransform name (unique identifier)\n"
                         "  --sql <string> (required)\tSQL transformation query\n"
                         "  --source <string> (required)\tSource name to read data from\n"
                         "  --description <string>\tHuman-readable description of the transformation\n\n"
                         "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                         "  datapipe transform create --name daily-revenue --sql "
                         "'SELECT date, SUM(amount) as revenue FROM orders GROUP BY date' "
                         "--source prod-db"),
    "transform run": ("Execute a transformation step\n\nUSAGE:\n"
                      "  datapipe transform run [flags]\n\nFLAGS:\n"
                      "  --name <string> (required)\tTransform name to execute\n"
                      "  --dry-run <bool>\tPreview the output without writing results\n"
                      "  --limit <int>\tLimit output rows (useful for preview)\n\n"
                      "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                      "  datapipe transform run --name daily-revenue --dry-run --limit 10"),
    "sink": ("Manage sink\n\nUSAGE:\n  datapipe sink <command> [flags]\n\nAVAILABLE COMMANDS:\n"
             "  create              Create a data sink destination\n\nFLAGS:\n"
             "  -h, --help          Show help for a command\n\n"
             'Use "datapipe sink <command> --help" for more information.'),
    "sink create": ("Create a data sink destination\n\nUSAGE:\n  datapipe sink create [flags]\n\n"
                    "FLAGS:\n  --name <string> (required)\tSink name (unique identifier)\n"
                    "  --type <enum> (required)\tSink type "
                    "(values: s3, bigquery, warehouse, postgres, elasticsearch)\n"
                    "  --config <json> (required)\tSink configuration as JSON "
                    '(e.g. {"bucket": "analytics-output", "prefix": "daily/"})\n\n'
                    "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                    "  datapipe sink create --name analytics-lake --type s3 "
                    "--config '{\"bucket\": \"analytics-output\", \"prefix\": \"daily/\"}'"),
    "pipeline": ("Manage pipeline\n\nUSAGE:\n  datapipe pipeline <command> [flags]\n\n"
                 "AVAILABLE COMMANDS:\n"
                 "  create              Create a complete data pipeline connecting source, "
                 "transforms, and sink with a schedule\n"
                 "  status              Check the status and execution history of a pipeline\n\n"
                 "FLAGS:\n  -h, --help          Show help for a command\n\n"
                 'Use "datapipe pipeline <command> --help" for more information.'),
    "pipeline create": ("Create a complete data pipeline connecting source, transforms, and sink "
                        "with a schedule\n\nUSAGE:\n  datapipe pipeline create [flags]\n\nFLAGS:\n"
                        "  --name <string> (required)\tPipeline name (unique identifier)\n"
                        "  --source <string> (required)\tSource name\n"
                        "  --transforms <string> (required)\tComma-separated list of transform "
                        "names in execution order\n"
                        "  --sink <string> (required)\tSink name\n"
                        "  --schedule <string> (required)\tCron expression for scheduled execution\n\n"
                        "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                        "  datapipe pipeline create --name daily-etl --source prod-db "
                        "--transforms daily-revenue,add-dimensions --sink analytics-lake "
                        "--schedule '0 2 * * *'"),
    "pipeline status": ("Check the status and execution history of a pipeline\n\nUSAGE:\n"
                        "  datapipe pipeline status [flags]\n\nFLAGS:\n"
                        "  --name <string> (required)\tPipeline name\n\n"
                        "  -h, --help\tShow help for this command\n\nEXAMPLES:\n"
                        "  datapipe pipeline status --name daily-etl"),
}

# ---------------------------------------------------------------- flowctl
FLOWCTL = {
    "": root("flowctl", "Workflow engine CLI for pipelines, gates, and runs",
             [("workflow", "Manage workflow"), ("gate", "Manage gate"), ("run", "Manage run")]),
    "workflow": group("flowctl", "Manage workflow", "workflow", [("create", "Create a workflow"),
                                                    ("get", "Get a workflow"),
                                                    ("list", "List workflows")]),
    "workflow create": leaf("flowctl", "workflow create", "Create a workflow", [
        ("--name", "string", True, "Workflow name (unique identifier)"),
        ("--steps", "json", True, "Workflow steps as JSON array"),
        ("--description", "string", False, "Human-readable description")],
        "flowctl workflow create --name deploy-staging --steps '[{\"name\": \"build\"}]'"),
    "workflow get": leaf("flowctl", "workflow get", "Get a workflow", [
        ("--id", "string", True, "Workflow ID or name")],
        "flowctl workflow get --id wf-001"),
    "workflow list": leaf("flowctl", "workflow list", "List workflows", [
        ("--status", "enum", False, "Filter by status (values: active, paused, archived)")],
        "flowctl workflow list"),
    "gate": group("flowctl", "Manage gate", "gate", [("approve", "Approve a gate"),
                                            ("reject", "Reject a gate")]),
    "gate approve": leaf("flowctl", "gate approve", "Approve a gate", [
        ("--id", "string", True, "Gate ID"),
        ("--comment", "string", False, "Approval comment")],
        "flowctl gate approve --id gate-001 --comment 'LGTM'"),
    "gate reject": leaf("flowctl", "gate reject", "Reject a gate", [
        ("--id", "string", True, "Gate ID"),
        ("--reason", "string", False, "Rejection reason")],
        "flowctl gate reject --id gate-001 --reason 'failing tests'"),
    "run": group("flowctl", "Manage run", "run", [("start", "Start a run"),
                                          ("status", "Check run status")]),
    "run start": leaf("flowctl", "run start", "Start a run", [
        ("--workflow", "string", True, "Workflow name"),
        ("--inputs", "json", False, "Run inputs as JSON object")],
        "flowctl run start --workflow deploy-staging"),
    "run status": leaf("flowctl", "run status", "Check run status", [
        ("--id", "string", True, "Run ID")], "flowctl run status --id run-001"),
}

# ---------------------------------------------------------------- notion
NOTION = {
    "": root("notion", "Notion CLI for pages, databases, and blocks",
             [("page", "Manage page"), ("database", "Manage database"),
              ("block", "Manage block")]),
    "page": group("notion", "Manage page", "page", [("list", "List pages"),
                                           ("create", "Create a page"),
                                           ("get", "Get a page"),
                                           ("append", "Append a block to a page")]),
    "page list": leaf("notion", "page list", "List pages", [
        ("--parent", "string", False, "Filter by parent database or page"),
        ("--limit", "int", False, "Maximum number of pages")],
        "notion page list --limit 20"),
    "page create": leaf("notion", "page create", "Create a page", [
        ("--title", "string", True, "Page title"),
        ("--parent", "string", True, "Parent database or page"),
        ("--content", "string", False, "Initial page content as plain text")],
        "notion page create --title 'Weekly Report' --parent 'Engineering Wiki'"),
    "page get": leaf("notion", "page get", "Get a page", [
        ("--id", "string", True, "Page ID")], "notion page get --id pg-001"),
    "page append": leaf("notion", "page append", "Append a block to a page", [
        ("--id", "string", True, "Page ID"),
        ("--content", "string", True, "Text content to append as a paragraph block")],
        "notion page append --id pg-001 --content 'Notes from standup'"),
    "database": group("notion", "Manage database", "database", [("list", "List databases")]),
    "database list": leaf("notion", "database list", "List databases", [], "notion database list"),
    "block": group("notion", "Manage block", "block", [("list", "List blocks of a page")]),
    "block list": leaf("notion", "block list", "List blocks of a page", [
        ("--id", "string", True, "Page ID")], "notion block list --id pg-001"),
}

# ---------------------------------------------------------------- meshctl
MESHCTL = {
    "": root("meshctl", "Service mesh configuration manager for routing, traffic policies, and "
             "observability across microservices",
             [("service", "Manage service"), ("policy", "Manage policy"),
              ("traffic", "Manage traffic"), ("observe", "Manage observe")]),
    "service": group("meshctl", "Manage service", "service", [
        ("list", "List all registered services with health status"),
        ("route", "Create or update a routing rule between two services"),
        ("register", "Register a new service in the mesh")]),
    "service list": leaf("meshctl", "service list", "List all registered services with health status", [
        ("--namespace", "string", False, "Filter by namespace"),
        ("--status", "enum", False, "Filter by health status (values: healthy, degraded, unhealthy)")],
        "meshctl service list --namespace production --status healthy"),
    "service route": leaf("meshctl", "service route",
                          "Create or update a routing rule between two services", [
        ("--from", "string", True, "Source service name"),
        ("--to", "string", True, "Destination service name"),
        ("--weight", "int", True, "Traffic weight percentage (0-100)"),
        ("--match-headers", "json", False, "Header matching rules as JSON object")],
        "meshctl service route --from api-gateway --to user-service --weight 80"),
    "service register": leaf("meshctl", "service register", "Register a new service in the mesh", [
        ("--name", "string", True, "Service name"),
        ("--namespace", "string", True, "Namespace to register in"),
        ("--port", "int", True, "Service port number"),
        ("--protocol", "enum", False, "Communication protocol (values: http, grpc, tcp)")],
        "meshctl service register --name payment-svc --namespace production --port 8080"),
    "policy": group("meshctl", "Manage policy", "policy", [("create", "Create a traffic policy"),
                                                ("apply", "Apply an existing policy to a service")]),
    "policy create": leaf("meshctl", "policy create",
                          "Create a traffic policy (rate limit, circuit breaker, or retry)", [
        ("--name", "string", True, "Policy name (unique identifier)"),
        ("--type", "enum", True, "Policy type (values: rate_limit, circuit_breaker, retry)"),
        ("--config", "json", True, "Policy configuration as JSON")],
        "meshctl policy create --name api-rate-limit --type rate_limit"),
    "policy apply": leaf("meshctl", "policy apply", "Apply an existing policy to a service", [
        ("--name", "string", True, "Policy name to apply"),
        ("--service", "string", True, "Target service name")],
        "meshctl policy apply --name api-rate-limit --service user-service"),
    "traffic": group("meshctl", "Manage traffic", "traffic", [
        ("split", "Configure traffic splitting across service versions for canary or "
                  "blue-green deployments")]),
    "traffic split": leaf("meshctl", "traffic split",
                          "Configure traffic splitting across service versions for canary "
                          "or blue-green deployments", [
        ("--service", "string", True, "Service name to split traffic for"),
        ("--versions", "json", True, "Version-to-weight mapping as JSON")],
        "meshctl traffic split --service user-service --versions '{\"v1\": 90, \"v2\": 10}'"),
    "observe": group("meshctl", "Manage observe", "observe", [("metrics", "Get real-time traffic metrics")]),
    "observe metrics": leaf("meshctl", "observe metrics",
                            "Get real-time traffic metrics for a service", [
        ("--service", "string", True, "Service name to observe"),
        ("--window", "enum", False, "Time window for aggregation "
                                    "(values: 5m, 15m, 1h, 6h, 24h)"),
        ("--metric", "enum", False, "Specific metric to query "
                                    "(values: latency, throughput, error_rate, saturation)")],
        "meshctl observe metrics --service user-service --window 15m"),
}

# ---------------------------------------------------------------- jira
JIRA = {
    "": root("jira", "Jira CLI for issues, projects, and sprints",
             [("issue", "Manage issue"), ("project", "Manage project")]),
    "issue": group("jira", "Manage issue", "issue", [("list", "List issues"),
                                           ("create", "Create an issue"),
                                           ("transition", "Transition an issue")]),
    "issue list": leaf("jira", "issue list", "List issues", [
        ("--project", "string", True, "Project key"),
        ("--status", "enum", False, "Filter by status (values: To Do, In Progress, Done)"),
        ("--assignee", "string", False, "Filter by assignee")],
        "jira issue list --project PLAT"),
    "issue create": leaf("jira", "issue create", "Create an issue", [
        ("--project", "string", True, "Project key"),
        ("--summary", "string", True, "Issue summary"),
        ("--description", "string", False, "Issue description"),
        ("--type", "enum", False, "Issue type (values: Bug, Task, Story)")],
        "jira issue create --project PLAT --summary 'Fix login'"),
    "issue transition": leaf("jira", "issue transition", "Transition an issue", [
        ("--key", "string", True, "Issue key"),
        ("--to", "string", True, "Target status")],
        "jira issue transition --key PLAT-12 --to Done"),
    "project": group("jira", "Manage project", "project", [("list", "List projects")]),
    "project list": leaf("jira", "project list", "List projects", [], "jira project list"),
}

# ---------------------------------------------------------------- kforge
KFORGE = {
    "": root("kforge", "Knowledge forge CLI for corpora, embeddings, and indexes",
             [("corpus", "Manage corpus"), ("index", "Manage index")]),
    "corpus": group("kforge", "Manage corpus", "corpus", [("list", "List corpora"),
                                               ("create", "Create a corpus"),
                                               ("add", "Add documents to a corpus")]),
    "corpus list": leaf("kforge", "corpus list", "List corpora", [], "kforge corpus list"),
    "corpus create": leaf("kforge", "corpus create", "Create a corpus", [
        ("--name", "string", True, "Corpus name"),
        ("--description", "string", False, "Corpus description")],
        "kforge corpus create --name handbooks"),
    "corpus add": leaf("kforge", "corpus add", "Add documents to a corpus", [
        ("--corpus", "string", True, "Corpus name"),
        ("--path", "path", True, "Path to a document or directory")],
        "kforge corpus add --corpus handbooks --path ./docs"),
    "index": group("kforge", "Manage index", "index", [("build", "Build an index for a corpus"),
                                             ("list", "List indexes")]),
    "index build": leaf("kforge", "index build", "Build an index for a corpus", [
        ("--corpus", "string", True, "Corpus name"),
        ("--dimensions", "int", False, "Embedding dimensions")],
        "kforge index build --corpus handbooks"),
    "index list": leaf("kforge", "index list", "List indexes", [], "kforge index list"),
}

# ---------------------------------------------------------------- alertmgr
ALERTMGR = {
    "": root("alertmgr", "Incident and alert manager CLI",
             [("incident", "Manage incident"), ("alert", "Manage alert"),
              ("oncall", "Manage oncall")]),
    "incident": group("alertmgr", "Manage incident", "incident", [
        ("create", "Open a new incident"),
        ("list", "List incidents"),
        ("update", "Update an incident"),
        ("resolve", "Resolve an incident")]),
    "incident create": leaf("alertmgr", "incident create",
                            "Open a new incident with a severity and title", [
        ("--title", "string", True, "Incident title"),
        ("--severity", "enum", True, "Incident severity (values: P1, P2, P3, P4)"),
        ("--service", "string", False, "Affected service"),
        ("--description", "string", False, "Incident description")],
        "alertmgr incident create --title 'Payment Service Degradation' --severity P1"),
    "incident list": leaf("alertmgr", "incident list", "List incidents", [
        ("--status", "enum", False, "Filter by status (values: open, resolved)"),
        ("--severity", "enum", False, "Filter by severity (values: P1, P2, P3, P4)")],
        "alertmgr incident list --status open"),
    "incident update": leaf("alertmgr", "incident update", "Update an incident", [
        ("--id", "string", True, "Incident ID"),
        ("--status", "enum", False, "New status (values: open, resolved)"),
        ("--severity", "enum", False, "New severity (values: P1, P2, P3, P4)")],
        "alertmgr incident update --id inc-001 --status resolved"),
    "incident resolve": leaf("alertmgr", "incident resolve", "Resolve an incident", [
        ("--id", "string", True, "Incident ID"),
        ("--note", "string", False, "Resolution note")],
        "alertmgr incident resolve --id inc-001 --note 'fixed'"),
    "alert": group("alertmgr", "Manage alert", "alert", [("list", "List alerts"),
                                               ("silence", "Silence an alert")]),
    "alert list": leaf("alertmgr", "alert list", "List alerts", [
        ("--status", "enum", False, "Filter by status (values: firing, resolved)")],
        "alertmgr alert list --status firing"),
    "alert silence": leaf("alertmgr", "alert silence", "Silence an alert", [
        ("--id", "string", True, "Alert ID"),
        ("--duration", "string", False, "Silence duration")],
        "alertmgr alert silence --id alert-1 --duration 1h"),
    "oncall": group("alertmgr", "Manage oncall", "oncall", [("list", "List on-call schedules")]),
    "oncall list": leaf("alertmgr", "oncall list", "List on-call schedules", [],
                        "alertmgr oncall list"),
}


def main() -> int:
    bin_dir = HERE / "bin"
    for name, pages in {"gh": GH, "slack": SLACK, "linear": LINEAR, "datapipe": DATAPIPE,
                        "flowctl": FLOWCTL, "notion": NOTION, "meshctl": MESHCTL,
                        "jira": JIRA, "kforge": KFORGE, "alertmgr": ALERTMGR}.items():
        write(bin_dir, name, pages)
    print(f"wrote {len(list(bin_dir.iterdir()))} programs to {bin_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
