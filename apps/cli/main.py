"""DevOps LLM Agent - CLI Tool

Interactive command-line interface for managing DevOps operations.
"""

import sys
import os
import json
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.syntax import Syntax

console = Console()

# Default configuration
DEFAULT_API_URL = "http://localhost:8000"
CONFIG_FILE = Path.home() / ".devops-agent" / "config.json"


class AgentCLI:
    """CLI client for DevOps LLM Agent."""

    def __init__(self, api_url: str, token: Optional[str] = None):
        self.api_url = api_url
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get JWT token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/api/auth/login",
                json={"username": username, "password": password},
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.headers["Authorization"] = f"Bearer {self.token}"
                return data
            else:
                raise Exception(f"Login failed: {response.text}")

    async def create_task(
        self, task: str, environment: str = "dev-vm", auto_approve: bool = False
    ) -> Dict[str, Any]:
        """Create a new task."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/api/tasks",
                headers=self.headers,
                json={
                    "task": task,
                    "environment_profile": environment,
                    "context": {},
                    "auto_approve": auto_approve,
                },
                timeout=60.0,
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                raise Exception(f"Task creation failed: {response.text}")

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/tasks/{task_id}",
                headers=self.headers,
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get task: {response.text}")

    async def list_tasks(self, limit: int = 10) -> list:
        """List recent tasks."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/api/tasks",
                headers=self.headers,
                params={"limit": limit},
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to list tasks: {response.text}")

    async def get_health(self) -> Dict[str, Any]:
        """Get API health status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.api_url}/api/health")
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Health check failed: {response.text}")


# Configuration management
def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"api_url": DEFAULT_API_URL, "token": None}


def save_config(config: Dict[str, Any]):
    """Save configuration to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


# CLI Commands
@click.group()
@click.option("--api-url", default=None, help="API URL")
@click.pass_context
def cli(ctx, api_url):
    """DevOps LLM Agent - AI-powered DevOps automation."""
    config = load_config()
    ctx.obj = AgentCLI(
        api_url=api_url or config.get("api_url", DEFAULT_API_URL),
        token=config.get("token"),
    )


@cli.command()
@click.option("--username", prompt=True, help="Username")
@click.option("--password", prompt=True, hide_input=True, help="Password")
@click.pass_obj
def login(client: AgentCLI, username: str, password: str):
    """Login to the agent."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Logging in...", total=None)
            result = asyncio.run(client.login(username, password))

        # Save token
        config = load_config()
        config["token"] = client.token
        config["api_url"] = client.api_url
        save_config(config)

        console.print(Panel.fit(
            f"[green]✓[/green] Successfully logged in as [bold]{username}[/bold]",
            title="Login Success",
        ))

    except Exception as e:
        console.print(f"[red]✗[/red] Login failed: {e}")
        sys.exit(1)


@cli.command()
@click.pass_obj
def logout(client: AgentCLI):
    """Logout and clear credentials."""
    config = load_config()
    config["token"] = None
    save_config(config)
    console.print("[green]✓[/green] Logged out successfully")


@cli.command()
@click.argument("task", nargs=-1, required=True)
@click.option("-e", "--environment", default="dev-vm", help="Environment profile")
@click.option("-y", "--yes", is_flag=True, help="Auto-approve without confirmation")
@click.option("-w", "--wait", is_flag=True, help="Wait for task completion")
@click.pass_obj
def run(client: AgentCLI, task: tuple, environment: str, yes: bool, wait: bool):
    """Execute a task."""
    task_text = " ".join(task)

    try:
        # Display task info
        console.print(Panel.fit(
            f"[bold]Task:[/bold] {task_text}\n"
            f"[bold]Environment:[/bold] {environment}\n"
            f"[bold]Auto-approve:[/bold] {yes}",
            title="Task Submission",
        ))

        # Confirm if not auto-approved
        if not yes:
            if not Confirm.ask("Execute this task?"):
                console.print("[yellow]Task cancelled[/yellow]")
                return

        # Create task
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Creating task...", total=None)
            result = asyncio.run(
                client.create_task(task_text, environment, auto_approve=yes)
            )

        task_id = result.get("task_id") or result.get("id")
        status = result.get("status")

        console.print(f"\n[green]✓[/green] Task created: [bold]{task_id}[/bold]")
        console.print(f"Status: [yellow]{status}[/yellow]")

        # Wait for completion if requested
        if wait:
            console.print("\nWaiting for task completion...")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task_progress = progress.add_task("Executing...", total=None)

                while True:
                    asyncio.sleep(2)
                    task_data = asyncio.run(client.get_task(task_id))
                    status = task_data.get("status")

                    if status in ["completed", "failed", "cancelled"]:
                        break

            # Display results
            display_task_result(task_data)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


@cli.command()
@click.argument("task_id")
@click.pass_obj
def status(client: AgentCLI, task_id: str):
    """Check task status."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching task status...", total=None)
            task = asyncio.run(client.get_task(task_id))

        display_task_result(task)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


@cli.command()
@click.option("-n", "--limit", default=10, help="Number of tasks to show")
@click.pass_obj
def list(client: AgentCLI, limit: int):
    """List recent tasks."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Fetching tasks...", total=None)
            tasks = asyncio.run(client.list_tasks(limit))

        if not tasks:
            console.print("[yellow]No tasks found[/yellow]")
            return

        # Create table
        table = Table(title=f"Recent Tasks (showing {len(tasks)})")
        table.add_column("ID", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="dim")

        for task in tasks:
            task_id = task.get("id", "")[:8]
            description = task.get("description", "")[:50]
            status = task.get("status", "unknown")
            created = task.get("created_at", "")[:19]

            # Color status
            if status == "completed":
                status = f"[green]{status}[/green]"
            elif status == "failed":
                status = f"[red]{status}[/red]"
            elif status == "pending":
                status = f"[yellow]{status}[/yellow]"

            table.add_row(task_id, description, status, created)

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


@cli.command()
@click.pass_obj
def health(client: AgentCLI):
    """Check API health."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Checking health...", total=None)
            health_data = asyncio.run(client.get_health())

        # Display health status
        table = Table(title="API Health Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")

        for component, healthy in health_data.items():
            status = "[green]✓ Healthy[/green]" if healthy else "[red]✗ Unhealthy[/red]"
            table.add_row(component, status)

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        sys.exit(1)


@cli.command()
def interactive():
    """Start interactive mode."""
    console.print(Panel.fit(
        "[bold cyan]DevOps LLM Agent - Interactive Mode[/bold cyan]\n"
        "Type 'help' for commands, 'exit' to quit",
        title="Welcome",
    ))

    config = load_config()
    client = AgentCLI(
        api_url=config.get("api_url", DEFAULT_API_URL),
        token=config.get("token"),
    )

    while True:
        try:
            command = Prompt.ask("\n[bold cyan]agent>[/bold cyan]")

            if not command.strip():
                continue

            if command.lower() in ["exit", "quit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if command.lower() == "help":
                show_interactive_help()
                continue

            # Execute as task
            try:
                result = asyncio.run(
                    client.create_task(command, auto_approve=False)
                )
                task_id = result.get("task_id") or result.get("id")
                console.print(f"[green]✓[/green] Task created: {task_id}")
                console.print(f"Use 'status {task_id}' to check progress")

            except Exception as e:
                console.print(f"[red]✗[/red] Error: {e}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except EOFError:
            break


def display_task_result(task: Dict[str, Any]):
    """Display task result in a nice format."""
    task_id = task.get("id", "unknown")
    description = task.get("description", "")
    status = task.get("status", "unknown")
    result = task.get("result", {})

    # Status color
    status_color = "green" if status == "completed" else "red" if status == "failed" else "yellow"

    console.print(Panel.fit(
        f"[bold]Task ID:[/bold] {task_id}\n"
        f"[bold]Description:[/bold] {description}\n"
        f"[bold]Status:[/bold] [{status_color}]{status}[/{status_color}]",
        title="Task Details",
    ))

    # Display result if available
    if result:
        console.print("\n[bold]Results:[/bold]")
        syntax = Syntax(json.dumps(result, indent=2), "json", theme="monokai")
        console.print(syntax)


def show_interactive_help():
    """Show help for interactive mode."""
    help_text = """
Available commands:
  - Type any task description to execute
  - 'status <task_id>' - Check task status
  - 'list' - List recent tasks
  - 'help' - Show this help
  - 'exit' or 'quit' - Exit interactive mode

Examples:
  > Check server health for web-01
  > Find errors in nginx logs
  > Restart postgresql service
    """
    console.print(Markdown(help_text))


if __name__ == "__main__":
    cli()
