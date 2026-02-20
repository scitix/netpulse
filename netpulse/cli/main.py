#!/usr/bin/env python3
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Set, Union

import pandas as pd
import requests
from pydantic import (
    AliasChoices,
    Field,
    HttpUrl,
    PrivateAttr,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    CliApp,
    CliPositionalArg,
    CliSubCommand,
    SettingsConfigDict,
)
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.prompt import Confirm
from rich.table import Table

from netpulse.models import DriverConnectionArgs, DriverName, QueueStrategy
from netpulse.models.request import (
    BulkExecutionRequest,
    ExecutionRequest,
    TemplateParseRequest,
    TemplateRenderRequest,
)
from netpulse.models.response import (
    BatchSubmitJobResponse,
    JobInResponse,
)
from netpulse.plugins.drivers.napalm.model import NapalmExecutionRequest
from netpulse.plugins.drivers.netmiko.model import NetmikoExecutionRequest
from netpulse.plugins.drivers.paramiko.model import ParamikoExecutionRequest
from netpulse.plugins.drivers.pyeapi.model import PyeapiExecutionRequest

# Constants
DEFAULT_ENDPOINT = "http://localhost:9000"
DEFAULT_API_KEY = "MY_API_KEY"
DEFAULT_HTTP_TIMEOUT = 15

MONITORING_TIMEOUT = 300  # 5 minutes timeout
MONITORING_INTERVAL = 5  # Check per 5s


printer: Optional["Printer"] = None
client: Optional["NetPulseClient"] = None
config: Optional["RootSettings"] = None


class DeviceVendor(str, Enum):
    """Supported network device vendors and their corresponding netmiko device types"""

    H3C = "hp_comware"
    HUAWEI = "huawei"
    CISCO = "cisco_ios"
    ARISTA = "arista_eos"
    FORTINET = "fortinet"


class HashableJob(JobInResponse):
    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, JobInResponse):
            return False
        return self.id == value.id


# Driver-specific request models for validation
REQUEST_MODEL_REGISTRY: dict[DriverName, type[ExecutionRequest]] = {
    DriverName.NETMIKO: NetmikoExecutionRequest,
    DriverName.NAPALM: NapalmExecutionRequest,
    DriverName.PYEAPI: PyeapiExecutionRequest,
    DriverName.PARAMIKO: ParamikoExecutionRequest,
}


def get_request_model(driver: DriverName) -> type[ExecutionRequest]:
    return REQUEST_MODEL_REGISTRY.get(driver, ExecutionRequest)


def ensure_printer() -> "Printer":
    if printer is None:
        raise RuntimeError("Printer is not initialized")
    return printer


def ensure_client() -> "NetPulseClient":
    if client is None:
        raise RuntimeError("NetPulseClient is not initialized")
    return client


def ensure_config() -> "RootSettings":
    if config is None:
        raise RuntimeError("RootSettings is not initialized")
    return config


def ensure_context() -> tuple["NetPulseClient", "Printer", "RootSettings"]:
    return ensure_client(), ensure_printer(), ensure_config()


class ExecSettings(BaseSettings):
    class RenderTemplate(str, Enum):
        JINJA2 = "jinja2"

    class ParseTemplate(str, Enum):
        TEXTFSM = "textfsm"
        TTP = "ttp"

    # Device list
    file: CliPositionalArg[str] = Field(
        ..., description="Path to the input CSV/XLSX file containing device information"
    )

    # Operation payload (choose one)
    command: Optional[str] = Field(
        default=None,
        description="Command to execute on devices",
        validation_alias=AliasChoices("command", "cmd"),
    )
    config: Optional[str] = Field(
        default=None,
        description="Configuration to push to devices",
        validation_alias=AliasChoices("config", "cfg"),
    )

    # Filters/options
    vendor: Optional[str] = Field(
        default=None,
        description="Filter devices by vendor (e.g., CISCO, HUAWEI), case insensitive",
    )
    force: bool = Field(
        default=False,
        description="Skip execution confirmation prompt",
        validation_alias=AliasChoices("force", "f"),
    )
    monitor: bool = Field(
        default=True,
        description="Monitor job execution progress",
        validation_alias=AliasChoices("monitor", "m"),
    )

    # Driver execution options (netmiko-oriented defaults)
    driver: DriverName = Field(DriverName.NETMIKO, description="Driver to use")
    queue_strategy: Optional[QueueStrategy] = Field(
        default=None,
        description="Queue strategy override (fifo/pinned). Auto-selected if unset",
    )
    ttl: Optional[int] = Field(
        default=None,
        description="Job timeout in seconds",
        ge=1,
        le=86400,
    )
    enable: bool = Field(
        default=True,
        description="Enter enable mode before execution (netmiko)",
    )
    save: bool = Field(
        default=False,
        description="Save configuration after execution (netmiko)",
    )
    driver_args: Optional[str] = Field(
        default=None,
        description="Driver-specific arguments as JSON string or file path",
        validation_alias=AliasChoices("driver-args", "da"),
    )

    # Templates: rendering (pre-process) and parsing (post-process)
    render_type: Optional[RenderTemplate] = Field(
        default=None,
        description="Template renderer to use for payload preprocessing",
        validation_alias=AliasChoices("render-type", "rt"),
    )
    render_template: Optional[str] = Field(
        default=None,
        description="Rendering template (inline or file/http/ftp URI)",
        validation_alias=AliasChoices("render-template", "R"),
    )
    render_context: Optional[str] = Field(
        default=None,
        description="Rendering context as JSON string or file path",
        validation_alias=AliasChoices("render-context", "rc"),
    )

    parse_type: Optional[ParseTemplate] = Field(
        default=None,
        description="Template parser to use for result post-processing",
        validation_alias=AliasChoices("parse-type", "pt"),
    )
    parse_template: Optional[str] = Field(
        default=None,
        description="Parsing template (inline or file/http/ftp URI)",
        validation_alias=AliasChoices("parse-template", "P"),
    )

    _df: Optional[pd.DataFrame] = PrivateAttr(None)

    @model_validator(mode="after")
    def validate_payload(self):
        if (self.command is None) == (self.config is None):
            raise ValueError("Exactly one of `command` or `config` must be provided")

        if (self.render_type is None) != (self.render_template is None):
            raise ValueError("Rendering requires both render-type and render-template")

        if (self.parse_type is None) != (self.parse_template is None):
            raise ValueError("Parsing requires both parse-type and parse-template")

        return self

    # Helper method
    def _load_device_list(self):
        cli, pr, cfg = ensure_context()
        try:
            df = cli.read_devices(self.file, vendor=self.vendor)
            devices = [cli.prepare_connection_args(row) for _, row in df.iterrows()]
        except Exception as e:
            pr.error(f"Error in reading device lists: {e!s}")
            sys.exit(1)

        # Show loading summary
        pr.print("")
        pr.show_config(cfg)
        pr.show_device_list(devices)

        self._df = df
        return devices

    def _prompt_confirmation(self):
        pr = ensure_printer()
        if not Confirm.ask("Proceed?"):
            pr.print("\n[yellow]Operation cancelled by user.[/yellow]")
            sys.exit(0)

    def _monitor_job(self, submitted: List["HashableJob"]):
        cli, pr, cfg = ensure_context()
        jobs = set(submitted)
        succeeded = set()
        failed = set()

        # Monitor the job execution progress
        total_jobs = len(submitted)
        start_time = time.time()

        with pr.create_progress_bar(total_jobs) as progress:
            task = progress.add_task(
                "[yellow]Monitoring job execution",
                total=total_jobs,
                completed=0,
                succeeded=0,
                failed=0,
            )

            while jobs:
                current_time = time.time()
                elapsed_time = current_time - start_time

                if elapsed_time >= cfg.timeout:
                    pr.warning(f"Monitoring timeout after {int(elapsed_time)}s")
                    for job in jobs:
                        job.status = "TIMEOUT"
                        failed.add(job)
                    break

                try:
                    su, fa = cli.check_jobs(jobs)
                except Exception as e:
                    pr.error(f"Error in checking jobs: {e!s}")
                    continue

                succeeded.update(su)
                failed.update(fa)
                jobs = jobs - succeeded - failed

                remaining_time = max(0, cfg.timeout - elapsed_time)
                progress.update(
                    task,
                    completed=len(succeeded) + len(failed),
                    description=f"[yellow]Monitoring job execution (in {int(remaining_time)}s)",
                    succeeded=len(succeeded),
                    failed=len(failed),
                )

                if jobs:
                    time.sleep(cfg.interval)

        return succeeded, failed

    def _save_results(
        self,
        succeeded: set["HashableJob"],
        failed: set["HashableJob"],
        payload_label: str,
    ) -> str:
        """Save execution results to CSV file"""
        if self._df is None:
            raise RuntimeError("Device list is not loaded")

        results = []
        job_map = {job.id: job for job in succeeded | failed}

        for _, device in self._df.iterrows():
            # Find job for this device
            device_jobs = [j for j in job_map.values() if j.queue.endswith(device["IP"])]
            if not device_jobs:
                # Device had no job (submission failed)
                results.append(
                    {
                        "IP": device["IP"],
                        "Name": device.get("Name", ""),
                        "Vendor": device.get("Vendor", ""),
                        "Payload": payload_label,
                        "Status": "Not Submitted",
                        "Job ID": "",
                        "Result": None,
                        "Error": None,
                        "Start Time": None,
                        "End Time": None,
                    }
                )
                continue

            job = device_jobs[0]  # Use first job if multiple exist
            result = job.result.retval if job.result else None
            error = job.result.error["message"] if job.result and job.result.error else None

            # Convert timestamps to local time if present
            start_time = (
                job.started_at.replace(tzinfo=timezone.utc).astimezone() if job.started_at else None
            )
            end_time = (
                job.ended_at.replace(tzinfo=timezone.utc).astimezone() if job.ended_at else None
            )

            results.append(
                {
                    "IP": device["IP"],
                    "Name": device.get("Name", ""),
                    "Vendor": device.get("Vendor", ""),
                    "Payload": payload_label,
                    "Status": job.status,
                    "Job ID": job.id,
                    "Result": result,
                    "Error": error,
                    "Start Time": start_time,
                    "End Time": end_time,
                }
            )

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"result_{timestamp}.csv"

        # Create and save results DataFrame
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_file, index=False)
        return output_file

    def _load_json(self, raw: str | None) -> Optional[dict]:
        if raw is None:
            return None

        pr = ensure_printer()
        path = Path(raw).expanduser()
        if path.exists() and path.is_file():
            try:
                import json

                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        try:
            import json

            return json.loads(raw)
        except Exception:
            pr.error("Failed to parse JSON content for template context/driver-args")
            raise

    def _prepare_rendering(self) -> Optional[TemplateRenderRequest]:
        if not self.render_type:
            return None

        cli = ensure_client()
        rendering = cli.prepare_template(
            TemplateRenderRequest, self.render_type.value, self.render_template
        )

        assert rendering is None or isinstance(rendering, TemplateRenderRequest), (
            "RenderingRequest not prepared, expected to be TemplateRenderRequest or None"
        )

        return rendering

    def _prepare_parsing(self) -> Optional[TemplateParseRequest]:
        if not self.parse_type:
            return None

        cli = ensure_client()
        parsing = cli.prepare_template(
            TemplateParseRequest, self.parse_type.value, self.parse_template
        )

        assert parsing is None or isinstance(parsing, TemplateParseRequest), (
            "ParsingRequest not prepared, expected to be TemplateParseRequest or None"
        )

        return parsing

    def _resolve_payload(self) -> tuple[str, Union[str, Dict, List[str]]]:
        pr = ensure_printer()
        payload_type = "command" if self.command is not None else "config"
        payload = self.command if payload_type == "command" else self.config

        # If rendering is used, payload must be dict (context)
        if self.render_type:
            context_source = self.render_context or payload
            try:
                payload = self._load_json(context_source) if context_source else {}
            except Exception:
                pr.error("Rendering requires JSON context (provide via payload or render-context)")
                sys.exit(1)
            if not isinstance(payload, dict):
                pr.error("Rendering context must be a JSON object")
                sys.exit(1)

        if not payload:
            pr.error("Payload cannot be empty")
            sys.exit(1)

        return payload_type, payload

    def _load_driver_args(self) -> Optional[dict]:
        if not self.driver_args:
            return None

        try:
            args = self._load_json(self.driver_args)
            if args is not None and not isinstance(args, dict):
                raise ValueError("Driver args must be a JSON object")
            return args
        except Exception:
            sys.exit(1)

    def _build_execution_request(
        self,
        payload_type: str,
        payload: Union[str, Dict, List[str]],
        rendering: Optional[TemplateRenderRequest],
        parsing: Optional[TemplateParseRequest],
        driver_args: Optional[dict],
        base_connection: DriverConnectionArgs,
    ) -> ExecutionRequest:
        pr = ensure_printer()
        req_cls = get_request_model(self.driver)

        base_kwargs: dict = {
            "driver": self.driver,
            "queue_strategy": self.queue_strategy,
            "connection_args": base_connection,
            "rendering": rendering,
            "parsing": parsing,
            "ttl": self.ttl,
        }
        base_kwargs[payload_type] = payload
        if driver_args:
            base_kwargs["driver_args"] = driver_args

        # Pass driver-specific flags only when the model supports them
        if "enable_mode" in req_cls.model_fields:
            base_kwargs["enable_mode"] = self.enable
        if "save" in req_cls.model_fields:
            base_kwargs["save"] = self.save
        if "dry_run" in req_cls.model_fields and hasattr(self, "dry_run"):
            base_kwargs["dry_run"] = getattr(self, "dry_run")

        try:
            return req_cls.model_validate(base_kwargs)
        except Exception as e:
            pr.error(f"Error in building execution request: {e}")
            sys.exit(1)

    def cli_cmd(self) -> None:
        cli = ensure_client()
        pr = ensure_printer()
        devices = self._load_device_list()

        rendering = self._prepare_rendering()
        parsing = self._prepare_parsing()
        payload_type, payload = self._resolve_payload()
        driver_args = self._load_driver_args()

        if not self.force:
            self._prompt_confirmation()

        base_request = self._build_execution_request(
            payload_type=payload_type,
            payload=payload,
            rendering=rendering,
            parsing=parsing,
            driver_args=driver_args,
            base_connection=devices[0],
        )

        try:
            response = cli.bulk_execute(
                devices=devices,
                base_request=base_request,
            )
            submitted = (
                [HashableJob(**job.model_dump()) for job in response.data.succeeded]
                if response.data and response.data.succeeded
                else []
            )
            unsubmitted = response.data.failed if response.data and response.data.failed else []
        except Exception as e:
            pr.error(f"Error in requesting execution: {e!s}")
            sys.exit(1)

        # Display job submission results
        pr.print("")
        pr.show_submission_results(submitted, unsubmitted)

        if self.monitor:
            pr.print("\n[italic]Job Status Monitoring[/italic]")
            succeeded, failed = self._monitor_job(submitted)

            output_file = ""
            try:
                payload_label = self.command if payload_type == "command" else self.config
                payload_label = payload_label if payload_label is not None else payload_type
                output_file = self._save_results(succeeded, failed, payload_label)
            except Exception as e:
                pr.error(f"Error in saving results: {e}")
                sys.exit(1)
            finally:
                pr.print("")
                pr.show_final_summary(succeeded, failed, output_file)


class RootSettings(BaseSettings):
    """
    NetPulse API Client in CLI
    """

    # Subcommands
    exec: CliSubCommand[ExecSettings] = Field(..., description="Execute command/config on devices")

    # API config
    endpoint: HttpUrl = Field(HttpUrl(DEFAULT_ENDPOINT), description="NetPulse API endpoint URL")
    api_key: str = Field(DEFAULT_API_KEY, description="API authentication key")

    # Monitoring config
    interval: int = Field(
        MONITORING_INTERVAL,
        description="Interval (in seconds) between job status checks",
        validation_alias=AliasChoices("interval", "i"),
    )
    timeout: int = Field(
        MONITORING_TIMEOUT,
        description="Maximum time (in seconds) to wait for job completion",
        validation_alias=AliasChoices("timeout", "t"),
    )

    model_config = SettingsConfigDict(
        cli_implicit_flags=True, cli_kebab_case=True, case_sensitive=True
    )

    def cli_cmd(self) -> None:
        global config, printer, client
        config = self
        printer = Printer()
        client = NetPulseClient(str(config.endpoint), config.api_key)

        CliApp.run_subcommand(self)


class Printer:
    """Handles all output display logic using Rich library"""

    TABLE_KWARGS: ClassVar[Dict[str, Any]] = {
        "title_justify": "left",
    }

    def __init__(self):
        self.console = Console()

        # Configure rich logger
        logging.basicConfig(
            level="INFO",
            format="%(message)s",
            datefmt="[%X]",
            handlers=[
                RichHandler(
                    rich_tracebacks=True,
                    markup=True,
                    console=self.console,
                    show_path=False,
                )
            ],
        )
        self.log = logging.getLogger("netpulse-cli")

    def print(self, *args, **kwargs):
        self.console.print(*args, **kwargs)

    def info(self, msg):
        self.log.info(msg)

    def error(self, msg):
        self.log.error(f"[red]{msg}[/red]")

    def warning(self, msg):
        self.log.warning(f"[yellow]{msg}[/yellow]")

    def debug(self, msg):
        self.log.debug(f"[dim]{msg}[/dim]")

    def show_config(self, setting: RootSettings):
        """Display config information"""
        table = Table(title="Config Summary", **self.TABLE_KWARGS)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("API Endpoint", str(setting.endpoint))
        table.add_row("API Key", setting.api_key)
        table.add_row("Timeout", f"{setting.timeout}s")
        table.add_row("Interval", f"{setting.interval}s")

        def show_subcommand_config(table, subcommand: BaseSettings):
            payload = subcommand.model_dump(exclude_none=True)
            for key, value in payload.items():
                table.add_row(key.capitalize().replace("_", " "), str(value))

        if setting.exec:
            show_subcommand_config(table, setting.exec)

        self.console.print(table)

    def show_device_list(self, devices: List[DriverConnectionArgs]):
        """Display table of selected devices"""
        table = Table(title="Selected Devices", **self.TABLE_KWARGS)
        table.add_column("IP", style="cyan")
        table.add_column("Port", style="blue")
        table.add_column("Type", style="green")
        table.add_column("Username", style="yellow")
        table.add_column("Password", style="black")

        for device in devices:
            table.add_row(
                device.host,
                str(getattr(device, "port", "-")),
                device.device_type,
                device.username,
                device.password,
            )

        self.console.print(table)

    def show_submission_results(self, submitted: List[HashableJob], unsubmitted: List[str]):
        """Display job submission results"""
        table = Table(title="Job Submission Results", **self.TABLE_KWARGS)

        if submitted:
            table.add_column("Submitted Jobs", style="green")
            for job in submitted:
                table.add_row(job.id)

        if unsubmitted:
            if not table.columns:
                table.add_column("Unsubmitted Hosts", style="red")
            else:
                table.add_column("Unsubmitted Hosts", style="red")
            for host in unsubmitted:
                table.add_row("", host)

        self.console.print(table)

    def show_final_summary(
        self,
        succeeded: Set[HashableJob],
        failed: Set[HashableJob],
        output_file: str,
    ):
        """Display final result summary"""
        if not output_file:
            output_file = ""

        table = Table(title="Result Summary", **self.TABLE_KWARGS)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")

        table.add_row("Total Devices", str(len(succeeded) + len(failed)))
        table.add_row("Successful Devices", f"[green]{len(succeeded)}[/green]")
        table.add_row("Failed Devices", f"[red]{len(failed)}[/red]")

        self.console.print(table)
        self.console.print(f"\n[blue]Results saved to:[/blue] {output_file}")

    def create_progress_bar(self, total_jobs: int) -> Progress:
        """Create a progress bar for job monitoring

        Args:
            total_jobs: Total number of jobs to monitor
        """
        return Progress(
            SpinnerColumn(),
            "[progress.description]{task.description}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            "[bold blue]{task.completed}/{task.total}",
            "•",
            "[green]Success: {task.fields[succeeded]}",
            "[red]Failed: {task.fields[failed]}",
            TimeElapsedColumn(),
            console=self.console,
        )


class NetPulseClient:
    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        api_key: str = DEFAULT_API_KEY,
        http_timeout: float = DEFAULT_HTTP_TIMEOUT,
    ):
        """Initialize the client with API endpoint and credentials

        Args:
            endpoint: NetPulse API endpoint URL
            api_key: API authentication key
            http_timeout: Timeout in seconds for HTTP requests
        """
        self.endpoint = endpoint
        self.headers = {"X-API-KEY": api_key}
        self.http_timeout = http_timeout

    def read_devices(self, file: str, vendor: str | None = None) -> pd.DataFrame:
        """Read device information from CSV/XLSX file

        Args:
            file: Path to the input file

        Returns:
            DataFrame containing device information

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is not supported
        """
        path = Path(file)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file}")

        if path.suffix.lower() == ".csv":
            df = pd.read_csv(file)
        elif path.suffix.lower() in [".xlsx", ".xls"]:
            df = pd.read_excel(file)
        else:
            raise ValueError("Only CSV and Excel (csv/xlsx/xls) formats are supported")

        df = df[df["Selected"] == True]  # noqa: E712
        if vendor:
            df = df[df["Vendor"].str.lower() == vendor.lower()]

        if df.empty:
            raise ValueError("No devices selected for execution")

        return df

    def prepare_template(
        self,
        constructor: type[TemplateParseRequest | TemplateRenderRequest],
        template_type: str,
        template: str | None,
    ):
        """Prepare template for parsing or rendering

        Args:
            constructor: Template constructor class
            template_type: Type of the template (e.g., textfsm, jinja2)
            template: Template URI or content

        Returns:
            TemplateParseRequest | TemplateRenderRequest | None: Template object if required.

        Raises:
            ValueError: If template type or URI is missing
            FileNotFoundError: If template file doesn't exist
        """
        # Check if required fields are present
        if (template_type is None) != (template is None):
            raise ValueError("Both template type and URI are required")

        # Early return if template is required
        if not template:
            return None

        pr = ensure_printer()
        server_side_file = template.startswith("file://")
        if server_side_file:
            pr.warning("Server-side template file is specified, skipping local file resolution.")
        else:
            # Try load template from local file
            try:
                tp = Path(template).resolve()
                if not tp.exists():
                    raise FileNotFoundError(f"Template file not found: {template}")
                with open(tp.as_posix(), "r") as f:
                    template = f.read()
            except Exception:
                pr.debug("Template is not a file, using inline template instead. ")

        return constructor(
            name=template_type,
            template=template,
        )

    def prepare_connection_args(self, row: pd.Series) -> DriverConnectionArgs:
        """Convert DataFrame row to device connection parameters

        Args:
            row: Single row from device information DataFrame

        Returns:
            DriverConnectionArgs: Validated connection parameters for the device

        Raises:
            ValueError: If required fields are missing or invalid
        """
        device_params = {
            "host": row["IP"],
            "port": int(row["Port"]) if not pd.isna(row["Port"]) else 22,
            "username": row["Username"],
            "password": row["Password"],
        }

        # Optional parameters
        if not pd.isna(row.get("Keepalive")):
            device_params["keepalive"] = int(row["Keepalive"])

        # Set device_type based on vendor
        if not pd.isna(row.get("Vendor")):
            try:
                vendor_name = str(row["Vendor"])
                vendor = DeviceVendor[vendor_name.upper()]
                device_params["device_type"] = vendor.value
            except KeyError as exc:
                raise ValueError(
                    f"Unsupported vendor '{row['Vendor']}' for device {row.get('IP')}"
                ) from exc

        return DriverConnectionArgs.model_validate(device_params)

    def bulk_execute(
        self, *, devices: List[DriverConnectionArgs], base_request: ExecutionRequest
    ) -> BatchSubmitJobResponse:
        """Execute commands or configs on multiple devices via unified /device/bulk API"""
        bulk_data = base_request.model_dump(exclude_none=True)
        bulk_data["devices"] = devices

        bulk_request = BulkExecutionRequest.model_validate(bulk_data)
        request_body = bulk_request.model_dump(exclude_none=True)

        response = requests.post(
            f"{self.endpoint}/device/bulk",
            headers=self.headers,
            json=request_body,
            timeout=self.http_timeout,
        )
        response.raise_for_status()
        return BatchSubmitJobResponse(**response.json())

    def check_jobs(self, jobs: set[HashableJob]) -> tuple[set[HashableJob], set[HashableJob]]:
        """Monitor execution status of submitted jobs

        Args:
            jobs: List of job IDs to monitor
        """
        pr = ensure_printer()
        succeeded = set()
        failed = set()

        for oldjob in jobs:
            try:
                # Use standard /{id} path for checking job status
                response = requests.get(
                    f"{self.endpoint}/jobs/{oldjob.id}",
                    headers=self.headers,
                    timeout=self.http_timeout,
                )
                response.raise_for_status()
                newjob_data = response.json()
                newjob = HashableJob(**newjob_data)

                if newjob.status == "finished":
                    if newjob.result and newjob.result.error:
                        pr.debug(f"Job {newjob.id} failed: {newjob.result}")
                        newjob.status = "failed"
                        failed.add(newjob)
                    else:
                        pr.debug(f"Job {newjob.id} succeeded: {newjob.result}")
                        succeeded.add(newjob)
                elif newjob.status == "failed":
                    pr.debug(f"Job {newjob.id} failed with no result")
                    failed.add(newjob)
            except Exception as e:
                pr.debug(f"Error checking job {oldjob.id}: {e}")
                # Keep in jobs to retry later
                continue

        return succeeded, failed


def main():
    try:
        signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
        _ = CliApp.run(RootSettings)
    except Exception as e:
        logging.error(f"Uncaught exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
