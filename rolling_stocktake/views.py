"""API views for the RollingStocktake plugin.

In practice, you would define your custom views here.

Ref: https://www.django-rest-framework.org/api-guide/views/
"""

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RollingStocktakeSerializer


class RollingStocktakeView(APIView):
    """API view for the RollingStocktake plugin.

    This view returns the next item to be counted by the user.
    The item is selected based on:

    - Items which have not been counted for the longest time
    - Items which are in stock
    - Items which belong to parts which are active or virtual
    - Items which belong to parts to which the user is subscribed (if any)

    """

    # You can control which users can access this view using DRF permissions
    permission_classes = [permissions.IsAuthenticated]

    # Control how the response is formatted
    serializer_class = RollingStocktakeSerializer

    def get(self, request, *args, **kwargs):
        """Override the GET method to return stock items for stocktake."""

        from plugin import registry

        rolling_stocktake_plugin = registry.get_plugin("rolling-stocktake")

        # Check if the user is in the allowed group (if configured)
        user_group = rolling_stocktake_plugin.get_setting("USER_GROUP")

        if user_group:
            # Check if the user is a member of the required group
            if not request.user.groups.filter(pk=user_group).exists():
                # User is not in the allowed group - return empty response
                return Response(
                    {
                        "items": [],
                        "stocktake_date": None,
                        "creation_date": None,
                        "error": "User does not have permission to perform stocktake operations",
                    },
                    status=403,
                )

        stock_items = rolling_stocktake_plugin.get_stock_items(request.user)

        # Get the oldest item's dates for backward compatibility
        # These dates are passed directly to the serializer and will be included in the response
        oldest_item = stock_items[0] if stock_items else None
        stocktake_date = (
            getattr(oldest_item, "stocktake_date", None) if oldest_item else None
        )
        creation_date = (
            getattr(oldest_item, "creation_date", None) if oldest_item else None
        )

        response_serializer = self.serializer_class(
            instance={
                "items": stock_items,
                "stocktake_date": stocktake_date,
                "creation_date": creation_date,
            }
        )

        return Response(response_serializer.data, status=200)
