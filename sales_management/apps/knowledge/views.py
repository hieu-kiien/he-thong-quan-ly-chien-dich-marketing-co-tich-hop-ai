from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services import KnowledgeDependencyError, KnowledgeService, format_context


def _search(request):
    query = (request.GET.get("q") or "").strip()
    if not query:
        return None, JsonResponse({"error": "q là bắt buộc"}, status=400)
    try:
        top_k = int(request.GET.get("top_k", "5"))
    except ValueError:
        return None, JsonResponse({"error": "top_k phải là số nguyên"}, status=400)
    try:
        results = KnowledgeService().search(
            query,
            top_k=top_k,
            status=request.GET.get("status") or None,
            source_type_filter=request.GET.get("source_type") or None,
        )
    except ValueError as exc:
        return None, JsonResponse({"error": str(exc)}, status=400)
    except KnowledgeDependencyError as exc:
        return None, JsonResponse({"error": str(exc)}, status=503)
    return results, None


@require_GET
def search(request):
    results, error = _search(request)
    if error:
        return error
    return JsonResponse(
        {
            "query": request.GET["q"],
            "results": results,
            "context": format_context(results),
        }
    )


@require_GET
def context(request):
    results, error = _search(request)
    if error:
        return error
    return JsonResponse({"query": request.GET["q"], "context": format_context(results)})
