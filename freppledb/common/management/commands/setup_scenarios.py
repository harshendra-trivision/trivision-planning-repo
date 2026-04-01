#
# Copyright (C) 2024 by frePPLe bv
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = "Set up scenario databases and grant user access for the scenario dropdown"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            default="admin",
            help="Username to grant scenario access to (default: admin)",
        )
        parser.add_argument(
            "--migrate",
            action="store_true",
            help="Run migrations on all scenario databases",
        )

    def handle(self, *args, **options):
        from freppledb.common.models import Scenario, User

        username = options["user"]
        run_migrate = options["migrate"]

        self.stdout.write(self.style.NOTICE("Setting up scenarios..."))

        # Get all configured databases (scenarios)
        all_scenarios = list(settings.DATABASES.keys())
        self.stdout.write(f"Configured databases: {all_scenarios}")

        # Run migrations if requested
        if run_migrate:
            for db_name in all_scenarios:
                if db_name != DEFAULT_DB_ALIAS:
                    self.stdout.write(f"Running migrations for {db_name}...")
                    try:
                        call_command("migrate", database=db_name, verbosity=0)
                        self.stdout.write(
                            self.style.SUCCESS(f"  Migrations complete for {db_name}")
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  Migration failed for {db_name}: {e}")
                        )

        # Sync scenarios with settings
        self.stdout.write("Syncing scenarios with settings...")
        try:
            Scenario.syncWithSettings()
            self.stdout.write(self.style.SUCCESS("  Scenarios synced successfully"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Sync failed: {e}"))

        # Update scenario status to 'In use'
        self.stdout.write("Updating scenario status...")
        for db_name in all_scenarios:
            try:
                scenario = Scenario.objects.using(DEFAULT_DB_ALIAS).get(name=db_name)
                if scenario.status != "In use" and db_name != DEFAULT_DB_ALIAS:
                    scenario.status = "In use"
                    scenario.save(using=DEFAULT_DB_ALIAS)
                    self.stdout.write(f"  Set {db_name} status to 'In use'")
            except Scenario.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  Scenario {db_name} not found in database")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error updating {db_name}: {e}"))

        # Grant user access to all scenarios
        self.stdout.write(f"Granting access to user '{username}'...")
        try:
            user = User.objects.using(DEFAULT_DB_ALIAS).get(username=username)
            user.databases = all_scenarios
            user.save(using=DEFAULT_DB_ALIAS)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  User '{username}' now has access to: {all_scenarios}"
                )
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f"  User '{username}' not found. Create the user first, then run this command again."
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error granting access: {e}"))

        # Display current scenarios
        self.stdout.write("\nCurrent scenarios in database:")
        for scenario in Scenario.objects.using(DEFAULT_DB_ALIAS).all():
            self.stdout.write(
                f"  - {scenario.name}: status={scenario.status}, description={scenario.description}"
            )

        self.stdout.write(
            self.style.SUCCESS("\nScenario setup complete! Restart the app to see the dropdown.")
        )
