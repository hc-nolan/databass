from sqlalchemy import extract, Integer
from sqlalchemy.engine.row import Row


def apply_comparison_filter(query, model: type, key: str, operator: str, value: str):
    """
    Used by dynamic_search to perform comparisons on begin, end, year, or rating
    :param query: An SQLAlchemy query class
    :param model: The database model class to filter on
    :param key: The column to filter on - begin_date or end_date
    :param operator: Denotes the comparison to perform
    :param value: The value to compare against
    :return: Newly constructed query
    """
    attribute = getattr(model, key)
    if not attribute:
        raise NameError(f"No attribute '{key}' found in model {model}")
    try:
        val = int(value)
    except TypeError as exc:
        raise TypeError(f"Value must be an integer, got {type(value)}: {value}") from exc

    if operator not in ["<", "=", ">"]:
        raise ValueError(f"Unrecognized operator value for year_comparison: {operator}")

    if key in ("begin", "end"):
        query = query.filter(extract("year", attribute).cast(Integer).op(operator)(val))
    elif key == "rating":
        query = query.filter(attribute.op(operator)(value))
    elif key == "year":
        query = query.filter(attribute.op(operator)(value))
    return query


# Utility function to calculate the mean average rating and total release count
# for releases associated with a specific Label/Artist
def mean_avg_and_count(entities: list[Row]) -> (int, int):
    """
    :param entities: List of SQLAlchemy Rows; returned from average_ratings_and_total_counts()
    :return: A tuple representing the mean average release rating and mean release count
    """
    avg = count = 0
    total = len(entities)
    for item in entities:
        try:
            avg += int(item.average_rating)
            count += int(item.release_count)
        except AttributeError:
            # TODO: consider logging info about the erroring release
            # Have not encountered this in practice, but if it is encountered
            # it means there is a corrupt entry
            total -= 1

    mean_avg = avg / total
    mean_count = count / total
    return mean_avg, mean_count


# Utility function used to calculate Bayesian average
def bayesian_avg(item_weight: float, item_avg: float, mean_avg: float) -> float:
    """
    Calculates the Bayesian average rating for a given item weight and average
    :param item_weight: Float representing the item's weight for the formula;
                        calculated as: count / (count + mean count)
    :param item_avg: Item's average rating
    :param mean_avg: Mean average release rating for all database entries
    :return: Float representing the Bayesian average rating for releases associated with this item
    """
    if not item_weight or not item_avg or not mean_avg:
        raise ValueError("Input missing one of the required values")
    return item_weight * item_avg + (1 - item_weight) * mean_avg
