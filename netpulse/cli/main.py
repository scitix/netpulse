#!/usr/bin/env python3
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Set, Type

import pandas as pd
import requests
from pydantic import (
    AliasChoices,
    BaseModel,
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

from netpulse.models import (
    DriverConnectionArgs,
    DriverName,
    QueueStrategy,
)
from netpulse.models.request import (
    BatchPullingRequest,
    BatchPushingRequest,
    TemplateParseRequest,
    TemplateRenderRequest,
)
from netpulse.models.response import (
    BatchSubmitJobResponse,
    GetJobResponse,
    JobInResponse,
)

# Constants
DEFAULT_ENDPOINT = "http://localhost:9000"
DEFAULT_API_KEY = "MY_API_KEY"

MONITORING_TIMEOUT = 300  # 5 minutes timeout
MONITORING_INTERVAL = 5  # Check per 5s


printer: "Printer" = None
client: "NetPulseClient" = None
config: "RootSettings" = None


class DeviceVendor(str, Enum):
    """Supported network device vendors and their corresponding netmiko device types"""

    H3C = "hp_comware"
    HUAWEI = "huawei"
    CISCO = "cisco_ios"
    ARISTA = "arista_eos"
    FORTINET = "fortinet"


class HashableJob(JobInResponse):
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, value):
        return self.id == value.id


class SubCommandSettings(BaseSettings):
    # Public args for all subcommands
    file: CliPositionalArg[str] = Field(
        ..., description="Path to the input CSV/XLSX file containing device information"
    )
    command: CliPositionalArg[str] = Field(
        ..., description="Command to execute on all selected devices"
    )

    # Public filters
    vendor: Optional[str] = Field(
        default=None,
        description="Filter devices by vendor (e.g., CISCO, HUAWEI), case insensitive",
    )

    # Public options
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

    _df: pd.DataFrame = PrivateAttr(None)

    # Helper method
    def _load_device_list(self):
        try:
            df = client.read_devices(self.file, vendor=self.vendor)
            devices = [client.prepare_connection_args(row) for _, row in df.iterrows()]
        except Exception as e:
            printer.error(f"Error in reading device lists: {e!s}")
            sys.exit(1)

        # Show loading summary
        printer.print("")
        printer.show_config(config)
        printer.show_device_list(devices)

        self._df = df
        return devices

    def _prompt_confirmation(self):
        if not Confirm.ask("Proceed?"):
            printer.print("\n[yellow]Operation cancelled by user.[/yellow]")
            sys.exit(0)

    def _monitor_job(self, submitted: List["HashableJob"]):
        jobs = set(submitted)
        succeeded = set()
        failed = set()

        # Monitor the job execution progress
        total_jobs = len(submitted)
        start_time = time.time()

        with printer.create_progress_bar(total_jobs) as progress:
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

                if elapsed_time >= config.timeout:
                    printer.warning(f"Monitoring timeout after {int(elapsed_time)}s")
                    for job in jobs:
                        job.status = "TIMEOUT"
                        failed.add(job)
                    break

                try:
                    su, fa = client.check_jobs(jobs)
                except Exception as e:
                    printer.error(f"Error in checking jobs: {e!s}")
                    continue

                succeeded.update(su)
                failed.update(fa)
                jobs = jobs - succeeded - failed

                remaining_time = max(0, config.timeout - elapsed_time)
                progress.update(
                    task,
                    completed=len(succeeded) + len(failed),
                    description=f"[yellow]Monitoring job execution (in {int(remaining_time)}s)",
                    succeeded=len(succeeded),
                    failed=len(failed),
                )

                if jobs:
                    time.sleep(config.interval)

        return succeeded, failed

    def _save_results(
        self,
        succeeded: set["HashableJob"],
        failed: set["HashableJob"],
        command: str,
    ) -> str:
        """Save execution results to CSV file

        Args:
            succeeded: Set of successful jobs
            failed: Set of failed jobs
            command: Executed command

        Returns:
            str: Path to the results file
        """
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
                        "Command": command,
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
                    "Command": command,
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


class PullSettings(SubCommandSettings):
    class TemplateType(str, Enum):
        TEXTFSM = "textfsm"
        TTP = "ttp"

    template_type: Optional[TemplateType] = Field(
        default=None,
        description="Template type used to parse the result",
        validation_alias=AliasChoices("template-type", "type"),
    )

    template: Optional[str] = Field(
        default=None,
        description="URI to the template used to parse the result",
        validation_alias=AliasChoices("template", "T"),
    )

    def cli_cmd(self) -> None:
        devices = self._load_device_list()

        # Prepare template
        parsing = client.prepare_template(TemplateParseRequest, self.template_type, self.template)

        if not self.force:
            self._prompt_confirmation()

        # Send request
        try:
            response = client.batch_pulling(command=self.command, devices=devices, parsing=parsing)
            submitted = (
                [HashableJob(**job.model_dump()) for job in response.data.succeeded]
                if response.data.succeeded
                else []
            )
            unsubmitted = response.data.failed if response.data.failed else []
        except Exception as e:
            printer.error(f"Error in batch requesting: {e!s}")
            sys.exit(1)

        # Display job submission results
        printer.print("")
        printer.show_submission_results(submitted, unsubmitted)

        if self.monitor:
            printer.print("\n[italic]Job Status Monitoring[/italic]")
            succeeded, failed = self._monitor_job(submitted)

            output_file = ""
            try:
                output_file = self._save_results(succeeded, failed, self.command)
            except Exception as e:
                printer.error(f"Error in saving results: {e}")
                sys.exit(1)
            finally:
                printer.print("")
                printer.show_final_summary(succeeded, failed, output_file)


class PushSettings(SubCommandSettings):
    class TemplateType(str, Enum):
        JINJA2 = "jinja2"

    template_type: TemplateType | None = Field(
        default=None,
        description="Template type used to render the config",
        validation_alias=AliasChoices("template-type", "type"),
    )

    template: Optional[str] = Field(
        default=None,
        description="URI to the template used to render the config",
        validation_alias=AliasChoices("template", "T"),
    )

    save: bool = Field(
        default=False,
        description="Save config into start config",
    )

    enable: bool = Field(
        default=True,
        description="Enter enable mode before pushing config",
    )

    # Override command field to use 'config' alias
    command: CliPositionalArg[str | Dict[str, str]] = Field(
        ...,
        description="config to push to all selected devices. (Dict if template rendering is used)",
        alias="config",
    )

    @model_validator(mode="after")
    def validate_template(self):
        if (self.template_type is None) != (self.template is None):
            raise ValueError("Both template type and URI are required")
        if self.template_type and not isinstance(self.command, dict):
            raise ValueError("Template rendering requires config as a Dict")
        return self

    def cli_cmd(self) -> None:
        devices = self._load_device_list()

        # Prepare template
        rendering = client.prepare_template(
            TemplateRenderRequest, self.template_type, self.template
        )

        if not self.force:
            self._prompt_confirmation()

        # Send request
        try:
            response = client.batch_pushing(
                config=self.command,
                devices=devices,
                rendering=rendering,
                save=self.save,
                enable=self.enable,
            )
            submitted = (
                [HashableJob(**job.model_dump()) for job in response.data.succeeded]
                if response.data.succeeded
                else []
            )
            unsubmitted = response.data.failed if response.data.failed else []
        except Exception as e:
            printer.error(f"Error in batch requesting: {e!s}")
            sys.exit(1)

        # Display job submission results
        printer.print("")
        printer.show_submission_results(submitted, unsubmitted)

        if self.monitor:
            printer.print("\n[italic]Job Status Monitoring[/italic]")
            succeeded, failed = self._monitor_job(submitted)

            output_file = ""
            try:
                output_file = self._save_results(succeeded, failed, self.command)
            except Exception as e:
                printer.error(f"Error in saving results: {e}")
                sys.exit(1)
            finally:
                printer.print("")
                printer.show_final_summary(succeeded, failed, output_file)


class RootSettings(BaseSettings):
    """
    NetPulse API Client in CLI
    """

    # Subcommands
    push: CliSubCommand[PushSettings] = Field(..., description="Push config to network devices")
    pull: CliSubCommand[PullSettings] = Field(..., description="Pull config from network devices")

    # API config
    endpoint: HttpUrl = Field(DEFAULT_ENDPOINT, description="NetPulse API endpoint URL")
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

    TABLE_KWARGS: ClassVar[Dict[str, str]] = {
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

        if setting.pull:
            show_subcommand_config(table, setting.pull)

        if setting.push:
            show_subcommand_config(table, setting.push)

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
                str(device.port),
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
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, api_key: str = DEFAULT_API_KEY):
        """Initialize the client with API endpoint and credentials

        Args:
            endpoint: NetPulse API endpoint URL
            api_key: API authentication key
        """
        self.endpoint = endpoint
        self.headers = {"X-API-KEY": api_key}

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

    def prepare_template(self, constructor: Type[BaseModel], template_type: str, template: str):
        """Prepare template for parsing or rendering

        Args:
            constructor: Template constructor class
            template_type: Type of the template (e.g., textfsm, jinja2)
            template: Template URI or content

        Returns:
            BaseModel: Template object

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

        server_side_file = template.startswith("file://")
        if server_side_file:
            printer.warning("Server-side template file is specified, skipping local files.")
        else:
            # Try load template from local file
            try:
                tp = Path(template).resolve()
                if not tp.exists():
                    raise FileNotFoundError(f"Template file not found: {template}")
                with open(tp.as_posix(), "r") as f:
                    template = f.read()
            except Exception:
                printer.debug("Template is not a file, using inline template instead. ")

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
                vendor = DeviceVendor[row["Vendor"].upper()]
                device_params["device_type"] = vendor.value
            except KeyError:
                printer.warning(f"Unknown vendor: {row['Vendor']}")

        return DriverConnectionArgs.model_validate(device_params)

    def batch_pulling(
        self,
        command: str,
        *,
        devices: List[DriverConnectionArgs],
        parsing: TemplateParseRequest = None,
        defaults: DriverConnectionArgs = None,
    ) -> BatchSubmitJobResponse:
        """Execute command on multiple devices in batch

        Args:
            command: Command to execute on devices
            devices: List of device connection parameters
            parsing: TemplateParseRequest for parsing command output
            defaults: Default connection parameters

        Returns:
            BatchSubmitJobResponse containing job submission results

        Raises:
            requests.exceptions.RequestException: If API request fails
            ValueError: If job submission returns non-zero code
        """
        # Prepare request payload
        payload = BatchPullingRequest(
            driver=DriverName.NETMIKO,
            queue_strategy=QueueStrategy.PINNED,
            devices=devices,
            command=command,
            connection_args=defaults if defaults else DriverConnectionArgs(),
            parsing=parsing,
        )

        # Send request
        response = requests.post(
            f"{self.endpoint}/pull/batch",
            headers=self.headers,
            json=payload.model_dump(exclude_none=True),
        )
        response.raise_for_status()

        resp = BatchSubmitJobResponse(**response.json())
        if resp.code != 0:
            raise ValueError(f"job submission return non-zero: {resp.message}")

        return resp

    def batch_pushing(
        self,
        config: str | Dict[str, str],
        *,
        save: bool = False,
        enable: bool = True,
        devices: List[DriverConnectionArgs],
        rendering: TemplateRenderRequest = None,
        defaults: DriverConnectionArgs = None,
    ):
        """Execute command on multiple devices in batch

        Args:
            config: Configuration to push to devices
            save: Save config into start config
            enable: Enter enable mode before pushing config
            devices: List of device connection parameters
            rendering: TemplateRenderRequest for rendering configuration
            defaults: Default connection parameters

        Returns:
            BatchSubmitJobResponse containing job submission results

        Raises:
            requests.exceptions.RequestException: If API request fails
            ValueError: If job submission returns non-zero code
        """
        # Prepare request payload
        payload = BatchPushingRequest(
            driver=DriverName.NETMIKO,
            queue_strategy=QueueStrategy.PINNED,
            devices=devices,
            config=config,
            connection_args=defaults if defaults else DriverConnectionArgs(),
            rendering=rendering,
            enable_mode=enable,
        )

        # Save is a extra field defined in Netmiko
        payload = payload.model_dump(exclude_none=True)
        payload["save"] = save

        # Send request
        response = requests.post(
            f"{self.endpoint}/push/batch",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()

        resp = BatchSubmitJobResponse(**response.json())
        if resp.code != 0:
            raise ValueError(f"job submission return non-zero: {resp.message}")

        return resp

    def check_jobs(self, jobs: set[HashableJob]) -> tuple[set[HashableJob], set[HashableJob]]:
        """Monitor execution status of submitted jobs

        Args:
            jobs: List of job IDs to monitor
        """
        succeeded = set()
        failed = set()

        for oldjob in jobs:
            response = requests.get(
                f"{self.endpoint}/job", headers=self.headers, params={"id": oldjob.id}
            )
            response.raise_for_status()

            status_response = GetJobResponse(**response.json())
            if not status_response.data:
                oldjob.status = "UNKNOWN"
                failed.add(oldjob)
                continue

            if isinstance(status_response.data, list):
                newjob = status_response.data[0]
            else:
                newjob = status_response.data
            newjob = HashableJob(**newjob.model_dump())

            if newjob.status == "finished":
                if newjob.result and newjob.result.error:
                    printer.debug(f"Job {newjob.id} failed: {newjob.result.error}")
                    newjob.status = "failed"
                    failed.add(newjob)
                else:
                    printer.debug(f"Job {newjob.id} succeeded: {newjob.result.error}")
                    succeeded.add(newjob)
            elif newjob.status == "failed":
                printer.debug(f"Job {newjob.id} failed with no result")
                failed.add(newjob)

            # If job still running, just ignore it and wait for next cycle

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
