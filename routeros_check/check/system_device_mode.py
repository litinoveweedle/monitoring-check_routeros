# SPDX-FileCopyrightText: PhiBo DinoTools (2021)
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import List, Optional

import click
import nagiosplugin

from ..cli import cli
from ..context import BooleanContext
from ..helper import logger
from ..resource import RouterOSCheckResource


class SystemDeviceModeResource(RouterOSCheckResource):
    name = "DeviceMode"

    def __init__(
        self,
        cmd_options,
        check: nagiosplugin.Check,
    ):
        super().__init__(cmd_options=cmd_options, check=check)

        self._routeros_metric_values = [
            {"name": "mode", "type": None},
            {"name": "flagged", "type": bool},
        ]

    def probe(self):
        logger.info("Fetching data ...")
        call = self.api.path(
            "/system/device-mode"
        )
        result = tuple(call)[0]

        return self.get_routeros_metric_item(result)


class SystemDeviceModeFlaggedContext(BooleanContext):
    def evaluate(self, metric, resource):
        if metric.value is True:
            return self.result_cls(
                nagiosplugin.state.Critical,
                hint=(
                    "Device configuration is flagged. Check all router configuration for unauthorized changes "
                    "and run '/system/device-mode/update flagged=no' after the audit."
                )
            )
        return self.result_cls(nagiosplugin.state.Ok, hint="Device configuration is not flagged")


class SystemDeviceModeModeContext(nagiosplugin.Context):
    def __init__(self, *args, modes: Optional[List[str]] = None, **kwargs):
        self._modes = modes
        super(SystemDeviceModeModeContext, self).__init__(*args, **kwargs)

    def evaluate(self, metric, resource):
        if self._modes is None or len(self._modes) == 0 or metric.value in self._modes:
            return nagiosplugin.Result(
                nagiosplugin.Ok,
                hint=f"Device mode is '{metric.value}'"
            )

        return nagiosplugin.Result(
            nagiosplugin.Warn,
            hint=f"Device mode '{metric.value}' not in list with allowed modes: {', '.join(self._modes)}"
        )


class SystemDeviceModeSummary(nagiosplugin.Summary):
    def ok(self, results: List[nagiosplugin.Result]):
        hints = []
        for result in results:
            if result.hint:
                hints.append(result.hint)

        return ", ".join(hints)


@cli.command("system.device-mode")
@click.option(
    "--mode",
    "modes",
    default=None,
    multiple=True,
    help="Allowed device mode(s). Repeat to use multiple values. Example: advanced, home, basic, ros"
)
@click.pass_context
@nagiosplugin.guarded
def system_device_mode(ctx, modes):
    """Check the RouterOS device-mode and its flagged status"""
    check = nagiosplugin.Check()

    check.add(
        SystemDeviceModeResource(
            cmd_options=ctx.obj,
            check=check,
        ),
        SystemDeviceModeFlaggedContext(
            name="flagged",
        ),
        SystemDeviceModeModeContext(
            name="mode",
            modes=modes,
        ),
        SystemDeviceModeSummary(),
    )

    check.main(verbose=ctx.obj["verbose"])
