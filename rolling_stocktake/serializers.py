"""API serializers for the RollingStocktake plugin."""

from rest_framework import serializers

from stock.serializers import StockItemSerializer


class RollingStocktakeSerializer(serializers.Serializer):
    """Serializer for the RollingStocktake plugin.

    This returns the items to be counted by the user.
    """

    class Meta:
        """Meta options for this serializer."""

        fields = [
            "items",
        ]

    items = StockItemSerializer(
        many=True,
        read_only=True,
    )
