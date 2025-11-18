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
            "stocktake_date",
            "creation_date",
        ]

    items = StockItemSerializer(
        many=True,
        read_only=True,
    )

    stocktake_date = serializers.DateField(read_only=True, allow_null=True)

    creation_date = serializers.DateField(read_only=True, allow_null=True)
