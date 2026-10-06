"""Authenticated central Dumosense intelligence endpoint."""
from django.db import DatabaseError
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .services import query_agent
from .reads import read_insights

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def query(request):
    if not settings.DUMOSENSE_ENABLE_INTELLIGENCE_QUERY:
        return Response({"error": "Intelligence query is not enabled."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    question = request.data.get("question") if isinstance(request.data, dict) else None
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        return Response({"error": "A short question is required."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        output = query_agent(user=request.user, question=question)
    except PermissionError:
        return Response({"error": "Current access is not available for the requested product."},
                        status=status.HTTP_403_FORBIDDEN)
    except ValueError:
        return Response({"error": "The requested product data could not be validated."},
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except DatabaseError:
        return Response({"error": "The intelligence service is temporarily unavailable."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(output)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def insights(request):
    if not settings.DUMOSENSE_ENABLE_INTELLIGENCE_QUERY:
        return Response({"error": "Intelligence query is not enabled."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    product = request.query_params.get("product")
    try:
        limit = int(request.query_params.get("limit", "10"))
        items = read_insights(user=request.user, product=product, limit=limit)
    except (TypeError, ValueError):
        return Response({"error": "Invalid product or limit."}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError:
        return Response({"error": "Current access is not available for the requested product."},
                        status=status.HTTP_403_FORBIDDEN)
    except DatabaseError:
        return Response({"error": "The intelligence service is temporarily unavailable."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"insights": items})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def latest_insight(request):
    if not settings.DUMOSENSE_ENABLE_INTELLIGENCE_QUERY:
        return Response({"error": "Intelligence query is not enabled."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    product = request.query_params.get("product")
    try:
        items = read_insights(user=request.user, product=product, limit=1)
    except ValueError:
        return Response({"error": "Invalid product."}, status=status.HTTP_400_BAD_REQUEST)
    except PermissionError:
        return Response({"error": "Current access is not available for the requested product."},
                        status=status.HTTP_403_FORBIDDEN)
    except DatabaseError:
        return Response({"error": "The intelligence service is temporarily unavailable."},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response({"insight": items[0] if items else None})
