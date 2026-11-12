
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Authenticate requests using a JWT in an HttpOnly cookie.

    Existing Authorization: Bearer requests remain supported.
    """

    def authenticate(self, request):
        # Keep existing Bearer-token authentication working.
        header = self.get_header(request)

        if header is not None:
            return super().authenticate(request)

        # Otherwise, look for the browser's access-token cookie.
        token = request.COOKIES.get("dumosense_access")

        if not token:
            return None

        # Cookie authentication needs CSRF protection.
        from django.middleware.csrf import CsrfViewMiddleware

        csrf_checker = CsrfViewMiddleware(
            lambda req: None
        )

        csrf_checker.process_request(request._request)

        rejection = csrf_checker.process_view(
            request._request,
            lambda req: None,
            (),
            {}
        )

        if rejection is not None:
            raise PermissionDenied(
                "CSRF verification failed."
            )

        validated_token = self.get_validated_token(token)

        return self.get_user(validated_token), validated_token
