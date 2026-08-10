from rest_framework.authentication import SessionAuthentication


class SessionAuthenticationWithChallenge(SessionAuthentication):
    def authenticate_header(self, request):
        return "Session"
