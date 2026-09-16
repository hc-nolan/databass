import pytest
from sqlalchemy.exc import IntegrityError
from databass.errors.util import integrity_error_message, friendly_message


def _integrity_error(orig_message: str) -> IntegrityError:
    return IntegrityError("statement", {}, Exception(orig_message))


class TestIntegrityErrorMessage:
    @pytest.mark.parametrize(
        "orig_message",
        [
            "UNIQUE constraint failed: release.mbid",
            'duplicate key value violates unique constraint "release_mbid_key"\n'
            "DETAIL:  Key (mbid)=(abc-123) already exists.\n",
        ],
    )
    def test_unique_violation_names_field(self, orig_message):
        err = _integrity_error(orig_message)
        message = integrity_error_message(err)
        assert "mbid" in message
        assert "already exists" in message

    @pytest.mark.parametrize(
        "orig_message",
        [
            "NOT NULL constraint failed: release.name",
            'null value in column "name" of relation "release" violates not-null constraint',
        ],
    )
    def test_not_null_violation_names_field(self, orig_message):
        err = _integrity_error(orig_message)
        message = integrity_error_message(err)
        assert "name" in message
        assert "required" in message

    def test_check_violation(self):
        err = _integrity_error("CHECK constraint failed: rating >= 0 AND rating <= 100")
        message = integrity_error_message(err)
        assert "rating" in message

    def test_foreign_key_violation(self):
        err = _integrity_error("FOREIGN KEY constraint failed")
        message = integrity_error_message(err)
        assert "references a record" in message

    def test_unparseable_error_falls_back_to_generic_message(self):
        err = _integrity_error("some totally unexpected driver error")
        message = integrity_error_message(err)
        assert message == "Could not save the entry because it conflicts with an existing record."


class TestFriendlyMessage:
    def test_integrity_error_uses_integrity_error_message(self):
        err = _integrity_error("UNIQUE constraint failed: artist.name")
        assert friendly_message(err) == integrity_error_message(err)

    def test_value_error_uses_str(self):
        err = ValueError("ERROR: No supported image type found in URL: http://x.com/pic")
        assert friendly_message(err) == str(err)

    def test_exception_with_no_message_falls_back(self):
        err = Exception()
        assert friendly_message(err) == "An unexpected Exception occurred."
