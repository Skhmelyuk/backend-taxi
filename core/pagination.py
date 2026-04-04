from collections import OrderedDict
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Pagination class with standard page size.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        """
        Return a paginated response with count, next/previous links, and results.
        Args:
            data (list): Serialized data for the current page.

        Returns:
            Response: DRF Response object with paginated structure:
            {
                "count": int,
                "next": str | None,
                "previous": str | None,
                "results": list
            }
        """
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class for large result sets.
    Attributes:
        page_size (int): Default number of items per page.
        page_size_query_param (str): Query parameter to override page size.
        max_page_size (int): Maximum allowed page size.
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination class for small result sets.
    Attributes:
        page_size (int): Default number of items per page.
        page_size_query_param (str): Query parameter to override page size.
        max_page_size (int): Maximum allowed page size.
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50
