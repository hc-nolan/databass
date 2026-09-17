from typing import Tuple
from flask import request
from flask_paginate import Pagination, get_page_parameter


class Pager:
    @staticmethod
    def get_page_param(flask_request: request):
        """
        Parses and returns page parameter from Flask request
        """
        return flask_request.args.get(
            get_page_parameter(),
            type=int,
            default=1
        )

    @staticmethod
    def get_page_range(per_page: int, current_page: int) -> Tuple[int, int]:
        """
        Get the start and end indices for a page of results given the page size and current page number.

        Args:
            per_page (int): The number of results to return per page.
            current_page (int): The current page number (1-indexed).

        Returns:
            Tuple[int, int]: The start and end indices for the current page of results.

        Raises:
            ValueError: If `per_page` or `current_page` is less than or equal to 0.
        """
        if per_page <= 0 or current_page <= 0:
            raise ValueError("per_page and current_page must be positive integers")
        start = (current_page - 1) * per_page
        end = start + per_page
        return start, end

    @staticmethod
    def paginate(
            per_page: int,
            current_page: int,
            data,
    ):
        start, end = Pager.get_page_range(per_page, current_page)
        paged_data = data[start:end]
        flask_pagination = Pagination(
            page=current_page,
            total=len(data),
            search=False,
        )
        return paged_data, flask_pagination
