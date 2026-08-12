from rest_framework.exceptions import APIException


class VersionConflict(APIException):
    status_code = 409
    default_code = "version_conflict"
    default_detail = "This record changed after you opened it. Refresh and review the latest version."

    def __init__(self, current_version):
        super().__init__(
            {
                "message": self.default_detail,
                "current_version": current_version,
            }
        )
