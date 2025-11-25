"""Support rolling stocktake for InvenTree"""

from django.db.models import DateField, Min, F
from django.db.models.functions import Cast, Coalesce
from django.core.validators import MinValueValidator

from plugin import InvenTreePlugin

from plugin.mixins import (
    EventMixin,
    ScheduleMixin,
    SettingsMixin,
    UrlsMixin,
    UserInterfaceMixin,
)

from . import PLUGIN_VERSION


class RollingStocktake(
    EventMixin,
    ScheduleMixin,
    SettingsMixin,
    UrlsMixin,
    UserInterfaceMixin,
    InvenTreePlugin,
):
    """RollingStocktake - InvenTree plugin for rolling stocktake functionality."""

    # Plugin metadata
    TITLE = "Rolling Stocktake"
    NAME = "RollingStocktake"
    SLUG = "rolling-stocktake"
    DESCRIPTION = "Support rolling stocktake for InvenTree"
    VERSION = PLUGIN_VERSION

    # Additional project information
    AUTHOR = "Oliver Walters"
    WEBSITE = "https://github.com/inventree/rolling-stocktake-plugin"
    LICENSE = "MIT"

    # Optionally specify supported InvenTree versions
    MIN_VERSION = "1.1.0"
    MAX_VERSION = "2.0.0"

    # Scheduled tasks (from ScheduleMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/schedule/
    SCHEDULED_TASKS = {
        # Define your scheduled tasks here...
    }

    # Plugin settings (from SettingsMixin)
    SETTINGS = {
        "USER_GROUP": {
            "name": "Allowed Group",
            "description": "The user group required to participate in perform rolling stocktake",
            "model": "auth.group",
        },
        "DAILY_LIMIT": {
            "name": "Daily Limit",
            "description": "The maximum number of stock items to be counted by a user in a single day (set to 0 for unlimited)",
            "default": 5,
            "validator": [
                int,
                MinValueValidator(0),
            ],
        },
        "IGNORE_EXTERNAL": {
            "name": "Ignore External Locations",
            "description": "Ignore stock items which are located in external locations",
            "default": True,
            "validator": bool,
        },
        "STOCKTAKE_SCOPE": {
            "name": "Stocktake Scope",
            "description": "Determine which stock items to present for stocktake: Single Item (oldest item only), Location (all items at the same location), Location with Sublocations (all items at the same location including sublocations), or All (all items of the same part)",
            "default": "ITEM",
            "choices": [
                ("ITEM", "Single Item"),
                ("LOCATION", "Stock Location"),
                ("LOCATION_WITH_SUBLOCATIONS", "Stock Location with Sublocations"),
                ("ALL", "All Items of Part"),
            ],
        },
    }

    def get_stock_items(self, user):
        """Return StockItem(s) which should be counted next by the given user.

        Returns a list of items based on the STOCKTAKE_SCOPE setting:
        - ITEM: Single oldest item
        - LOCATION: All items at the same location as the oldest item (same location only)
        - LOCATION_WITH_SUBLOCATIONS: All items at the same location as the oldest item (including sublocations)
        - ALL: All items of the same part as the oldest item
        """

        from InvenTree.helpers import current_date
        from stock.models import StockItem

        # First, check if the user has already counted the maximum number of items today
        daily_limit = int(self.get_setting("DAILY_LIMIT", backup_value=5))

        if daily_limit > 0:
            stocakes = StockItem.objects.filter(
                stocktake_date=current_date(),
                stocktake_user=user,
            ).count()

            # Already reached the daily limit
            if stocakes >= daily_limit:
                return []

        # Start with a list of "in stock" items
        items = StockItem.objects.filter(StockItem.IN_STOCK_FILTER)

        # Exclude items which are linked to inactive or virtual parts
        items = items.filter(part__active=True).exclude(part__virtual=True)

        # Optionally filter out items in external locations
        if self.get_setting("IGNORE_EXTERNAL", backup_value=True):
            items = items.exclude(location__external=True)

        # TODO: Filter items based on user subscriptions

        # Annotate the "creation" date, based on the oldest StockItemHistory entry
        items = items.annotate(
            creation_date=Cast(Min("tracking_info__date"), output_field=DateField())
        )

        # For items which do not have a "stocktake" date, annotate the "creation" date

        items = items.annotate(
            oldest_date=Coalesce(
                F("stocktake_date"), F("creation_date"), output_field=DateField()
            )
        )

        # TODO: Randomize the order of items which have the same stocktake date

        items = items.order_by("oldest_date")

        # Get the oldest item
        oldest_item = items.first()

        if not oldest_item:
            return []

        # Get the scope setting
        scope = self.get_setting("STOCKTAKE_SCOPE", backup_value="ITEM")

        if scope == "ITEM":
            # Return only the single oldest item
            return [oldest_item]
        elif scope == "LOCATION":
            # Return all items of the same part at the same location (same location only)
            location = oldest_item.location

            if location:
                # Filter items by the same part and location (exact location only)
                location_items = items.filter(part=oldest_item.part, location=location)
            else:
                # If no location, return items without location for the same part
                location_items = items.filter(
                    location__isnull=True, part=oldest_item.part
                )
            return list(location_items)
        elif scope == "LOCATION_WITH_SUBLOCATIONS":
            # Return all items of the same part at the same location (including sublocations)
            location = oldest_item.location

            if location:
                # Filter items by the same part and location (including sublocations)
                location_items = items.filter(
                    part=oldest_item.part,
                    location__in=location.get_descendants(include_self=True),
                )
            else:
                # If no location, return items without location for the same part
                location_items = items.filter(
                    location__isnull=True, part=oldest_item.part
                )
            return list(location_items)
        elif scope == "ALL":
            # Return all items of the same part
            part_items = items.filter(part=oldest_item.part)
            return list(part_items)
        else:
            # Default to single item
            return [oldest_item]

    # Respond to InvenTree events (from EventMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/event/
    def wants_process_event(self, event: str) -> bool:
        """Return True if the plugin wants to process the given event."""
        # Example: only process the 'create part' event
        return event == "part_part.created"

    def process_event(self, event: str, *args, **kwargs) -> None:
        """Process the provided event."""
        print("Processing custom event:", event)
        print("Arguments:", args)
        print("Keyword arguments:", kwargs)

    # Custom URL endpoints (from UrlsMixin)
    # Ref: https://docs.inventree.org/en/latest/plugins/mixins/urls/
    def setup_urls(self):
        """Configure custom URL endpoints for this plugin."""
        from django.urls import path
        from .views import RollingStocktakeView

        return [
            # Provide path to a simple custom view - replace this with your own views
            path(
                "next/",
                RollingStocktakeView.as_view(),
                name="api-rolling-stocktake-view",
            ),
        ]

    # Custom dashboard items
    def get_ui_dashboard_items(self, request, context: dict, **kwargs):
        """Return a list of custom dashboard items to be rendered in the InvenTree user interface."""

        # Check if user has permission based on the configured group
        if not request.user or not request.user.is_authenticated:
            return []

        # Check if the user is in the allowed group (if configured)
        user_group = self.get_setting("USER_GROUP")

        if user_group and user_group != "":
            # Only show widget to users in the allowed group
            if not request.user.groups.filter(pk=user_group).exists():
                return []

        items = []

        items.append({
            "key": "rolling-stocktake-dashboard",
            "title": "Rolling Stocktake Dashboard Item",
            "description": "Display a stock item which needs to be counted next",
            "icon": "ti:dashboard:outline",
            "source": self.plugin_static_file(
                "Dashboard.js:renderRollingStocktakeDashboardItem"
            ),
            "context": {
                "settings": self.get_settings_dict(),
            },
        })

        return items
