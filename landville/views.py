from django.http import JsonResponse


def error_404(request, exception):
    message = ("The endpoint you are trying to access might "
               "have been removed, "
               "had its name changed, or is temporarily unavailable. "
               "Please check the documentation here : "
               "/api/v1/documentation/ "
               "and try again later.")
    response = JsonResponse(data={"message": message})
    response.status_code = 404
    return response
